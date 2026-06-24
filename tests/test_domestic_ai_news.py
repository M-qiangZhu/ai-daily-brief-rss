import asyncio
from email.message import EmailMessage
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

import src.main as main_module
from src.domestic_ai_news import DomesticAINewsFetcher, NewsItem
from src.main import _mark_notification_sent, _notification_sent, notify_from_archive
from src.notifier import build_wechat_markdown
from src.page_generator import PageGenerator


def test_feed_parses_domestic_ai_item(tmp_path):
    now = datetime.now(timezone.utc)
    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <item>
          <title>江苏发布人工智能大模型政策</title>
          <link>https://example.com/ai-policy</link>
          <description><![CDATA[<p>江苏省围绕人工智能和大模型产业发布新政策。</p>]]></description>
          <pubDate>{now.strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
        </item>
      </channel>
    </rss>"""
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({
        "fetch_limit": 10,
        "feeds": [{"name": "测试来源", "url": "https://example.com/feed.xml", "enabled": True}],
        "searches": [],
    }), encoding="utf-8")

    async def run():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=rss)

        fetcher = DomesticAINewsFetcher(config_path)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetcher._fetch_feed(client, fetcher.config["feeds"][0], now.replace(hour=0))

    items = asyncio.run(run())

    assert len(items) == 1
    assert items[0].type == "政策"
    assert items[0].source_site == "测试来源"
    assert items[0].content_summary == "江苏省围绕人工智能和大模型产业发布新政策。"


def test_feed_filters_non_ai_item(tmp_path):
    now = datetime.now(timezone.utc)
    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <item>
          <title>周末读书与旅行记录</title>
          <link>https://example.com/life</link>
          <description>一篇关于城市散步、读书和咖啡馆的生活记录。</description>
          <pubDate>{now.strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
        </item>
      </channel>
    </rss>"""
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({
        "fetch_limit": 10,
        "feeds": [{"name": "测试来源", "url": "https://example.com/feed.xml", "enabled": True}],
        "searches": [],
    }), encoding="utf-8")

    async def run():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=rss)

        fetcher = DomesticAINewsFetcher(config_path)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetcher._fetch_feed(client, fetcher.config["feeds"][0], now.replace(hour=0))

    assert asyncio.run(run()) == []


def _mail_bytes(subject: str, date_value: str, html: str | None = None, text: str | None = None) -> bytes:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = "news@example.com"
    message["To"] = "reader@example.com"
    message["Date"] = date_value
    message["Message-ID"] = f"<{abs(hash(subject))}@example.com>"
    message.set_content(text or "plain fallback")
    if html is not None:
        message.add_alternative(html, subtype="html")
    return message.as_bytes()


class FakeIMAP:
    messages: dict[bytes, bytes] = {}
    commands: list[tuple] = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.closed = False

    def login(self, user, password):
        self.commands.append(("login", user, password))
        return "OK", []

    def _simple_command(self, *args):
        self.commands.append(("_simple_command", *args))
        return "OK", []

    def select(self, folder, readonly=False):
        self.commands.append(("select", folder, readonly))
        return "OK", []

    def search(self, charset, *criteria):
        self.commands.append(("search", charset, *criteria))
        return "OK", [b" ".join(self.messages.keys())]

    def fetch(self, message_id, query):
        self.commands.append(("fetch", message_id, query))
        return "OK", [(b"1 (BODY[])", self.messages[message_id])]

    def close(self):
        self.closed = True
        return "OK", []

    def logout(self):
        return "BYE", []


