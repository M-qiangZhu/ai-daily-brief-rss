"""CLI for domestic AI news retrieval and page generation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .domestic_ai_news import DomesticAINewsFetcher, dump_payload
from .notifier import build_wechat_markdown, send_wechat_markdown
from .page_generator import PageGenerator


def _target_date(value: str | None, tz_name: str) -> date:
    if value:
        return date.fromisoformat(value)
    return datetime.now(ZoneInfo(tz_name)).date()


def _stringify_outputs(outputs: dict) -> dict:
    result = {}
    for key, value in outputs.items():
        if isinstance(value, list):
            result[key] = [str(item) for item in value]
        else:
            result[key] = str(value)
    return result


async def build(
    days: int | None,
    target_date: date | None,
    config: str,
    docs_dir: str,
    tz_name: str,
    public_url: str,
    notify: bool,
) -> dict:
    fetcher = DomesticAINewsFetcher(config)
    report_date = target_date or _target_date(None, tz_name)
    items = (
        await fetcher.fetch(days=days, tz_name=tz_name)
        if days is not None
        else await fetcher.fetch_date(report_date, tz_name=tz_name)
    )
    outputs = PageGenerator(docs_dir).write_daily(items)
    page_url = public_url.rstrip("/") + "/ai-news.html" if public_url else ""
    brief_markdown = build_wechat_markdown(items, page_url, report_date.isoformat())
    notification = {"enabled": False}
    webhook_url = os.environ.get("WECHAT_WEBHOOK_URL", "").strip()
    if notify:
        if not webhook_url:
            notification = {"enabled": True, "sent": False, "reason": "WECHAT_WEBHOOK_URL is not set"}
        else:
            notification = {"enabled": True, "sent": True, "response": await send_wechat_markdown(webhook_url, brief_markdown)}
    return {
        "success": True,
        "total": len(items),
        "dates": sorted({item.date for item in items}, reverse=True),
        "sources": sorted({item.source_site for item in items}),
        "outputs": _stringify_outputs(outputs),
        "page_url": page_url,
        "brief_markdown": brief_markdown,
        "notification": notification,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Domestic AI daily news brief")
    parser.add_argument("--days", type=int, default=None, help="Fetch a lookback window instead of the current local day")
    parser.add_argument("--date", default=None, help="Fetch one local date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--timezone", default="Asia/Shanghai", help="Local timezone for daily windows")
    parser.add_argument("--config", default="data/sources.json", help="Domestic source config path")
    parser.add_argument("--docs-dir", default="docs", help="Static site output directory")
    parser.add_argument("--public-url", default="http://220.154.142.131:19401", help="Public static site base URL")
    parser.add_argument("--notify", action="store_true", help="Send the brief to WECHAT_WEBHOOK_URL")
    parser.add_argument("--json-only", action="store_true", help="Print fetched JSON without writing pages")
    args = parser.parse_args()
    target_date = _target_date(args.date, args.timezone)

    if args.json_only:
        fetcher = DomesticAINewsFetcher(args.config)
        items = (
            asyncio.run(fetcher.fetch(days=args.days, tz_name=args.timezone))
            if args.days is not None
            else asyncio.run(fetcher.fetch_date(target_date, tz_name=args.timezone))
        )
        print(json.dumps(dump_payload(items), ensure_ascii=False, indent=2))
        return

    result = asyncio.run(build(
        args.days,
        target_date,
        args.config,
        args.docs_dir,
        args.timezone,
        args.public_url,
        args.notify,
    ))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
