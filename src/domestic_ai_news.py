"""Domestic AI news retrieval and normalization."""

from __future__ import annotations

import asyncio
import calendar
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlparse, urlunparse
from zoneinfo import ZoneInfo

import feedparser
import httpx
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, text/xml, text/html, */*",
}

KEYWORDS = [
    "AI",
    "人工智能",
    "AIGC",
    "AGI",
    "GenAI",
    "生成式AI",
    "大模型",
    "基础模型",
    "推理模型",
    "智能体",
    "Agent",
    "多模态",
    "机器学习",
    "深度学习",
    "神经网络",
    "Reasoning",
    "Inference",
    "Fine-tuning",
    "RAG",
    "Embedding",
    "向量数据库",
    "LLM",
    "VLM",
    "SLM",
    "MoE",
    "Transformer",
    "Diffusion",
    "世界模型",
    "World Model",
    "Context Window",
    "Long Context",
    "Chain of Thought",
    "CoT",
    "Test Time Compute",
    "TTC",
    "MCP",
    "Function Calling",
    "Tool Use",
    "Agentic",
    "Memory Layer",
    "Test-Time Scaling",
    "Vibe Coding",
    "AI Coding",
    "AI编程",
    "Copilot",
    "Cursor",
    "Windsurf",
    "Codeium",
    "Trae",
    "Lovable",
    "Bolt",
    "Replit",
    "Devin",
    "Code Agent",
    "Claude Code",
    "OpenHands",
    "Cline",
    "Roo Code",
    "Aider",
    "Continue",
    "Codex",
    "AI Agent",
    "Autonomous Agent",
    "Multi-Agent",
    "Workflow",
    "CrewAI",
    "LangGraph",
    "AutoGen",
    "OpenManus",
    "Dify",
    "n8n",
    "Flowise",
    "OpenClaw",
    "Browser Use",
    "Computer Use",
    "A2A",
    "Agent2Agent",
    "OpenAI",
    "ChatGPT",
    "GPT-4",
    "GPT-4o",
    "GPT-5",
    "GPT-5.5",
    "o1",
    "o3",
    "Operator",
    "Sora",
    "OpenAI API",
    "Anthropic",
    "Claude",
    "Claude Sonnet",
    "Claude Opus",
    "Gemini",
    "Gemma",
    "Google DeepMind",
    "DeepMind",
    "NotebookLM",
    "AlphaFold",
    "Project Astra",
    "DeepSeek",
    "DeepSeek-R1",
    "通义千问",
    "Qwen",
    "豆包",
    "Kimi",
    "Moonshot",
    "智谱",
    "GLM",
    "文心一言",
    "讯飞星火",
    "混元",
    "百川",
    "MiniMax",
    "零一万物",
    "StepFun",
    "华为",
    "华为昇腾",
    "Ascend",
    "910B",
    "910C",
    "昇腾",
    "MindSpore",
    "盘古",
    "鲲鹏",
    "CANN",
    "华为云AI",
    "Atlas",
    "NVIDIA",
    "CUDA",
    "Blackwell",
    "H100",
    "H200",
    "B200",
    "GB200",
    "DGX",
    "NVLink",
    "TensorRT",
    "NIM",
    "RTX 5090",
    "RTX PRO",
    "GPU集群",
    "算力",
    "推理加速",
    "边缘AI",
    "液冷",
    "AMD AI",
    "MI300",
    "Intel Gaudi",
    "TPU",
    "ASIC",
    "自动驾驶",
    "智能驾驶",
    "端到端智驾",
    "FSD",
    "Robotaxi",
    "Waymo",
    "Tesla AI",
    "智驾",
    "BEV",
    "Occupancy",
    "VLA",
    "人形机器人",
    "具身智能",
    "Embodied AI",
    "Figure AI",
    "Unitree",
    "宇树",
    "Spatial Intelligence",
    "AI PC",
    "AI手机",
    "AI眼镜",
    "智能设备",
    "AI耳机",
    "智能穿戴",
    "XR",
    "AR",
    "MR",
    "Vision Pro",
    "Token",
    "Tokens",
    "API调用",
    "上下文窗口",
    "Context Length",
    "Prompt",
    "Prompt Engineering",
    "推理成本",
    "Inference Cost",
    "Token Cost",
    "蒸馏",
    "Distillation",
    "Benchmark",
    "Arena",
    "MMLU",
    "AI融资",
    "AI创业",
    "AI独角兽",
    "AI估值",
    "AI Infra",
    "AI SaaS",
    "企业AI",
    "AI应用",
    "AI搜索",
    "AI浏览器",
    "AI安全",
    "模型对齐",
    "Alignment",
    "版权",
    "深度伪造",
    "Deepfake",
    "AI监管",
    "欧盟AI法案",
    "江苏",
    "工信部",
    "国家数据局",
    "中国电信",
    "中国移动",
    "中国联通",
]

STRONG_AI_KEYWORDS = [
    "AI",
    "AIGC",
    "AGI",
    "GenAI",
    "人工智能",
    "生成式AI",
    "大模型",
    "基础模型",
    "推理模型",
    "智能体",
    "AI Agent",
    "LLM",
    "VLM",
    "MoE",
    "RAG",
    "Transformer",
    "Diffusion",
    "Vibe Coding",
    "AI Coding",
    "AI编程",
    "Copilot",
    "Cursor",
    "Windsurf",
    "Claude Code",
    "Codex",
    "OpenAI",
    "ChatGPT",
    "Claude",
    "Gemini",
    "DeepSeek",
    "Qwen",
    "通义千问",
    "豆包",
    "Kimi",
    "GLM",
    "NVIDIA",
    "CUDA",
    "Blackwell",
    "昇腾",
    "算力",
    "自动驾驶",
    "智能驾驶",
    "具身智能",
    "人形机器人",
    "AI PC",
    "AI手机",
    "AI眼镜",
    "AI安全",
    "AI监管",
]

STRICT_FEED_SOURCES = {"IT之家", "V2EX"}

V2EX_BLOCKED_TITLE_PATTERNS = [
    "[推广]",
    "[酷工作]",
    "中转",
    "充值",
    "注册送",
    "回贴送",
    "接码",
    "土区",
    "美区",
    "外网的卡",
    "plus 首月",
    "$0plus",
    "付费了",
    "宣传",
]

V2EX_NOISY_NODES = ["[分享发现]", "[程序员]", "[问与答]"]

V2EX_TECH_CONTEXT = [
    "开发",
    "代码",
    "编程",
    "工具",
    "开源",
    "项目",
    "api",
    "gateway",
    "agent",
    "模型",
    "智能体",
    "prompt",
    "token",
    "workflow",
    "自动化",
    "机器码",
    "vibe coding",
]

TYPE_PRIORITY = {
    "政策": 0,
    "运营商": 1,
    "算力芯片": 2,
    "AI技术": 3,
    "AI模型": 4,
    "AI Agent": 5,
    "智能驾驶": 6,
    "机器人": 7,
    "AI硬件": 8,
    "AI安全": 9,
    "AI编程": 10,
    "AI资讯": 11,
}

LEADERSHIP_CATEGORY_PRIORITY = {
    "政策与监管": 0,
    "南通市官方AI动态": 1,
    "运营商与央国企动态": 2,
    "算力、数据中心与云基础设施": 3,
    "AI技术与产业应用": 4,
    "投融资与竞争格局": 5,
    "风险、安全与合规": 6,
    "技术社区观察": 7,
}

NANTONG_TERMS = [
    "南通",
    "通城",
    "崇川",
    "通州",
    "海门",
    "如皋",
    "启东",
    "海安",
    "如东",
    "南通开发区",
    "苏锡通",
    "通州湾",
]

NANTONG_AI_TERMS = [
    "AI",
    "人工智能",
    "大模型",
    "智能体",
    "生成式",
    "算力",
    "智算",
    "机器人",
    "具身智能",
    "数字政府",
    "智能制造",
    "智慧城市",
    "机器学习",
    "深度学习",
]

LEGACY_LEADERSHIP_CATEGORIES = {
    "AI模型与智能体技术",
    "行业应用与商业化",
    "AI终端、机器人与硬件",
}


@dataclass
class NewsItem:
    """A normalized AI news item for the daily page."""

    id: str
    date: str
    type: str
    title: str
    content_summary: str
    detail_link: str
    source_site: str
    published_at: str
    leadership_category: str = "AI技术与产业应用"
    organization: str = ""
    language: str = "zh"
    source_tier: str = "media"
    source_channel: str = "feed"


class DomesticAINewsFetcher:
    """Fetch and normalize AI news from official, media, and community sources."""

    def __init__(self, config_path: str | Path = "data/sources.json"):
        self.config_path = Path(config_path)
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        state_dir = Path(self.config.get("state_dir", self.config_path.parent / "state"))
        if not state_dir.is_absolute():
            state_dir = self.config_path.parent.parent / state_dir
        self.state_dir = state_dir
        self.health_path = state_dir / "source_health.json"
        self.first_seen_path = state_dir / "first_seen.json"
        self.health = self._load_json(self.health_path, {"sources": {}})
        self.first_seen = self._load_json(self.first_seen_path, {})

    async def fetch(self, days: int = 1, tz_name: str = "Asia/Shanghai") -> list[NewsItem]:
        local_tz = ZoneInfo(tz_name)
        since = datetime.now(local_tz).astimezone(timezone.utc) - timedelta(days=days)
        return await self._fetch_between(since, None, local_tz)

    async def fetch_date(self, target_date: date, tz_name: str = "Asia/Shanghai") -> list[NewsItem]:
        local_tz = ZoneInfo(tz_name)
        start = datetime.combine(target_date, time.min, tzinfo=local_tz)
        end = datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=local_tz)
        return await self._fetch_between(
            start.astimezone(timezone.utc),
            end.astimezone(timezone.utc),
            local_tz,
        )

    async def _fetch_between(
        self,
        since: datetime,
        until: datetime | None,
        local_tz: ZoneInfo,
    ) -> list[NewsItem]:
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, headers=HEADERS) as client:
            sources = self._configured_sources()
            results = await asyncio.gather(
                *[
                    self._fetch_source(client, source, since, until, local_tz)
                    for source in sources
                    if source.get("enabled", True)
                ],
                return_exceptions=True,
            )

        items: list[NewsItem] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            items.extend(result)

        self._save_state()
        return self._apply_tier_limits(self._dedupe(items))

    def _configured_sources(self) -> list[dict]:
        if self.config.get("sources"):
            return [dict(source) for source in self.config["sources"]]
        sources = []
        for source in self.config.get("feeds", []):
            sources.append({"kind": "feed", **source})
        for source in self.config.get("searches", []):
            sources.append({"kind": "baidu_news", **source})
        return sources

    async def _fetch_source(
        self,
        client: httpx.AsyncClient,
        source: dict,
        since: datetime,
        until: datetime | None,
        local_tz: ZoneInfo,
    ) -> list[NewsItem]:
        name = source.get("name", source.get("url", "unknown"))
        kind = source.get("kind", "feed")
        try:
            if kind in {"feed", "github_atom"}:
                items = await self._fetch_feed(client, source, since, until, local_tz)
            elif kind == "html":
                items = await self._fetch_html(client, source, since, until, local_tz)
            elif kind == "huggingface_api":
                items = await self._fetch_huggingface(client, source, since, until, local_tz)
            elif kind == "baidu_news":
                items = await self._fetch_baidu_news(client, source, since, until, local_tz)
            else:
                raise ValueError(f"Unsupported source kind: {kind}")
            self._record_health(name, kind, True, len(items))
            return items
        except Exception as exc:
            self._record_health(name, kind, False, 0, str(exc))
            return []

    async def _fetch_feed(
        self,
        client: httpx.AsyncClient,
        source: dict,
        since: datetime,
        until: datetime | None = None,
        local_tz: ZoneInfo | None = None,
    ) -> list[NewsItem]:
        local_tz = local_tz or ZoneInfo("Asia/Shanghai")
        response = await client.get(source["url"], follow_redirects=True)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        if feed.bozo and not feed.entries:
            raise ValueError(str(feed.bozo_exception))

        items: list[NewsItem] = []
        for entry in feed.entries[: source.get("max_entries", 20)]:
            link = entry.get("link", source["url"])
            published_at = self._parse_feed_date(entry) or self._first_seen_at(link)
            if published_at < since or (until and published_at >= until):
                continue

            title = self._clean_text(entry.get("title", ""))
            summary = self._summary(self._entry_content(entry) or title)
            if not self._source_accepts(source, title, summary):
                continue

            items.append(self._make_item(
                title=title,
                link=link,
                summary=summary,
                source_site=source.get("name", self._host(link)),
                published_at=published_at,
                category=source.get("category"),
                local_tz=local_tz,
                leadership_category=source.get("leadership_category"),
                source=source,
            ))

        return items

    async def _fetch_html(
        self,
        client: httpx.AsyncClient,
        source: dict,
        since: datetime,
        until: datetime | None = None,
        local_tz: ZoneInfo | None = None,
    ) -> list[NewsItem]:
        local_tz = local_tz or ZoneInfo("Asia/Shanghai")
        response = await client.get(source["url"], follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        item_selector = source.get("item_selector", "article")
        items = []
        for block in soup.select(item_selector)[: source.get("max_entries", 20)]:
            link_el = block.select_one(source.get("link_selector", "a[href]"))
            title_el = block.select_one(source.get("title_selector", "h2, h3, a[href]"))
            if not link_el or not title_el:
                continue
            link = urljoin(str(response.url), link_el.get("href", ""))
            title = self._clean_text(title_el.get_text(" ", strip=True))
            summary_el = block.select_one(source.get("summary_selector", "p"))
            summary = self._summary(
                summary_el.get_text(" ", strip=True) if summary_el else block.get_text(" ", strip=True)
            )
            date_el = block.select_one(source.get("date_selector", "time"))
            date_value = ""
            if date_el:
                date_value = date_el.get(source.get("date_attribute", "datetime"), "") or date_el.get_text(" ", strip=True)
            published_at = self._parse_datetime(date_value) or self._first_seen_at(link)
            if published_at < since or (until and published_at >= until):
                continue
            if not self._is_valid_result(title, link) or not self._source_accepts(source, title, summary):
                continue
            items.append(self._make_item(
                title=title,
                link=link,
                summary=summary or title,
                source_site=source.get("name", self._host(link)),
                published_at=published_at,
                category=source.get("category"),
                local_tz=local_tz,
                leadership_category=source.get("leadership_category"),
                source=source,
            ))
        return items

    async def _fetch_huggingface(
        self,
        client: httpx.AsyncClient,
        source: dict,
        since: datetime,
        until: datetime | None = None,
        local_tz: ZoneInfo | None = None,
    ) -> list[NewsItem]:
        local_tz = local_tz or ZoneInfo("Asia/Shanghai")
        organization = source["organization"]
        endpoint = source.get("url", "https://huggingface.co/api/models")
        response = await client.get(
            endpoint,
            params={
                "author": organization,
                "sort": "lastModified",
                "direction": -1,
                "limit": source.get("max_entries", 20),
                "full": "false",
            },
            follow_redirects=True,
        )
        response.raise_for_status()
        items = []
        for model in response.json():
            model_id = model.get("modelId") or model.get("id")
            if not model_id:
                continue
            link = f"https://huggingface.co/{model_id}"
            published_at = self._parse_datetime(model.get("lastModified", "")) or self._first_seen_at(link)
            if published_at < since or (until and published_at >= until):
                continue
            tags = ", ".join(model.get("tags", [])[:8])
            title = f"{organization} 发布模型 {model_id.split('/')[-1]}"
            summary = self._summary(f"Hugging Face model update. {tags}".strip())
            items.append(self._make_item(
                title=title,
                link=link,
                summary=summary,
                source_site=source.get("name", f"{organization} Hugging Face"),
                published_at=published_at,
                category=source.get("category", "AI模型"),
                local_tz=local_tz,
                source=source,
            ))
        return items

    async def _fetch_baidu_news(
        self,
        client: httpx.AsyncClient,
        source: dict,
        since: datetime,
        until: datetime | None = None,
        local_tz: ZoneInfo | None = None,
    ) -> list[NewsItem]:
        local_tz = local_tz or ZoneInfo("Asia/Shanghai")
        response = await client.get(self._baidu_url(source["query"]), follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        items: list[NewsItem] = []
        for result in self._extract_baidu_results(soup)[: source.get("max_results", 10)]:
            if not self._is_valid_result(result["title"], result["link"]):
                continue

            published_at = (
                self._parse_cn_time(result["date"])
                or self._parse_cn_time(result["summary"])
                or self._first_seen_at(result["link"])
            )
            if published_at < since or (until and published_at >= until):
                continue

            summary = self._summary(result["summary"] or result["title"])
            if source.get("local_focus") == "nantong" and not self._is_nantong_ai_result(
                result["title"],
                summary,
            ):
                continue
            if not self._source_accepts(source, result["title"], summary):
                continue
            items.append(self._make_item(
                title=result["title"],
                link=result["link"],
                summary=summary,
                source_site=result["source"] or self._host(result["link"]),
                published_at=published_at,
                category=source.get("category"),
                local_tz=local_tz,
                leadership_category=source.get("leadership_category"),
                source=source,
            ))

        return items

    def _make_item(
        self,
        title: str,
        link: str,
        summary: str,
        source_site: str,
        published_at: datetime,
        category: str | None,
        local_tz: ZoneInfo | None = None,
        leadership_category: str | None = None,
        source: dict | None = None,
    ) -> NewsItem:
        source = source or {}
        local_tz = local_tz or ZoneInfo("Asia/Shanghai")
        local_published_at = published_at.astimezone(local_tz)
        news_type = category or self._classify(title, summary)
        leadership_category = leadership_category or self._leadership_category(news_type, title, summary, source_site)
        return NewsItem(
            id=hashlib.sha1(f"{title}|{link}".encode("utf-8")).hexdigest()[:16],
            date=local_published_at.date().isoformat(),
            type=news_type,
            title=title,
            content_summary=summary,
            detail_link=link,
            source_site=source_site,
            published_at=local_published_at.isoformat(),
            leadership_category=leadership_category,
            organization=source.get("organization", source_site),
            language=source.get("language", self._detect_language(title, summary)),
            source_tier=source.get("source_tier", "official" if source.get("official") else "media"),
            source_channel=source.get("channel", source.get("kind", "feed")),
        )

    @staticmethod
    def _baidu_url(query: str) -> str:
        return f"http://www.baidu.com/s?tn=news&rtt=1&bsst=1&wd={quote_plus(query)}"

    def _extract_baidu_results(self, soup: BeautifulSoup) -> list[dict]:
        results = []
        for block in soup.select(".result, .result-op, .c-container"):
            link_el = block.select_one("h3 a, .news-title_1YtI1 a, a")
            if not link_el:
                continue

            link = link_el.get("href", "").strip()
            title = self._clean_text(link_el.get_text(" ", strip=True))
            if not title or not link.startswith(("http://", "https://")):
                continue

            text = self._clean_text(block.get_text(" ", strip=True))
            summary = text.replace(title, "", 1).strip()
            source = ""
            date = ""
            meta = re.search(
                r"([\u4e00-\u9fa5A-Za-z0-9_.-]{2,20})\s+((?:\d{4}年\d{1,2}月\d{1,2}日)|(?:\d{1,2}月\d{1,2}日)|(?:\d+\s*(?:分钟|小时|天)前))",
                summary,
            )
            if meta:
                source = meta.group(1)
                date = meta.group(2)
                summary = summary.replace(meta.group(0), "", 1).strip()
            if not source:
                source_match = re.search(r"\s([\u4e00-\u9fa5A-Za-z0-9_.-]{2,20})$", summary)
                if source_match:
                    source = source_match.group(1)
                    summary = summary[: source_match.start()].strip()

            results.append({
                "title": title,
                "link": link,
                "summary": summary,
                "source": source,
                "date": date,
            })
        return results

    @staticmethod
    def _parse_feed_date(entry: dict) -> datetime | None:
        for field in ("published", "updated", "created"):
            try:
                parsed = entry.get(f"{field}_parsed")
                if parsed:
                    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
                if entry.get(field):
                    dt = parsedate_to_datetime(entry[field])
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
        return None

    @staticmethod
    def _parse_cn_time(value: str) -> datetime | None:
        text = (value or "").strip()
        now = datetime.now(timezone.utc)
        relative = re.search(r"(\d+)\s*(分钟|小时|天)前", text)
        if relative:
            amount = int(relative.group(1))
            unit = relative.group(2)
            if unit == "分钟":
                return now - timedelta(minutes=amount)
            if unit == "小时":
                return now - timedelta(hours=amount)
            return now - timedelta(days=amount)

        match = re.search(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日", text)
        if not match:
            return None
        year = int(match.group(1) or now.year)
        month = int(match.group(2))
        day = int(match.group(3))
        dt = datetime(year, month, day, tzinfo=timezone.utc)
        if not match.group(1) and dt > now + timedelta(days=1):
            dt = datetime(year - 1, month, day, tzinfo=timezone.utc)
        return dt

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            normalized = text.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        try:
            parsed = parsedate_to_datetime(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return DomesticAINewsFetcher._parse_cn_time(text)

    @staticmethod
    def _entry_content(entry: dict) -> str:
        if entry.get("summary"):
            return DomesticAINewsFetcher._clean_text(entry.summary)
        if entry.get("description"):
            return DomesticAINewsFetcher._clean_text(entry.description)
        if entry.get("content"):
            return DomesticAINewsFetcher._clean_text(entry.content[0].get("value", ""))
        return ""

    @staticmethod
    def _clean_text(value: str) -> str:
        text = BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _detect_language(title: str, summary: str) -> str:
        text = f"{title}{summary}"
        chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
        latin = len(re.findall(r"[A-Za-z]", text))
        return "zh" if chinese >= max(4, latin // 5) else "en"

    def _source_accepts(self, source: dict, title: str, summary: str) -> bool:
        if source.get("official") and source.get("ai_focused", True):
            return True
        return self._is_relevant(title, summary, source.get("keywords"), source.get("name", ""))

    @classmethod
    def _summary(cls, value: str, max_chars: int = 320) -> str:
        text = cls._clean_text(value)
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1].rstrip() + "…"

    @staticmethod
    def _classify(title: str, summary: str) -> str:
        text = f"{title}\n{summary}".lower()
        if DomesticAINewsFetcher._looks_like_policy(text):
            return "政策"
        rules = [
            ("运营商", ["中国电信", "中国移动", "中国联通", "运营商", "天翼", "移动云", "联通云"]),
            ("AI编程", ["ai coding", "ai编程", "vibe coding", "copilot", "cursor", "windsurf", "claude code", "codex", "devin", "cline", "aider"]),
            ("AI Agent", ["智能体", "agent", "multi-agent", "workflow", "langgraph", "autogen", "dify", "mcp", "function calling", "tool use"]),
            ("AI模型", ["大模型", "基础模型", "推理模型", "llm", "vlm", "slm", "deepseek", "通义", "qwen", "豆包", "kimi", "glm", "claude", "gemini", "gpt"]),
            ("算力芯片", ["算力", "nvidia", "cuda", "blackwell", "h100", "h200", "b200", "gb200", "昇腾", "ascend", "gpu", "tpu", "mi300", "芯片"]),
            ("机器人", ["机器人", "具身智能", "embodied ai", "figure ai", "unitree", "宇树", "spatial intelligence"]),
            ("智能驾驶", ["自动驾驶", "智能驾驶", "端到端智驾", "fsd", "robotaxi", "waymo", "tesla ai", "智驾", "bev", "occupancy"]),
            ("AI硬件", ["ai pc", "ai手机", "ai眼镜", "智能设备", "ai耳机", "智能穿戴", "xr", "ar", "mr", "vision pro"]),
            ("AI安全", ["ai安全", "模型对齐", "alignment", "深度伪造", "deepfake", "ai监管", "欧盟ai法案", "版权"]),
            ("AI技术", ["多模态", "机器学习", "深度学习", "算法", "训练", "推理", "rag", "embedding", "向量数据库", "transformer", "diffusion"]),
        ]
        for label, keywords in rules:
            if any(keyword.lower() in text for keyword in keywords):
                return label
        return "AI资讯"

    @staticmethod
    def _looks_like_policy(text: str) -> bool:
        direct_terms = ["政策", "通知", "办法", "国家数据局", "工信厅", "行动方案", "实施方案", "政务"]
        if any(term in text for term in direct_terms):
            return True
        return bool(re.search(r"(工信部|国家数据局).{0,16}(发布|印发|通知|部署|组织|征求|开展)", text))

    @staticmethod
    def _leadership_category(news_type: str, title: str, summary: str, source_site: str) -> str:
        text = f"{title}\n{summary}\n{source_site}".lower()
        if source_site == "V2EX":
            return "技术社区观察"
        if news_type == "政策":
            return "政策与监管"
        if news_type == "运营商" or any(keyword in text for keyword in ["中国电信", "中国移动", "中国联通", "运营商", "央企", "国资"]):
            return "运营商与央国企动态"
        if news_type == "算力芯片" or any(keyword in text for keyword in ["算力", "数据中心", "云计算", "云服务", "云基础设施", "云网", "gpu", "nvidia", "昇腾", "边缘ai", "液冷"]):
            return "算力、数据中心与云基础设施"
        if news_type == "AI安全" or any(keyword in text for keyword in ["安全", "合规", "监管", "对齐", "deepfake", "版权"]):
            return "风险、安全与合规"
        if any(keyword in text for keyword in ["融资", "估值", "ipo", "资本", "基金", "投资", "市场"]):
            return "投融资与竞争格局"
        return "AI技术与产业应用"

    @staticmethod
    def _is_nantong_ai_result(title: str, summary: str) -> bool:
        text = f"{title}\n{summary}".lower()
        has_nantong_context = any(term.lower() in text for term in NANTONG_TERMS)
        has_ai_context = any(
            DomesticAINewsFetcher._keyword_matches(text, term)
            for term in NANTONG_AI_TERMS
        )
        return has_nantong_context and has_ai_context

    @staticmethod
    def normalize_leadership_category(category: str) -> str:
        if category in LEGACY_LEADERSHIP_CATEGORIES:
            return "AI技术与产业应用"
        return category or "AI技术与产业应用"

    @staticmethod
    def _is_relevant(
        title: str,
        summary: str,
        keywords: Iterable[str] | None = None,
        source_name: str = "",
    ) -> bool:
        haystack = f"{title}\n{summary}".lower()
        matched = DomesticAINewsFetcher._matched_keywords(haystack, keywords or KEYWORDS)
        if not matched:
            return False
        if source_name not in STRICT_FEED_SOURCES:
            return True
        return DomesticAINewsFetcher._passes_strict_feed_filter(title, summary, source_name, matched)

    @staticmethod
    def _passes_strict_feed_filter(
        title: str,
        summary: str,
        source_name: str,
        matched_keywords: list[str],
    ) -> bool:
        title_text = title.lower()
        body_text = f"{title}\n{summary}".lower()
        strong_matches = DomesticAINewsFetcher._matched_keywords(body_text, STRONG_AI_KEYWORDS)
        strong_title_matches = DomesticAINewsFetcher._matched_keywords(title_text, STRONG_AI_KEYWORDS)

        if source_name == "V2EX":
            if any(pattern.lower() in title_text for pattern in V2EX_BLOCKED_TITLE_PATTERNS):
                return False
            if any(node.lower() in title_text for node in V2EX_NOISY_NODES):
                has_tech_context = any(keyword.lower() in body_text for keyword in V2EX_TECH_CONTEXT)
                return len(strong_matches) >= 2 and has_tech_context
            return bool(strong_matches)

        if source_name == "IT之家":
            if strong_title_matches:
                return True
            return len(strong_matches) >= 2 or (len(strong_matches) >= 1 and len(matched_keywords) >= 3)

        return bool(strong_matches)

    @staticmethod
    def _matched_keywords(haystack: str, keywords: Iterable[str]) -> list[str]:
        return [keyword for keyword in keywords if DomesticAINewsFetcher._keyword_matches(haystack, keyword)]

    @staticmethod
    def _keyword_matches(haystack: str, keyword: str) -> bool:
        normalized = keyword.strip().lower()
        if not normalized:
            return False
        if re.search(r"[\u4e00-\u9fff]", normalized):
            return normalized in haystack
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", haystack))

    @staticmethod
    def _is_valid_result(title: str, url: str) -> bool:
        blocked_title_patterns = [
            "GEO 优化",
            "GEO优化",
            "软文推广",
            "品牌传播",
            "权威测评",
            "管理层讨论",
            "年度管理层",
        ]
        if any(pattern in title for pattern in blocked_title_patterns):
            return False
        host = urlparse(url).hostname or ""
        return bool(re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", title)) and host not in {"top.baidu.com"}

    @staticmethod
    def _host(url: str) -> str:
        hostname = urlparse(url).hostname
        return hostname.replace("www.", "") if hostname else ""

    @staticmethod
    def _canonical_url(url: str) -> str:
        parsed = urlparse(url.strip())
        ignored = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "source"}
        query = urlencode([
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in ignored
        ])
        path = re.sub(r"/+$", "", parsed.path) or "/"
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", query, ""))

    @staticmethod
    def _title_fingerprint(title: str) -> str:
        normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title.lower())
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:20]

    def _first_seen_at(self, url: str) -> datetime:
        key = self._canonical_url(url)
        saved = self.first_seen.get(key)
        if saved:
            parsed = self._parse_datetime(saved)
            if parsed:
                return parsed
        now = datetime.now(timezone.utc)
        self.first_seen[key] = now.isoformat()
        return now

    @staticmethod
    def _load_json(path: Path, default):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return default

    def _save_state(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        configured_names = {
            source.get("name", source.get("url", "unknown"))
            for source in self._configured_sources()
            if source.get("enabled", True)
        }
        self.health["sources"] = {
            name: value
            for name, value in self.health.get("sources", {}).items()
            if name in configured_names
        }
        self.health["generated_at"] = datetime.now(timezone.utc).isoformat()
        self.health_path.write_text(
            json.dumps(self.health, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.first_seen_path.write_text(
            json.dumps(self.first_seen, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _record_health(
        self,
        name: str,
        kind: str,
        success: bool,
        accepted_count: int,
        error: str = "",
    ) -> None:
        sources = self.health.setdefault("sources", {})
        previous = sources.get(name, {})
        now = datetime.now(timezone.utc).isoformat()
        sources[name] = {
            "kind": kind,
            "status": "ok" if success else "error",
            "last_checked_at": now,
            "last_success_at": now if success else previous.get("last_success_at", ""),
            "accepted_count": accepted_count,
            "candidate_count": accepted_count,
            "consecutive_failures": 0 if success else previous.get("consecutive_failures", 0) + 1,
            "error": "" if success else (error or "unknown error")[:300],
        }

    def health_summary(self) -> dict:
        configured = [source for source in self._configured_sources() if source.get("enabled", True)]
        official_names = {
            source.get("name", source.get("url", "unknown"))
            for source in configured
            if source.get("official")
        }
        health_sources = self.health.get("sources", {})
        failing = [
            name
            for name in official_names
            if health_sources.get(name, {}).get("status") == "error"
        ]
        alert_threshold = int(self.config.get("health_alert_threshold", 3))
        alerts = [
            name
            for name in official_names
            if health_sources.get(name, {}).get("consecutive_failures", 0) >= alert_threshold
        ]
        return {
            "generated_at": self.health.get("generated_at", ""),
            "official_total": len(official_names),
            "official_checked": sum(1 for name in official_names if name in health_sources),
            "official_failing": len(failing),
            "failing_sources": sorted(failing),
            "alert_sources": sorted(alerts),
            "sources": health_sources,
        }

    def _apply_tier_limits(self, items: list[NewsItem]) -> list[NewsItem]:
        limits = self.config.get("tier_limits", {})
        default_limit = int(self.config.get("fetch_limit", 120))
        counts: dict[str, int] = {}
        selected = []
        for item in items:
            tier = item.source_tier or "media"
            limit = int(limits.get(tier, default_limit))
            if counts.get(tier, 0) >= limit:
                continue
            counts[tier] = counts.get(tier, 0) + 1
            selected.append(item)
            if len(selected) >= default_limit:
                break
        return selected

    @classmethod
    def _dedupe(cls, items: list[NewsItem]) -> list[NewsItem]:
        seen_urls = set()
        seen_titles = set()
        unique = []
        tier_priority = {"official": 0, "media": 1, "community": 2}
        for item in sorted(
            items,
            key=lambda x: (
                tier_priority.get(x.source_tier, 9),
                -int(datetime.fromisoformat(x.published_at).timestamp()),
            ),
        ):
            url_key = cls._canonical_url(item.detail_link)
            title_key = cls._title_fingerprint(item.title)
            if url_key in seen_urls or title_key in seen_titles:
                continue
            seen_urls.add(url_key)
            seen_titles.add(title_key)
            unique.append(item)
        return cls._sort_for_brief(unique)

    @staticmethod
    def _sort_for_brief(items: list[NewsItem]) -> list[NewsItem]:
        return sorted(
            items,
            key=lambda item: (
                item.date,
                -LEADERSHIP_CATEGORY_PRIORITY.get(item.leadership_category, 99),
                -TYPE_PRIORITY.get(item.type, 99),
                item.published_at,
            ),
            reverse=True,
        )


def dump_payload(items: list[NewsItem]) -> dict:
    """Return the JSON payload consumed by the static pages."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": [asdict(item) for item in items],
    }