def test_imap_mail_fetch_extracts_html_news_and_uses_body_peek(tmp_path, monkeypatch):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)
    FakeIMAP.commands = []
    FakeIMAP.messages = {
        b"1": _mail_bytes(
            "今日新闻",
            "Wed, 24 Jun 2026 08:10:00 +0800",
            html="""
            <html><body>
              <ul>
                <li><a href="https://example.com/model">OpenAI 发布新模型</a><p>大模型推理能力升级。</p></li>
                <li><a href="https://example.com/agent">企业 AI Agent 平台发布</a><p>智能体工作流面向开发者开放。</p></li>
                <li><a href="https://example.com/model">OpenAI 发布新模型</a></li>
              </ul>
            </body></html>
            """,
        )
    }
    monkeypatch.setattr("src.domestic_ai_news.imaplib.IMAP4_SSL", FakeIMAP)
    monkeypatch.setenv("MAIL_NEWS_IMAP_USER", "reader@163.com")
    monkeypatch.setenv("MAIL_NEWS_IMAP_PASSWORD", "auth-code")

    items = fetcher._fetch_imap_mail(
        {"name": "163新闻邮件", "kind": "imap_mail", "folder": "INBOX", "source_tier": "media", "channel": "mail"},
        datetime(2026, 6, 24, tzinfo=timezone.utc),
        datetime(2026, 6, 25, tzinfo=timezone.utc),
    )

    assert [item.title for item in items] == ["OpenAI 发布新模型", "企业 AI Agent 平台发布"]
    assert all(item.source_site == "163新闻邮件" for item in items)
    assert all(item.source_channel == "mail" for item in items)
    assert ("fetch", b"1", "(BODY.PEEK[])") in FakeIMAP.commands
    assert any(command[0] == "_simple_command" and command[1] == "ID" for command in FakeIMAP.commands)


def test_imap_mail_filters_out_non_today_messages(tmp_path, monkeypatch):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)
    FakeIMAP.commands = []
    FakeIMAP.messages = {
        b"1": _mail_bytes(
            "昨天新闻",
            "Tue, 23 Jun 2026 23:30:00 +0800",
            html='<a href="https://example.com/model">OpenAI 发布新模型</a>',
        )
    }
    monkeypatch.setattr("src.domestic_ai_news.imaplib.IMAP4_SSL", FakeIMAP)
    monkeypatch.setenv("MAIL_NEWS_IMAP_USER", "reader@163.com")
    monkeypatch.setenv("MAIL_NEWS_IMAP_PASSWORD", "auth-code")

    items = fetcher._fetch_imap_mail(
        {"name": "163新闻邮件", "kind": "imap_mail"},
        datetime(2026, 6, 24, tzinfo=timezone.utc),
        datetime(2026, 6, 25, tzinfo=timezone.utc),
    )

    assert items == []


def test_extracts_plain_text_mail_news_candidates():
    candidates = DomesticAINewsFetcher._extract_mail_news_candidates(
        "OpenAI 发布新模型 https://example.com/model\n普通生活记录 https://example.com/life",
        False,
    )

    assert candidates == [
        {"title": "OpenAI 发布新模型", "link": "https://example.com/model", "summary": "OpenAI 发布新模型"},
        {"title": "普通生活记录", "link": "https://example.com/life", "summary": "普通生活记录"},
    ]


def test_imap_id_compatibility_errors_are_ignored():
    class MailboxWithoutId:
        def _simple_command(self, *args):
            raise KeyError("ID")

    DomesticAINewsFetcher._send_imap_id(MailboxWithoutId())


def test_keyword_matching_avoids_short_ascii_substrings(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)

    assert fetcher._is_relevant("OpenAI 发布新模型", "")
    assert fetcher._is_relevant("开发者讨论 RAG 工作流", "")
    assert not fetcher._is_relevant("Daily notes from a maintainer", "")


def test_strict_filter_removes_noisy_ithome_items(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)

    assert fetcher._is_relevant(
        "安全公司：部分使用氛围编程 Vibe Coding 开发的网络 App 缺乏身份验证机制",
        "开发者利用 AI 编程工具快速打造应用。",
        source_name="IT之家",
    )
    assert not fetcher._is_relevant(
        "影子图书馆再陷版权风暴，出版商要求彻底封杀安娜档案馆",
        "出版企业要求托管商和域名注册机构封禁盗版网站。",
        source_name="IT之家",
    )


def test_v2ex_strict_filter_blocks_promotions_and_soft_questions(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)

    assert not fetcher._is_relevant(
        "[推广] 新建 Codex 中转站,0.06 倍率消耗,注册送 5 刀",
        "只有 Codex 的 Plus, 分组消耗倍率是 0.06。",
        source_name="V2EX",
    )
    assert not fetcher._is_relevant(
        "[问与答] 一直充的美区 chatgpt plus，有必要换成土区吗",
        "土区价格太诱人了。",
        source_name="V2EX",
    )
    assert not fetcher._is_relevant(
        "[酷工作] base 成都 , 招 前端 React / 后端 Python + go / 中高级运维",
        "业务涉及 AI 应用开发。",
        source_name="V2EX",
    )
    assert fetcher._is_relevant(
        "[分享创造] 做了个 OpenAI-compatible 多模型 API Gateway，求建议",
        "用 Claude Code、Codex、Cursor 时统一 base_url、key 和模型供应商，处理 timeout 和 429。",
        source_name="V2EX",
    )


