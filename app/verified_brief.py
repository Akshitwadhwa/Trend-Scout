from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import unescape
import re
from typing import Any
from urllib.parse import urlparse


OFFICIAL_DOMAINS = {
    "openai.com",
    "anthropic.com",
    "deepmind.google",
    "ai.google",
    "blog.google",
    "ai.meta.com",
    "about.fb.com",
    "microsoft.com",
    "blogs.microsoft.com",
    "nvidia.com",
    "apple.com",
    "news.samsung.com",
    "samsung.com",
    "garmin.com",
    "whoop.com",
    "ouraring.com",
    "tesla.com",
    "ir.tesla.com",
    "huggingface.co",
    "github.blog",
    "kimi.com",
    "platform.kimi.ai",
    "deepseek.com",
    "mistral.ai",
    "docs.mistral.ai",
    "qwen.ai",
}

REPUTABLE_FEEDS = {
    "techcrunch.com",
    "news.ycombinator.com",
    "wired.com",
    "engadget.com",
    "9to5mac.com",
    "macrumors.com",
    "sammobile.com",
    "wareable.com",
}

REPUTABLE_PUBLICATIONS = {
    "associated press",
    "ap news",
    "axios",
    "bbc",
    "bloomberg",
    "cnbc",
    "financial times",
    "the indian express",
    "the information",
    "the verge",
    "techcrunch",
    "tom's hardware",
    "the guardian",
    "reuters",
    "wired",
}


class VerifiedBriefBuilder:
    """Turns raw source items into a compact, auditable research brief."""

    def __init__(self, max_age_hours: int = 72) -> None:
        self.max_age_hours = max(1, max_age_hours)

    def build(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        briefs: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for item in items:
            title = self._clean(str(item.get("title") or item.get("text") or ""))
            if not title:
                continue
            title_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
            if title_key in seen_titles:
                continue
            created_at = self._parse_date(str(item.get("created_at", "")))
            age_hours = self._age_hours(created_at, now)
            source_level, source_name = self._source_level(item)
            evidence = self._evidence(item, title)
            eligible = age_hours is None or age_hours <= self.max_age_hours
            briefs.append(
                {
                    "title": title,
                    "what_happened": evidence,
                    "source_url": str(item.get("url", "")),
                    "source_name": source_name,
                    "source_level": source_level,
                    "published_at": created_at.isoformat() if created_at else "Unknown",
                    "age_hours": round(age_hours, 1) if age_hours is not None else None,
                    "eligible": eligible,
                    "verification_note": self._verification_note(source_level, eligible),
                }
            )
            seen_titles.add(title_key)
        briefs.sort(
            key=lambda value: (
                not value["eligible"],
                {"primary": 0, "web_researched": 1, "reputable": 2, "discovery": 3}.get(value["source_level"], 4),
                value["age_hours"] if value["age_hours"] is not None else 9_999,
            )
        )
        return {
            "generated_at": now.isoformat(),
            "max_age_hours": self.max_age_hours,
            "items": briefs[:12],
            "ready_count": sum(1 for item in briefs if item["eligible"] and item["source_level"] != "discovery"),
            "source_counts": {
                level: sum(1 for item in briefs if item["source_level"] == level)
                for level in ("primary", "web_researched", "reputable", "discovery")
            },
        }

    def _source_level(self, item: dict[str, Any]) -> tuple[str, str]:
        url = str(item.get("url", ""))
        host = urlparse(url).netloc.lower().removeprefix("www.")
        source_type = str(item.get("source_type", ""))
        publisher_url = str(item.get("publisher_url", ""))
        publisher_host = urlparse(publisher_url).netloc.lower().removeprefix("www.")
        if host == "news.google.com" and any(
            publisher_host == domain or publisher_host.endswith(f".{domain}")
            for domain in OFFICIAL_DOMAINS
        ):
            return "primary", str(item.get("author_name") or publisher_host)
        if any(host == domain or host.endswith(f".{domain}") for domain in OFFICIAL_DOMAINS):
            return "primary", host
        if source_type == "openai_web_research":
            return "web_researched", str(item.get("author_name") or host or "OpenAI web research")
        publisher = str(item.get("author_name", "")).lower().strip()
        if host == "news.google.com" and publisher in REPUTABLE_PUBLICATIONS:
            return "reputable", str(item.get("author_name"))
        if any(host == domain or host.endswith(f".{domain}") for domain in REPUTABLE_FEEDS):
            return "reputable", host
        return "discovery", host or str(item.get("author_name") or "unknown source")

    def _evidence(self, item: dict[str, Any], title: str) -> str:
        text = self._clean(str(item.get("text", "")))
        remaining = text.removeprefix(title).strip(" -:\n")
        return (remaining or title)[:420]

    def _parse_date(self, value: str) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _age_hours(self, created_at: datetime | None, now: datetime) -> float | None:
        if created_at is None:
            return None
        return max(0.0, (now - created_at).total_seconds() / 3600)

    def _verification_note(self, source_level: str, eligible: bool) -> str:
        if not eligible:
            return "Too old for a latest-tech post; keep only as background."
        if source_level == "primary":
            return "Use this as a publishable factual source; keep the post tied to the link."
        if source_level == "web_researched":
            return "OpenAI web research supplied this direct link; open it before posting an exact claim."
        if source_level == "reputable":
            return "Good discovery source; prefer an official announcement before making a strong claim."
        return "Discovery only; verify the claim with an official or reputable source before posting."

    def _clean(self, value: str) -> str:
        return " ".join(re.sub(r"<[^>]+>", " ", unescape(value)).split())
