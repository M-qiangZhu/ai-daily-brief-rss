"""CLI for domestic AI news retrieval and page generation."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .domestic_ai_news import DomesticAINewsFetcher, dump_payload
from .page_generator import PageGenerator


async def build(days: int, config: str, docs_dir: str) -> dict:
    fetcher = DomesticAINewsFetcher(config)
    items = await fetcher.fetch(days=days)
    outputs = PageGenerator(docs_dir).write(items)
    return {
        "success": True,
        "total": len(items),
        "dates": sorted({item.date for item in items}, reverse=True),
        "sources": sorted({item.source_site for item in items}),
        "outputs": {key: str(value) for key, value in outputs.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Domestic AI daily news brief")
    parser.add_argument("--days", type=int, default=7, help="Fetch news from the last N days")
    parser.add_argument("--config", default="data/sources.json", help="Domestic source config path")
    parser.add_argument("--docs-dir", default="docs", help="Static site output directory")
    parser.add_argument("--json-only", action="store_true", help="Print fetched JSON without writing pages")
    args = parser.parse_args()

    if args.json_only:
        fetcher = DomesticAINewsFetcher(args.config)
        items = asyncio.run(fetcher.fetch(days=args.days))
        print(json.dumps(dump_payload(items), ensure_ascii=False, indent=2))
        return

    result = asyncio.run(build(args.days, args.config, args.docs_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