def test_vehicle_news_is_filtered_unless_infrastructure_related(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)

    assert not fetcher._is_relevant(
        "长安汽车否认采用千里科技智驾方案",
        "自研智能驾驶系统进入量产阶段。",
        source_name="IT之家",
    )
    assert fetcher._is_relevant(
        "理想新一代座舱采用高通 AI 芯片",
        "车载芯片支持本地推理和端侧算力升级。",
        source_name="IT之家",
    )
    assert fetcher._source_accepts(
        {"name": "Official AI", "official": True, "ai_focused": True},
        "Waymo 发布自动驾驶服务更新",
        "主要是运营区域和乘车体验更新。",
    ) is False


def test_consumer_terminal_news_is_filtered_unless_ai_industry_related(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)

    assert not fetcher._is_relevant(
        "OPPO ColorOS 16 六月更新公布：锁屏岛新增酷狗音乐等",
        "AI 流体云新增课程提醒，系统更新将在 6 月底前完成推送。",
        source_name="IT之家",
    )
    assert not fetcher._is_relevant(
        "[macOS] 有没有买了 Mac book Pro M5 的，CPU 温度很容易升高，风扇就狂转",
        "正常浏览网页和 Codex 开发时发热，想问是不是硬件问题。",
        source_name="V2EX",
    )
    assert not fetcher._is_relevant(
        "新款 Android 手机参数曝光：电池和充电规格升级",
        "搭载 AI 拍照功能，售价预计下月公布。",
        source_name="IT之家",
    )
    assert not fetcher._is_relevant(
        "新款 AI PC 迷你主机参数公布",
        "机身内置双风扇，售价和接口规格同步公布。",
        source_name="IT之家",
    )

    assert fetcher._is_relevant(
        "手机厂商发布端侧大模型战略",
        "新系统支持端侧模型、本地推理和 NPU 加速，面向开发者开放 AI 平台。",
        source_name="IT之家",
    )
    assert fetcher._is_relevant(
        "AI 芯片支持本地推理，终端算力平台发布",
        "NPU 提供 120 TOPS 算力，面向端侧大模型应用。",
        source_name="IT之家",
    )
    assert fetcher._is_relevant(
        "AI 红利分配不均：三星存储器部门奖金上涨",
        "三星半导体和芯片代工业务是全球 AI 供应链的重要环节。",
        source_name="IT之家",
    )
    assert fetcher._is_relevant(
        "行业首款开源鸿蒙消费级人形机器人亮相",
        "机器人接入开发者生态，面向具身智能和 AI Agent 场景。",
        source_name="IT之家",
    )
    assert fetcher._is_relevant(
        "企业 AI Agent 平台发布 iOS SDK",
        "平台提供可复用工作流、模型调用 API 和开发者生态能力。",
        source_name="V2EX",
    )


def test_brief_sort_prioritizes_leadership_topics():
    items = [
        NewsItem("1", "2026-05-11", "AI编程", "编程工具", "", "https://example.com/1", "测试", "2026-05-11T12:00:00+00:00"),
        NewsItem("2", "2026-05-11", "政策", "政策新闻", "", "https://example.com/2", "测试", "2026-05-11T08:00:00+00:00"),
        NewsItem("3", "2026-05-11", "运营商", "运营商新闻", "", "https://example.com/3", "测试", "2026-05-11T10:00:00+00:00"),
        NewsItem("4", "2026-05-11", "AI技术", "技术新闻", "", "https://example.com/4", "测试", "2026-05-11T11:00:00+00:00"),
    ]

    sorted_items = DomesticAINewsFetcher._sort_for_brief(items)

    assert [item.type for item in sorted_items] == ["政策", "运营商", "AI技术", "AI编程"]


def test_policy_classification_avoids_generic_planning_mentions(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)

    assert fetcher._classify("工信部发布人工智能行动方案", "推进产业高质量发展") == "政策"
    assert fetcher._classify("科技企业为人工智能发展规划筹措资金", "用于 AI 基础设施建设") != "政策"


