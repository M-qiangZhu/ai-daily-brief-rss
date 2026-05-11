"""Domestic AI news retrieval and normalization."""

from __future__ import annotations

import asyncio
import calendar
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus, urlparse

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
    "运营商与央国企动态": 1,
    "算力、数据中心与云基础设施": 2,
    "AI模型与智能体技术": 3,
    "行业应用与商业化": 4,
    "AI终端、机器人与硬件": 5,
    "投融资与竞争格局": 6,
    "风险、安全与合规": 7,
    "技术社区观察": 8,
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
    leadership_category: str = "行业应用与商业化"


class DomesticAINewsFetcher:
    """Fetch domestic AI news from RSS feeds and Baidu News searches."""

    def __init__(self, config_path: str | Path = "data/sources.json"):
        self.config_path = Path(config_path)
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))

    async def fetch(self, days: int = 1) -> list[NewsItem]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, headers=HEADERS) as client:
            tasks = []
            for source in self.config.get("feeds", []):
                if source.get("enabled", True):
                    tasks.append(self._fetch_feed(client, source, since))
            for source in self.config.get("searches", []):
                if source.get("enabled", True):
                    tasks.append(self._fetch_baidu_news(client, source, since))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        items: list[NewsItem] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            items.extend(result)

        return self._dedupe(items)[: self.config.get("fetch_limit", 80)]

    async def _fetch_feed(
        self,
        client: httpx.AsyncClient,
        source: dict,
        since: datetime,
    ) -> list[NewsItem]:
        try:
            response = await client.get(source["url"], follow_redirects=True)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
        except Exception:
            return []

        items: list[NewsItem] = []
        for entry in feed.entries[: source.get("max_entries", 20)]:
            published_at = self._parse_feed_date(entry) or datetime.now(timezone.utc)
            if published_at < since:
                continue

            title = self._clean_text(entry.get("title", ""))
            link = entry.get("link", source["url"])
            summary = self._summary(self._entry_content(entry) or title)
            if not self._is_relevant(title, summary, source.get("keywords"), source.get("name", "")):
                continue

            items.append(self._make_item(
                title=title,
                link=link,
                summary=summary,
                source_site=source.get("name", self._host(link)),
                published_at=published_at,
                category=source.get("category"),
            ))

        return items

    async def _fetch_baidu_news(
        self,
        client: httpx.AsyncClient,
        source: dict,
        since: datetime,
    ) -> list[NewsItem]:
        try:
            response = await client.get(self._baidu_url(source["query"]), follow_redirects=True)
            response.raise_for_status()
        except Exception:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        items: list[NewsItem] = []
        for result in self._extract_baidu_results(soup)[: source.get("max_results", 10)]:
            if not self._is_valid_result(result["title"], result["link"]):
                continue

            published_at = (
                self._parse_cn_time(result["date"])
                or self._parse_cn_time(result["summary"])
                or datetime.now(timezone.utc)
            )
            if published_at < since:
                continue

            summary = self._summary(result["summary"] or result["title"])
            items.append(self._make_item(
                title=result["title"],
                link=result["link"],
                summary=summary,
                source_site=result["source"] or self._host(result["link"]),
                published_at=published_at,
                category=source.get("category"),
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
    ) -> NewsItem:
        news_type = category or self._classify(title, summary)
        leadership_category = self._leadership_category(news_type, title, summary, source_site)
        return NewsItem(
            id=hashlib.sha1(f"{title}|{link}".encode("utf-8")).hexdigest()[:16],
            date=published_at.date().isoformat(),
            type=news_type,
            title=title,
            content_summary=summary,
            detail_link=link,
            source_site=source_site,
            published_at=published_at.isoformat(),
            leadership_category=leadership_category,
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
        if news_type in {"AI模型", "AI Agent", "AI技术", "AI编程"}:
            return "AI模型与智能体技术"
        if news_type in {"机器人", "智能驾驶", "AI硬件"}:
            return "AI终端、机器人与硬件"
        if news_type == "AI安全" or any(keyword in text for keyword in ["安全", "合规", "监管", "对齐", "deepfake", "版权"]):
            return "风险、安全与合规"
        if any(keyword in text for keyword in ["融资", "估值", "ipo", "资本", "基金", "投资", "市场"]):
            return "投融资与竞争格局"
        return "行业应用与商业化"

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

    @classmethod
    def _dedupe(cls, items: list[NewsItem]) -> list[NewsItem]:
        seen = set()
        unique = []
        for item in sorted(items, key=lambda x: x.published_at, reverse=True):
            key = item.detail_link.rstrip("/")
            if key in seen:
                continue
            seen.add(key)
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
