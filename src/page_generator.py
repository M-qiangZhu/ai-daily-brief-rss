"""Generate static pages and data files for the AI daily brief."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .domestic_ai_news import NewsItem, dump_payload


class PageGenerator:
    """Writes the static HTML assets for the domestic AI news brief."""

    def __init__(
        self,
        docs_dir: str | Path = "docs",
        latest_path: str | Path = "data/ai_news/latest.json",
    ):
        self.docs_dir = Path(docs_dir)
        self.data_dir = self.docs_dir / "assets" / "data"
        self.latest_path = Path(latest_path)

    def write(self, items: list[NewsItem]) -> dict[str, Path]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = dump_payload(items)
        data_path = self.data_dir / "ai-news.json"
        data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        archive_dir = self.docs_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        for date in sorted({item.date for item in items}, reverse=True):
            target = archive_dir / f"{date}.json"
            date_items = [item for item in items if item.date == date]
            target.write_text(
                json.dumps(dump_payload(date_items), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        latest_copy = self.latest_path
        latest_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(data_path, latest_copy)
        return {"data": data_path, "latest": latest_copy}