def test_leadership_category_maps_telecom_and_infra_topics(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)

    assert fetcher._leadership_category("运营商", "中国电信发布政企 AI 平台", "", "中国电信") == "运营商与央国企动态"
    assert fetcher._leadership_category("算力芯片", "液冷数据中心支撑 AI 算力", "", "测试") == "算力、数据中心与云基础设施"
    assert fetcher._leadership_category("AI Agent", "Agent 工具实践", "", "V2EX") == "技术社区观察"
    assert fetcher._leadership_category("AI模型", "发布新模型", "", "测试") == "AI技术与产业应用"
    assert fetcher._leadership_category("机器人", "人形机器人落地工厂", "", "测试") == "AI技术与产业应用"


def test_nantong_focus_requires_local_and_ai_context(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)

    assert fetcher._is_nantong_ai_result(
        "南通推动人工智能产业发展",
        "崇川区建设大模型创新应用中心。",
    )
    assert fetcher._is_nantong_ai_result(
        "媒体转载：海门智能制造提速",
        "当地企业引入 AI 视觉质检。",
    )
    assert not fetcher._is_nantong_ai_result("南通举办文旅消费活动", "多个景区推出优惠。")
    assert not fetcher._is_nantong_ai_result("人工智能产业政策发布", "推动大模型产业发展。")


def test_legacy_leadership_categories_are_merged():
    for category in [
        "AI模型与智能体技术",
        "行业应用与商业化",
        "AI终端、机器人与硬件",
    ]:
        assert DomesticAINewsFetcher.normalize_leadership_category(category) == "AI技术与产业应用"

    assert DomesticAINewsFetcher.normalize_leadership_category("政策与监管") == "政策与监管"


def test_nantong_category_priority():
    items = [
        NewsItem("1", "2026-06-15", "运营商", "运营商", "", "https://example.com/1", "测试", "2026-06-15T10:00:00+08:00", "运营商与央国企动态"),
        NewsItem("2", "2026-06-15", "AI资讯", "南通", "", "https://example.com/2", "测试", "2026-06-15T09:00:00+08:00", "南通市官方AI动态"),
        NewsItem("3", "2026-06-15", "政策", "政策", "", "https://example.com/3", "测试", "2026-06-15T08:00:00+08:00", "政策与监管"),
    ]

    assert [item.leadership_category for item in DomesticAINewsFetcher._sort_for_brief(items)] == [
        "政策与监管",
        "南通市官方AI动态",
        "运营商与央国企动态",
    ]


def test_wechat_markdown_only_reports_nantong_when_present():
    without_nantong = build_wechat_markdown([], "https://example.com", "2026-06-15")
    assert "南通动态" not in without_nantong
    assert "南通市官方AI动态" not in without_nantong

    item = NewsItem(
        "1",
        "2026-06-15",
        "AI资讯",
        "南通发布人工智能产业新举措",
        "",
        "https://example.com/1",
        "南通日报",
        "2026-06-15T09:00:00+08:00",
        "南通市官方AI动态",
    )
    with_nantong = build_wechat_markdown([item], "https://example.com", "2026-06-15")
    assert "南通动态：<font color=\"comment\">1 条</font>，南通发布人工智能产业新举措" in with_nantong
    assert "南通市官方AI动态：" not in with_nantong


def test_extracts_baidu_news_result(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"feeds": [], "searches": []}), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)
    html = """
    <div class="result">
      <h3><a href="https://example.com/news">江苏推进人工智能产业政策</a></h3>
      <div>人民网 2小时前 江苏发布人工智能相关政策，支持大模型应用。</div>
    </div>
    """

    results = fetcher._extract_baidu_results(BeautifulSoup(html, "html.parser"))

    assert results == [{
        "title": "江苏推进人工智能产业政策",
        "link": "https://example.com/news",
        "summary": "江苏发布人工智能相关政策，支持大模型应用。",
        "source": "人民网",
        "date": "2小时前",
    }]


def test_page_generator_writes_data(tmp_path):
    docs_dir = tmp_path / "docs"
    outputs = PageGenerator(docs_dir, latest_path=tmp_path / "latest.json").write([])

    assert outputs["data"].exists()
    assert outputs["latest"].exists()
    assert outputs["index"].exists()
    payload = json.loads(outputs["data"].read_text(encoding="utf-8"))
    assert payload["count"] == 0


