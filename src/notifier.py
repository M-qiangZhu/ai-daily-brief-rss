"""Enterprise WeChat notification helpers for the daily AI brief."""

from __future__ import annotations

from collections import Counter

import httpx

from .domestic_ai_news import NewsItem


LEADERSHIP_LABELS = [
    "政策与监管",
    "运营商与央国企动态",
    "算力、数据中心与云基础设施",
    "AI模型与智能体技术",
    "行业应用与商业化",
    "AI终端、机器人与硬件",
    "投融资与竞争格局",
    "风险、安全与合规",
    "技术社区观察",
]


def build_wechat_markdown(items: list[NewsItem], page_url: str, report_date: str) -> str:
    """Build a concise leadership-style markdown message."""
    category_counts = Counter(item.leadership_category for item in items)
    lines = [
        f"每日 AI 资讯已更新：{report_date}",
        f">共收录：<font color=\"warning\">{len(items)} 条</font>",
    ]

    for label in LEADERSHIP_LABELS[:4]:
        count = category_counts.get(label, 0)
        if count:
            lines.append(f">{label}：<font color=\"comment\">{count} 条</font>")

    focus_items = items[:3]
    if focus_items:
        lines.append(">重点关注：")
        for index, item in enumerate(focus_items, start=1):
            title = _shorten(item.title, 48)
            lines.append(f">{index}. {title}")
    else:
        lines.append(">重点关注：今日暂无新增匹配资讯，首页将展示最近一次归档。")

    lines.append("")
    lines.append(f"[查看今日简报]({page_url})")
    return "\n".join(lines)


async def send_wechat_markdown(webhook_url: str, content: str) -> dict:
    """Send a markdown message to an Enterprise WeChat robot webhook."""
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": content,
        },
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()
        return response.json()


def _shorten(value: str, max_chars: int) -> str:
    text = " ".join((value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"
