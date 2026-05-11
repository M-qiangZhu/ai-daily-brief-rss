import asyncio
import json
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from src.domestic_ai_news import DomesticAINewsFetcher, NewsItem
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
    payload = json.loads(outputs["data"].read_text(encoding="utf-8"))
    assert payload["count"] == 0