def test_page_generator_merges_daily_archive(tmp_path):
    docs_dir = tmp_path / "docs"
    generator = PageGenerator(docs_dir, latest_path=tmp_path / "latest.json")
    first = NewsItem(
        "1",
        "2026-05-17",
        "政策",
        "政策新闻",
        "摘要",
        "https://example.com/1",
        "测试",
        "2026-05-17T09:00:00+08:00",
        "政策与监管",
    )
    second = NewsItem(
        "2",
        "2026-05-17",
        "AI模型",
        "模型新闻",
        "摘要",
        "https://example.com/2",
        "测试",
        "2026-05-17T10:00:00+08:00",
        "AI技术与产业应用",
    )

    generator.write_daily([first])
    generator.write_daily([first, second])

    archive = json.loads((docs_dir / "archive" / "2026-05-17.json").read_text(encoding="utf-8"))
    index = json.loads((docs_dir / "archive" / "index.json").read_text(encoding="utf-8"))
    assert archive["count"] == 2
    assert index["latest_date"] == "2026-05-17"
    assert index["dates"][0]["count"] == 2


def test_html_official_source_parses_entries(tmp_path):
    now = datetime.now(timezone.utc)
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"sources": []}), encoding="utf-8")
    source = {
        "name": "Official AI",
        "kind": "html",
        "url": "https://example.com/news",
        "official": True,
        "ai_focused": True,
        "organization": "Example AI",
        "language": "en",
        "item_selector": "article",
    }
    html = f"""
    <article>
      <h2>New multimodal model</h2>
      <a href="/news/model">Read</a>
      <p>A model and API update.</p>
      <time datetime="{now.isoformat()}"></time>
    </article>
    """

    async def run():
        fetcher = DomesticAINewsFetcher(config_path)
        transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetcher._fetch_html(client, source, now - timedelta(hours=1))

    items = asyncio.run(run())
    assert len(items) == 1
    assert items[0].detail_link == "https://example.com/news/model"
    assert items[0].source_tier == "official"
    assert items[0].language == "en"


def test_huggingface_adapter_builds_official_model_item(tmp_path):
    now = datetime.now(timezone.utc)
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"sources": []}), encoding="utf-8")
    source = {
        "name": "Qwen Hugging Face",
        "kind": "huggingface_api",
        "organization": "Qwen",
        "official": True,
        "source_tier": "official",
        "channel": "model-release",
    }

    async def run():
        payload = [{"modelId": "Qwen/Qwen-Test", "lastModified": now.isoformat(), "tags": ["text-generation"]}]
        fetcher = DomesticAINewsFetcher(config_path)
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetcher._fetch_huggingface(client, source, now - timedelta(hours=1))

    items = asyncio.run(run())
    assert items[0].title == "Qwen 发布模型 Qwen-Test"
    assert items[0].source_channel == "model-release"
    assert items[0].type == "AI模型"


def test_dedupe_prefers_official_source_and_normalizes_tracking_urls():
    media = NewsItem(
        "media", "2026-06-15", "AI模型", "OpenAI releases Model X", "",
        "https://news.example/model-x?utm_source=test", "Media",
        "2026-06-15T12:00:00+00:00", source_tier="media",
    )
    official = NewsItem(
        "official", "2026-06-15", "AI模型", "OpenAI releases Model X", "",
        "https://openai.com/model-x", "OpenAI",
        "2026-06-15T10:00:00+00:00", source_tier="official",
    )

    assert DomesticAINewsFetcher._dedupe([media, official]) == [official]
    assert DomesticAINewsFetcher._canonical_url("https://x.test/a/?utm_source=y") == "https://x.test/a"


def test_first_seen_date_is_persisted(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({"sources": []}), encoding="utf-8")
    first = DomesticAINewsFetcher(config_path)
    first_seen = first._first_seen_at("https://example.com/undated")
    first._save_state()

    second = DomesticAINewsFetcher(config_path)
    assert second._first_seen_at("https://example.com/undated") == first_seen


