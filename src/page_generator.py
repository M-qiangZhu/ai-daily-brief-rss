"""Generate static pages and data files for the AI daily brief."""

from __future__ import annotations

from collections import Counter
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .domestic_ai_news import LEADERSHIP_CATEGORY_PRIORITY, NewsItem, dump_payload


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
        return self.write_daily(items)

    def write_daily(self, items: list[NewsItem]) -> dict[str, Path]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        archive_dir = self.docs_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        touched_archives = []
        for item_date in sorted({item.date for item in items}, reverse=True):
            target = archive_dir / f"{item_date}.json"
            merged_items = self._merge_archive_items(target, [item for item in items if item.date == item_date])
            target.write_text(
                json.dumps(dump_payload(merged_items), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            touched_archives.append(target)

        index_path = archive_dir / "index.json"
        index_payload = self._archive_index(archive_dir)
        index_path.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        latest_items = self._latest_items(archive_dir, index_payload.get("latest_date"))
        data_path = self.data_dir / "ai-news.json"
        data_path.write_text(json.dumps(dump_payload(latest_items), ensure_ascii=False, indent=2), encoding="utf-8")
        latest_copy = self.latest_path
        latest_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(data_path, latest_copy)
        return {
            "data": data_path,
            "latest": latest_copy,
            "index": index_path,
            "archives": touched_archives,
        }

    @staticmethod
    def _merge_archive_items(target: Path, new_items: list[NewsItem]) -> list[NewsItem]:
        existing_items = []
        if target.exists():
            try:
                payload = json.loads(target.read_text(encoding="utf-8"))
                existing_items = [PageGenerator._item_from_dict(item) for item in payload.get("items", [])]
            except (json.JSONDecodeError, TypeError, OSError):
                existing_items = []

        by_link = {}
        for item in [*existing_items, *new_items]:
            key = item.detail_link.rstrip("/") or item.id
            by_link[key] = item
        return sorted(
            by_link.values(),
            key=lambda item: (
                -LEADERSHIP_CATEGORY_PRIORITY.get(item.leadership_category, 99),
                item.published_at,
            ),
            reverse=True,
        )

    @staticmethod
    def _item_from_dict(value: dict) -> NewsItem:
        return NewsItem(
            id=value.get("id", ""),
            date=value.get("date", ""),
            type=value.get("type", "AI资讯"),
            title=value.get("title", ""),
            content_summary=value.get("content_summary", ""),
            detail_link=value.get("detail_link", ""),
            source_site=value.get("source_site", ""),
            published_at=value.get("published_at", ""),
            leadership_category=value.get("leadership_category", "行业应用与商业化"),
        )

    @staticmethod
    def _archive_index(archive_dir: Path) -> dict:
        dates = []
        for path in sorted(archive_dir.glob("*.json"), reverse=True):
            if path.name == "index.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            items = payload.get("items", [])
            if not items:
                continue
            category_counts = Counter(item.get("leadership_category", "行业应用与商业化") for item in items)
            type_counts = Counter(item.get("type", "AI资讯") for item in items)
            dates.append({
                "date": path.stem,
                "count": len(items),
                "category_counts": dict(category_counts),
                "type_counts": dict(type_counts),
                "top_items": [
                    {
                        "title": item.get("title", ""),
                        "type": item.get("type", "AI资讯"),
                        "leadership_category": item.get("leadership_category", "行业应用与商业化"),
                        "source_site": item.get("source_site", ""),
                    }
                    for item in items[:3]
                ],
            })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "latest_date": dates[0]["date"] if dates else "",
            "dates": dates,
        }

    @staticmethod
    def _latest_items(archive_dir: Path, latest_date: str | None) -> list[NewsItem]:
        if not latest_date:
            return []
        target = archive_dir / f"{latest_date}.json"
        if not target.exists():
            return []
        payload = json.loads(target.read_text(encoding="utf-8"))
        return [PageGenerator._item_from_dict(item) for item in payload.get("items", [])]
