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
    "intel.com",
    "apple.com",
    "news.samsung.com",
    "samsung.com",
    "garmin.com",
    "whoop.com",
    "ouraring.com",
    "tesla.com",
    "ir.tesla.com",
    "huggingface.co",
    "github.com",
    "github.blog",
    "kimi.com",
    "platform.kimi.ai",
    "deepseek.com",
    "mistral.ai",
    "docs.mistral.ai",
    "qwen.ai",
    "cursor.com",
    "status.openai.com",
}

# A repository hosted on Hugging Face is not automatically an official model
# release.  Community conversions and GGUF mirrors can appear as newly
# modified with zero downloads, which made them look like major launches in
# the inbox.  Keep only recognisable publisher organisations in the primary
# bucket; adopted community models can still qualify as reputable below.
HUGGING_FACE_OFFICIAL_ORGS = {
    "allenai",
    "anthropic",
    "baai",
    "black-forest-labs",
    "cohereforai",
    "deepseek-ai",
    "google",
    "huggingface",
    "huggingfaceh4",
    "meta-llama",
    "microsoft",
    "mistralai",
    "moonshotai",
    "nvidia",
    "openai",
    "qwen",
    "stabilityai",
    "xai-org",
}
HUGGING_FACE_REPUTABLE_DOWNLOADS = 5_000
HUGGING_FACE_REPUTABLE_LIKES = 25

# A company careers page can appear in a Google News result and inherit the
# company's primary-source status. It is not a product, model, or technology
# update, so it must never enter the tweet-drafting inbox.
JOB_LISTING_PREFIXES = (
    "account executive,",
    "business development,",
    "data scientist,",
    "design engineer,",
    "engineering manager,",
    "machine learning engineer,",
    "product manager,",
    "program manager,",
    "research engineer,",
    "research scientist,",
    "software engineer,",
    "solutions engineer,",
    "staff software engineer,",
)
JOB_LISTING_TERMS = (
    "careers",
    "job opening",
    "open role",
    "apply now",
    "join our team",
)

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
    "al jazeera",
    "axios",
    "bbc",
    "bloomberg",
    "business insider",
    "cnbc",
    "digitimes",
    "financial times",
    "india today",
    "the korea times",
    "korea joongang daily",
    "ked global",
    "mashable",
    "mlex",
    "moneycontrol",
    "moneycontrol.com",
    "the indian express",
    "the information",
    "the verge",
    "techcrunch",
    "time",
    "tom's hardware",
    "the guardian",
    "reuters",
    "wired",
    "the wall street journal",
    "wsj",
    "south china morning post",
}