def test_health_summary_flags_consecutive_official_failures(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps({
        "health_alert_threshold": 2,
        "sources": [{"name": "Official", "kind": "feed", "url": "https://example.com", "official": True}],
    }), encoding="utf-8")
    fetcher = DomesticAINewsFetcher(config_path)
    fetcher._record_health("Official", "feed", False, 0, "broken")
    fetcher._record_health("Official", "feed", False, 0, "broken")

    summary = fetcher.health_summary()
    assert summary["official_failing"] == 1
    assert summary["alert_sources"] == ["Official"]


def test_static_ui_and_schedule_include_new_contracts():
    root = Path(__file__).parents[1]
    script = (root / "docs/assets/js/ai-news.js").read_text(encoding="utf-8")
    today = (root / "docs/ai-news.html").read_text(encoding="utf-8")
    cron = (root / "deploy/ai-daily-brief.cron").read_text(encoding="utf-8")
    runner = (root / "scripts/run_daily.sh").read_text(encoding="utf-8")
    notifier = (root / "scripts/send_daily_notification.sh").read_text(encoding="utf-8")

    assert "aria-expanded" in script
    assert "category-nav-list" in today
    assert "摘要" in script
    assert "领导摘要" not in script
    assert "版本 V1.0.2" in today
    assert "site-footer" in today
    assert "source-health" not in today
    assert "category-overview" not in today
    assert "source-health.json" not in script
    assert "alwaysVisibleCategories" not in script
    assert "return fromHash || ''" in script
    assert "0 0,16 * * *" in cron
    assert "50 8 * * *" in cron
    assert "0 9 * * *" in cron
    assert "--days 2" in runner
    assert "--notify" not in runner
    assert "--notify-only" in notifier


def test_daily_notification_state_prevents_duplicate_send(tmp_path):
    config_path = tmp_path / "sources.json"
    config_path.write_text("{}", encoding="utf-8")
    report_date = datetime(2026, 6, 15).date()

    assert not _notification_sent(report_date, str(config_path))
    _mark_notification_sent(report_date, str(config_path))
    assert _notification_sent(report_date, str(config_path))


def test_notify_from_archive_requires_webhook(tmp_path, monkeypatch):
    report_date = datetime(2026, 6, 15).date()
    docs_dir = tmp_path / "docs"
    archive_dir = docs_dir / "archive"
    archive_dir.mkdir(parents=True)
    (archive_dir / "2026-06-15.json").write_text(
        json.dumps({"items": []}),
        encoding="utf-8",
    )
    config_path = tmp_path / "sources.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.delenv("WECHAT_WEBHOOK_URL", raising=False)

    result = asyncio.run(notify_from_archive(
        report_date,
        str(config_path),
        str(docs_dir),
        "https://example.com",
    ))

    assert result == {
        "success": False,
        "sent": False,
        "reason": "WECHAT_WEBHOOK_URL is not set",
    }


def test_notify_from_archive_sends_same_content_to_formal_and_test_webhooks(tmp_path, monkeypatch):
    report_date = datetime(2026, 6, 15).date()
    docs_dir = tmp_path / "docs"
    archive_dir = docs_dir / "archive"
    archive_dir.mkdir(parents=True)
    item = NewsItem(
        "1",
        "2026-06-15",
        "AI模型",
        "OpenAI 发布新模型",
        "",
        "https://example.com/1",
        "OpenAI",
        "2026-06-15T09:00:00+08:00",
    )
    (archive_dir / "2026-06-15.json").write_text(
        json.dumps({"items": [item.__dict__]}),
        encoding="utf-8",
    )
    config_path = tmp_path / "sources.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "https://example.com/formal")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL_TEST", "https://example.com/test")
    sent = []

    async def fake_send(webhook_url, content):
        sent.append((webhook_url, content))
        return {"errcode": 0, "errmsg": "ok"}

    monkeypatch.setattr(main_module, "send_wechat_markdown", fake_send)

    result = asyncio.run(notify_from_archive(
        report_date,
        str(config_path),
        str(docs_dir),
        "https://brief.example.com",
    ))

    assert result["success"] is True
    assert result["sent"] is True
    assert result["targets"] == 2
    assert [target for target, _ in sent] == ["https://example.com/formal", "https://example.com/test"]
    assert not sent[0][1].startswith("【企业微信测试渠道】")
    assert sent[1][1] == "【企业微信测试渠道】\n" + sent[0][1]
    assert "OpenAI 发布新模型" in sent[0][1]
