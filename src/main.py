"""CLI for domestic AI news retrieval and page generation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import date, datetime
from pathlib import Path
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


def _wechat_webhook_targets() -> list[dict[str, str]]:
    values = [
        (os.environ.get("WECHAT_WEBHOOK_URL", ""), ""),
        (os.environ.get("WECHAT_WEBHOOK_URL_TEST", ""), "【企业微信测试渠道】\n"),
        (os.environ.get("WECHAT_WEBHOOK_URLS", ""), ""),
    ]
    targets = []
    seen = set()
    for value, prefix in values:
        for part in value.replace("\n", ",").split(","):
            url = part.strip()
            if not url or url in seen:
                continue
            seen.add(url)
            targets.append({"url": url, "prefix": prefix})
    return targets


async def _send_wechat_markdown_to_all(content: str) -> list[dict]:
    responses = []
    for index, target in enumerate(_wechat_webhook_targets(), start=1):
        message = target["prefix"] + content
        responses.append({
            "target": index,
            "response": await send_wechat_markdown(target["url"], message),
        })
    return responses


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
    health = fetcher.health_summary()
    public_health = {
        key: value
        for key, value in health.items()
        if key not in {"sources", "failing_sources", "alert_sources"}
    }
    outputs = PageGenerator(docs_dir).write_daily(items, public_health)
    report_items = [item for item in items if item.date == report_date.isoformat()]
    page_url = public_url.rstrip("/") + "/ai-news.html" if public_url else ""
    brief_markdown = build_wechat_markdown(
        report_items,
        page_url,
        report_date.isoformat(),
    )
    notification = {"enabled": False}
    webhook_targets = _wechat_webhook_targets()
    if notify:
        if not webhook_targets:
            notification = {"enabled": True, "sent": False, "reason": "WECHAT_WEBHOOK_URL is not set"}
        elif _notification_sent(report_date, config):
            notification = {"enabled": True, "sent": False, "reason": "daily notification already sent"}
        else:
            responses = await _send_wechat_markdown_to_all(brief_markdown)
            notification = {"enabled": True, "sent": True, "targets": len(responses), "responses": responses}
            _mark_notification_sent(report_date, config)
    return {
        "success": True,
        "total": len(items),
        "dates": sorted({item.date for item in items}, reverse=True),
        "sources": sorted({item.source_site for item in items}),
        "outputs": _stringify_outputs(outputs),
        "page_url": page_url,
        "brief_markdown": brief_markdown,
        "notification": notification,
        "source_health": health,
    }


async def notify_from_archive(
    report_date: date,
    config: str,
    docs_dir: str,
    public_url: str,
) -> dict:
    archive_path = Path(docs_dir) / "archive" / f"{report_date.isoformat()}.json"
    try:
        payload = json.loads(archive_path.read_text(encoding="utf-8"))
        items = [PageGenerator._item_from_dict(item) for item in payload.get("items", [])]
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        return {
            "success": False,
            "sent": False,
            "reason": f"archive unavailable: {exc}",
            "archive": str(archive_path),
        }

    webhook_targets = _wechat_webhook_targets()
    if not webhook_targets:
        return {"success": False, "sent": False, "reason": "WECHAT_WEBHOOK_URL is not set"}
    if _notification_sent(report_date, config):
        return {"success": True, "sent": False, "reason": "daily notification already sent"}

    page_url = public_url.rstrip("/") + "/ai-news.html" if public_url else ""
    content = build_wechat_markdown(items, page_url, report_date.isoformat())
    responses = await _send_wechat_markdown_to_all(content)
    _mark_notification_sent(report_date, config)
    return {
        "success": True,
        "sent": True,
        "count": len(items),
        "archive": str(archive_path),
        "targets": len(responses),
        "responses": responses,
    }


def _notification_state_path(config: str) -> Path:
    config_path = Path(config)
    return config_path.parent / "state" / "notifications.json"


def _notification_sent(report_date: date, config: str) -> bool:
    path = _notification_state_path(config)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return report_date.isoformat() in payload.get("sent_dates", [])


def _mark_notification_sent(report_date: date, config: str) -> None:
    path = _notification_state_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {"sent_dates": []}
    dates = sorted(set(payload.get("sent_dates", []) + [report_date.isoformat()]))[-60:]
    path.write_text(json.dumps({"sent_dates": dates}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Domestic AI daily news brief")
    parser.add_argument("--days", type=int, default=None, help="Fetch a lookback window instead of the current local day")
    parser.add_argument("--date", default=None, help="Fetch one local date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--timezone", default="Asia/Shanghai", help="Local timezone for daily windows")
    parser.add_argument("--config", default="data/sources.json", help="Domestic source config path")
    parser.add_argument("--docs-dir", default="docs", help="Static site output directory")
    parser.add_argument("--public-url", default="http://220.154.142.131:19401", help="Public static site base URL")
    parser.add_argument("--notify", action="store_true", help="Send the brief to WECHAT_WEBHOOK_URL")
    parser.add_argument("--notify-only", action="store_true", help="Send today's existing archive without fetching")
    parser.add_argument("--json-only", action="store_true", help="Print fetched JSON without writing pages")
    args = parser.parse_args()
    target_date = _target_date(args.date, args.timezone)

    if args.notify_only:
        result = asyncio.run(notify_from_archive(
            target_date,
            args.config,
            args.docs_dir,
            args.public_url,
        ))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

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
