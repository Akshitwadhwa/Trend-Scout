from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


POST_READY_LEVELS = {"primary", "reputable", "web_researched"}


class TrendInbox:
    """A small local memory of distinct, source-backed tech stories."""

    def __init__(self, path: Path, retention_hours: int = 2) -> None:
        self.path = path
        self.retention_hours = max(1, retention_hours)

    def merge(self, verified_brief: dict[str, Any], *, replace_existing: bool = False) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        existing = [] if replace_existing else self._read().get("items", [])
        incoming = verified_brief.get("items", [])
        candidates = [*incoming, *existing]
        retained: list[dict[str, Any]] = []
        seen: set[str] = set()

        for item in candidates:
            if not isinstance(item, dict):
                continue
            if item.get("source_level") not in POST_READY_LEVELS:
                continue
            if not self._within_retention(item, now):
                continue
            key = self._title_key(str(item.get("title", "")))
            if not key or key in seen:
                continue
            retained.append(item)
            seen.add(key)

        retained.sort(key=lambda item: str(item.get("published_at", "")), reverse=True)
        payload = {
            "updated_at": now.isoformat(),
            "retention_hours": self.retention_hours,
            "items": retained[:30],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        self._markdown_path().write_text(self._markdown(payload), encoding="utf-8")
        return payload

    def _read(self) -> dict[str, Any]:
        try:
            parsed = json.loads(self.path.read_text(encoding="utf-8"))
            return parsed if isinstance(parsed, dict) else {}
        except (OSError, ValueError):
            return {}

    def _within_retention(self, item: dict[str, Any], now: datetime) -> bool:
        value = str(item.get("published_at", ""))
        try:
            published = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return published >= now - timedelta(hours=self.retention_hours)

    def _title_key(self, title: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()

    def _markdown_path(self) -> Path:
        return self.path.with_suffix(".md")

    def _markdown(self, payload: dict[str, Any]) -> str:
        lines = [
            "# Saved Trend Inbox",
            "",
            "Distinct post-ready stories saved locally. Nothing is posted automatically.",
            "",
            f"Updated: {payload.get('updated_at', '')}",
            f"Memory window: {payload.get('retention_hours', 2)} hours",
            "",
        ]
        for index, item in enumerate(payload.get("items", []), start=1):
            lines.extend(
                [
                    f"## {index}. {item.get('title', '')}",
                    f"Source: {item.get('source_name', '')} ({item.get('source_level', '')})",
                    f"URL: {item.get('source_url', '')}",
                    "",
                    str(item.get("what_happened", "")),
                    "",
                ]
            )
        return "\n".join(lines)