class VerifiedBriefBuilder:
    """Turns raw source items into a compact, auditable research brief."""

    def __init__(self, max_age_hours: int = 12) -> None:
        self.max_age_hours = max(1, max_age_hours)

    def build(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        briefs: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for item in items:
            title = self._clean(str(item.get("title") or item.get("text") or ""))
            if not title:
                continue
            if self._is_job_listing(item, title):
                continue
            title_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
            if title_key in seen_titles:
                continue
            created_at = self._parse_date(str(item.get("created_at", "")))
            age_hours = self._age_hours(created_at, now)
            source_level, source_name = self._source_level(item)
            evidence = self._evidence(item, title)
            # A "latest" brief must have a real publication timestamp.  An
            # undated RSS/research record is not evidence that the story is
            # current; allowing it through is what made old model releases
            # look like today's news in Telegram.
            eligible = age_hours is not None and age_hours <= self.max_age_hours
            briefs.append(
                {
                    "title": title,
                    "what_happened": evidence,
                    "source_url": str(item.get("url", "")),
                    "source_name": source_name,
                    "source_level": source_level,
                    "published_at": created_at.isoformat() if created_at else "Unknown",
                    "age_hours": round(age_hours, 1) if age_hours is not None else None,
                    "scanned_at": now.isoformat(),
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
        selected = self._diverse_briefs(briefs, limit=12)
        return {
            "generated_at": now.isoformat(),
            "scanned_at": now.isoformat(),
            "max_age_hours": self.max_age_hours,
            "items": selected,
            "ready_count": sum(1 for item in briefs if item["eligible"] and item["source_level"] != "discovery"),
            "source_counts": {
                level: sum(1 for item in briefs if item["source_level"] == level)
                for level in ("primary", "web_researched", "reputable", "discovery")
            },
        }

    def _diverse_briefs(self, briefs: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
        """Retain different tech conversations, not twelve variations of one."""
        categories = (
            "consumer tech",
            "chips and infrastructure",
            "developer tools",
            "security",
            "business and policy",
            "AI and models",
            "other tech",
        )
        buckets: dict[str, list[dict[str, Any]]] = {category: [] for category in categories}
        for brief in briefs:
            buckets[self._brief_category(brief)].append(brief)

        selected: list[dict[str, Any]] = []
        while len(selected) < limit:
            added = False
            for category in categories:
                if not buckets[category]:
                    continue
                selected.append(buckets[category].pop(0))
                added = True
                if len(selected) >= limit:
                    break
            if not added:
                break
        return selected

    def _brief_category(self, brief: dict[str, Any]) -> str:
        text = f"{brief.get('title', '')} {brief.get('what_happened', '')}".lower()
        if any(word in text for word in ("iphone", "android", "samsung", "apple", "wearable", "smartwatch", "consumer")):
            return "consumer tech"
        if any(word in text for word in ("chip", "gpu", "semiconductor", "nvidia", "amd", "data center", "fab", "foundry")):
            return "chips and infrastructure"
        if any(word in text for word in ("developer", "coding", "github", "software", "api", "programming")):
            return "developer tools"
        if any(word in text for word in ("security", "cyber", "breach", "hack", "vulnerability", "exploit", "privacy")):
            return "security"
        if any(word in text for word in ("startup", "funding", "acquisition", "antitrust", "regulation", "lawsuit", "hiring", "layoff")):
            return "business and policy"
        if any(word in text for word in (" ai ", "openai", "anthropic", "gemini", "claude", "llm", "model", "deepseek", "agent")):
            return "AI and models"
        return "other tech"

    def _source_level(self, item: dict[str, Any]) -> tuple[str, str]:
        url = str(item.get("url", ""))
        host = urlparse(url).netloc.lower().removeprefix("www.")
        source_type = str(item.get("source_type", ""))
        publisher_url = str(item.get("publisher_url", ""))
        publisher_host = urlparse(publisher_url).netloc.lower().removeprefix("www.")
        if source_type == "huggingface_model":
            return self._hugging_face_source_level(item)
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

    def _hugging_face_source_level(self, item: dict[str, Any]) -> tuple[str, str]:
        """Classify a Hub upload by publisher identity and adoption, not host."""
        org = str(item.get("model_org") or item.get("author_username") or "").strip()
        org_key = org.casefold()
        label = f"Hugging Face / {org}" if org else "Hugging Face community"
        if org_key in HUGGING_FACE_OFFICIAL_ORGS:
            return "primary", label

        metrics = item.get("public_metrics")
        likes = int(metrics.get("like_count") or 0) if isinstance(metrics, dict) else 0
        try:
            downloads = int(float(item.get("score") or 0))
        except (TypeError, ValueError):
            downloads = 0
        if downloads >= HUGGING_FACE_REPUTABLE_DOWNLOADS and likes >= HUGGING_FACE_REPUTABLE_LIKES:
            return "reputable", label
        return "discovery", label

    def _is_job_listing(self, item: dict[str, Any], title: str) -> bool:
        """Reject careers pages even when their publisher is otherwise primary."""
        title_key = title.casefold()
        if title_key.startswith(JOB_LISTING_PREFIXES):
            return True
        source_paths = (
            urlparse(str(item.get("url", ""))).path.casefold(),
            urlparse(str(item.get("publisher_url", ""))).path.casefold(),
        )
        if any("career" in path or "/jobs" in path for path in source_paths):
            return True
        return any(term in title_key for term in JOB_LISTING_TERMS)

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
        if not eligible and source_level != "discovery":
            return "Publication time is missing or outside the freshness window; do not use for a latest-tech post."
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
