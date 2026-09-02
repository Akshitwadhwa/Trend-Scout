from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import requests

from app.config import Settings


POST_READY_LEVELS = {"primary", "reputable", "web_researched"}


class CloudInboxReader:
    """Read the current GitHub-backed inbox without trusting a local clone."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.last_error = ""

    def fetch(
        self,
        *,
        retention_hours: int = 12,
        new_since: datetime | None = None,
        delivered_keys: Iterable[str] = (),
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        hours = max(1, int(retention_hours))
        delivered = {str(key) for key in delivered_keys if str(key).strip()}
        url = str(getattr(self.settings, "cloud_inbox_url", "")).strip()
        timeout = max(3, min(int(getattr(self.settings, "cloud_inbox_timeout_seconds", 15)), 30))
        if not url:
            raise RuntimeError("CLOUD_INBOX_URL is not configured.")

        self.last_error = ""
        try:
            response = requests.get(
                url,
                params={"_fresh": int(now.timestamp())},
                headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            self.last_error = str(exc)
            raise RuntimeError(f"Could not fetch the live cloud inbox: {exc}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("The cloud inbox response was not a JSON object.")

        inbox_updated = self._parse_datetime(payload.get("updated_at"))
        scanned_at = self._parse_datetime(payload.get("scanned_at")) or inbox_updated
        cutoff = now - timedelta(hours=hours)
        items: list[dict[str, Any]] = []
        rejected = {"missing_date": 0, "old": 0, "unverified": 0, "delivered": 0, "invalid": 0}
        seen: set[str] = set()
        for raw in payload.get("items", []):
            if not isinstance(raw, dict):
                rejected["invalid"] += 1
                continue
            published = self._parse_datetime(raw.get("published_at"))
            if published is None:
                rejected["missing_date"] += 1
                continue
            if published < cutoff or published > now + timedelta(minutes=5):
                rejected["old"] += 1
                continue
            if str(raw.get("source_level", "")) not in POST_READY_LEVELS:
                rejected["unverified"] += 1
                continue
            source_url = str(raw.get("source_url", "")).strip()
            title = " ".join(str(raw.get("title", "")).split()).strip()
            if not source_url or not title:
                rejected["invalid"] += 1
                continue
            source_key = self.source_key(source_url, title)
            if source_key in seen or source_key in delivered:
                rejected["delivered"] += 1
                continue
            if new_since is not None and published <= new_since.astimezone(timezone.utc):
                rejected["old"] += 1
                continue
            item = dict(raw)
            item["title"] = title
            item["source_key"] = source_key
            item["published_at"] = published.isoformat()
            item["age_hours"] = round(max(0.0, (now - published).total_seconds() / 3600), 1)
            item["scanned_at"] = (scanned_at or now).isoformat()
            items.append(item)
            seen.add(source_key)

        items.sort(key=lambda item: str(item.get("published_at", "")), reverse=True)
        return {
            "source_url": url,
            "fetched_at": now.isoformat(),
            "inbox_updated_at": inbox_updated.isoformat() if inbox_updated else "Unknown",
            "scanned_at": (scanned_at or now).isoformat(),
            "retention_hours": hours,
            "inbox_is_stale": inbox_updated is None or inbox_updated < cutoff,
            "items": items,
            "new_count": len(items),
            "rejected": rejected,
        }

    @staticmethod
    def source_key(source_url: str, title: str = "") -> str:
        raw = f"{source_url.strip()}\n{title.strip().casefold()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        text = str(value or "").strip()
        if not text or text.casefold() in {"unknown", "none", "null"}:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
