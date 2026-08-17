from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.ai_writer import TrendWriter
from app.config import Settings
from app.db import Database
from app.openai_research import OpenAIWebResearcher
from app.output_writer import OutputWriter
from app.reply_scout import ReplyScout
from app.trend_inbox import TrendInbox
from app.web_client import WebFeedClient
from app.x_client import XClient
from app.verified_brief import VerifiedBriefBuilder


class Workflow:
    def __init__(
        self,
        *,
        settings: Settings,
        db: Database,
        x_client: XClient,
        web_client: WebFeedClient,
        writer: TrendWriter,
        output_writer: OutputWriter,
        researcher: OpenAIWebResearcher | None = None,
    ) -> None:
        self.settings = settings
        self.db = db
        self.x_client = x_client
        self.web_client = web_client
        self.writer = writer
        self.output_writer = output_writer
        self.researcher = researcher or OpenAIWebResearcher(settings)
        self.brief_builder = VerifiedBriefBuilder(
            int(getattr(settings, "verified_max_age_hours", 2))
        )
        self._last_x_errors: list[str] = []

    def scan(self) -> dict[str, Any]:
        topic_query = self.db.get_topic_query(self.settings.topic_query)
        free_sources = self._collect_sources(topic_query)
        cloud_sources = self._openai_research_sources(topic_query)
        discovered = self._select_items([*cloud_sources, *free_sources])
        verified_brief = self.brief_builder.build(discovered)
        selected = self._post_ready_sources(discovered, verified_brief)
        if not selected:
            return {
                "status": "no_sources",
                "topic_query": topic_query,
                "source_count": 0,
                "discovered_count": len(discovered),
                "cloud_source_count": len(cloud_sources),
                "opportunities": [],
                "verified_brief": verified_brief,
                "openai_research": self._research_status(),
            }

        opportunities = self.writer.find_opportunities(
            topic_query=topic_query,
            source_items=selected,
        )
        created: list[dict[str, Any]] = []
        duplicates = 0

        for opportunity in opportunities:
            source_items = self._items_for_opportunity(opportunity, selected)
            fingerprint = self._fingerprint(opportunity, source_items, topic_query)
            existing = self.db.find_existing_by_fingerprint(fingerprint)
            if existing is not None:
                duplicates += 1
                continue

            opportunity_id = self.db.create_opportunity(
                topic_query=topic_query,
                title=str(opportunity.get("title", "Untitled opportunity")),
                category=str(opportunity.get("category", "General Tech")),
                why_now=str(opportunity.get("why_now", "")),
                post_angle=str(opportunity.get("post_angle", "")),
                confidence=float(opportunity.get("confidence", 0.5)),
                source_posts=source_items,
                fingerprint=fingerprint,
            )
            created.append(self._opportunity_payload(self.db.get_opportunity(opportunity_id)))

        return {
            "status": "ok",
            "topic_query": topic_query,
            "source_count": len(selected),
            "discovered_count": len(discovered),
            "cloud_source_count": len(cloud_sources),
            "x_source_count": len(
                [item for item in selected if item.get("source_type") == "x"]
            ),
            "x_timeline_source_count": len(
                [item for item in selected if item.get("source_type") == "x_timeline"]
            ),
            "x_watchlist_source_count": len(
                [item for item in selected if item.get("source_type") == "x_watchlist"]
            ),
            "web_source_count": len(
                [item for item in selected if item.get("source_type") == "web"]
            ),
            "x_scan_errors": self._last_x_errors[:5],
            "web_feed_errors": self.web_client.last_errors[:5],
            "verified_brief": verified_brief,
            "openai_research": self._research_status(),
            "created_count": len(created),
            "duplicate_count": duplicates,
            "opportunities": created,
        }

    def refresh_trend_inbox(
        self,
        *,
        retention_hours: int = 2,
        inbox_filename: str = "trend-inbox.json",
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        """Collect sources only; this two-hour path never invokes the local writer."""
        topic_query = self.db.get_topic_query(self.settings.topic_query)
        free_sources = self._collect_sources(topic_query)
        cloud_sources = self._openai_research_sources(topic_query)
        discovered = self._select_items([*cloud_sources, *free_sources])
        verified_brief = self.brief_builder.build(discovered)
        safe_name = Path(inbox_filename).name
        if safe_name != inbox_filename or not safe_name.endswith(".json"):
            raise ValueError("Inbox filename must be a JSON filename without a directory path.")
        inbox_path = self.settings.database_path.parent / safe_name
        inbox = TrendInbox(
            inbox_path,
            retention_hours=retention_hours,
        ).merge(verified_brief, replace_existing=replace_existing)
        return {
            "status": "ok",
            "discovered_count": len(discovered),
            "cloud_source_count": len(cloud_sources),
            "inbox_count": len(inbox.get("items", [])),
            "inbox_path": str(inbox_path),
            "verified_brief": verified_brief,
            "web_feed_errors": self.web_client.last_errors[:5],
            "openai_research": self._research_status(),
        }

    def draft_post(self, opportunity_id: int, style: str = "") -> dict[str, Any]:
        opportunity = self.db.get_opportunity(opportunity_id)
        if opportunity is None:
            raise ValueError(f"Opportunity #{opportunity_id} was not found.")

        source_items = json.loads(opportunity["source_json"])
        generated = self.writer.draft_post(
            opportunity=self._opportunity_payload(opportunity),
            source_items=source_items,
            style=style,
        )
        self.db.save_draft(opportunity_id, generated["draft"], generated["notes"])
        refreshed = self.db.get_opportunity(opportunity_id)
        drafted = self._opportunity_payload(refreshed)
        drafted["output_files"] = self.output_writer.save_draft(drafted)
        return drafted

    def draft_recent(self, *, style: str = "", limit: int = 5) -> dict[str, Any]:
        drafted = []
        for opportunity in self._diverse_opportunities(self.list_opportunities(), limit):
            drafted.append(self.draft_post(opportunity["id"], style=style))
        return {
            "drafted_count": len(drafted),
            "output_dir": str(self.settings.output_dir),
            "drafts": drafted,
        }

    def build_brief(self, *, style: str = "", limit: int = 10) -> dict[str, Any]:
        scan_result = self.scan()
        opportunities = self._diverse_opportunities(self.list_opportunities(), limit)
        content_pack = self.writer.build_content_pack(
            opportunities=opportunities,
            style=style,
        )
        output_files = self.output_writer.save_content_pack(
            content_pack=content_pack,
            opportunities=opportunities,
        )
        if getattr(self.settings, "enable_verified_brief", True):
            output_files["verified_brief"] = self.output_writer.save_verified_brief(
                scan_result.get("verified_brief", {})
            )
        return {
            "status": "ok",
            "scan": scan_result,
            "opportunity_count": len(opportunities),
            "output_files": output_files,
            "content_pack": content_pack,
        }

    def optimize_ctr(self, *, style: str = "", limit: int = 10) -> dict[str, Any]:
        scan_result = self.scan()
        opportunities = self._diverse_opportunities(self.list_opportunities(), limit)
        ctr_pack = self.writer.build_ctr_pack(
            opportunities=opportunities,
            style=style,
        )
        output_files = self.output_writer.save_ctr_pack(
            ctr_pack=ctr_pack,
            opportunities=opportunities,
        )
        if getattr(self.settings, "enable_verified_brief", True):
            output_files["verified_brief"] = self.output_writer.save_verified_brief(
                scan_result.get("verified_brief", {})
            )
        return {
            "status": "ok",
            "scan": scan_result,
            "opportunity_count": len(opportunities),
            "output_files": output_files,
            "ctr_pack": ctr_pack,
        }

    def fresh_optimize(self, *, style: str = "", limit: int = 10) -> dict[str, Any]:
        cleared_files = self.output_writer.clear_generated_files()
        cleared_opportunities = self.db.clear_opportunities()
        result = self.optimize_ctr(style=style, limit=limit)
        result["cleared"] = {
            "files": cleared_files,
            "opportunities": cleared_opportunities,
        }
        return result

    def reply_scout(self, *, handles: list[str], limit: int = 10) -> dict[str, Any]:
        self._last_x_errors = []
        source_tweets = self.web_client.fetch_reply_scout_items(
            handles,
            max_results_per_handle=max(limit, 3),
        )

        reply_pack = ReplyScout().build_pack(source_tweets, limit=limit)
        output_files = self.output_writer.save_reply_scout_pack(reply_pack=reply_pack)
        return {
            "status": "ok" if source_tweets else "no_sources",
            "handles": handles,
            "source_count": len(source_tweets),
            "web_scrape_errors": self.web_client.last_errors[:5],
            "output_files": output_files,
            "reply_pack": reply_pack,
        }

    def optimize_manual_source(
        self,
        *,
        source_text: str,
        source_url: str = "",
        source_title: str = "",
        style: str = "",
        limit: int = 5,
    ) -> dict[str, Any]:
        item = self._manual_source_item(
            source_text=source_text,
            source_url=source_url,
            source_title=source_title,
        )
        topic_query = "manual signal"
        raw_opportunities = self.writer.find_opportunities(
            topic_query=topic_query,
            source_items=[item],
        )
        opportunities = [
            self._manual_opportunity_payload(opportunity, item, index)
            for index, opportunity in enumerate(raw_opportunities[:limit], start=1)
        ]
        ctr_pack = self.writer.build_ctr_pack(
            opportunities=opportunities,
            style=style
            or "factual, statement-led, India-aware, copy-paste ready, no hype",
        )
        output_files = self.output_writer.save_ctr_pack(
            ctr_pack=ctr_pack,
            opportunities=opportunities,
        )
        return {
            "status": "ok",
            "source_count": 1,
            "opportunity_count": len(opportunities),
            "output_files": output_files,
            "ctr_pack": ctr_pack,
        }

    def set_topic(self, topic_query: str) -> str:
        normalized = self._normalize_query(topic_query)
        self.db.set_topic_query(normalized)
        return normalized

    def get_topic(self) -> str:
        return self.db.get_topic_query(self.settings.topic_query)

    def list_opportunities(self) -> list[dict[str, Any]]:
        return [
            self._opportunity_payload(row)
            for row in self.db.list_recent_opportunities()
        ]

    def handle_text_command(self, message: str) -> str:
        text = message.strip()
        upper = text.upper()

        if upper == "HELP":
            return self._help_message()
        if upper == "TOPIC":
            return f"Current tracked query:\n{self.get_topic()}"
        if upper == "LIST":
            return self._list_message()
        if upper == "SCAN":
            return self._scan_message()

        track_match = re.fullmatch(r"TRACK\s+(.+)", text, re.IGNORECASE | re.DOTALL)
        if track_match:
            topic = self.set_topic(track_match.group(1).strip())
            return f"Updated tracked query:\n{topic}"

        draft_match = re.fullmatch(r"DRAFT\s+(\d+)(?::\s*(.+))?", text, re.IGNORECASE | re.DOTALL)
        if draft_match:
            style = draft_match.group(2) or ""
            drafted = self.draft_post(int(draft_match.group(1)), style)
            return (
                f"Draft for opportunity #{drafted['id']}:\n\n"
                f"{drafted['draft_text']}\n\n"
                f"Notes:\n{drafted['draft_notes']}"
            )

        return "I didn't understand that.\n\n" + self._help_message()

    def _scan_message(self) -> str:
        result = self.scan()
        if result["status"] == "no_sources":
            return f"No matching X or web feed items found for:\n{result['topic_query']}"
        if not result["opportunities"]:
            return (
                "Scan finished, but there were no new opportunities. "
                f"{result['duplicate_count']} matched older scans."
            )

        lines = ["New post opportunities:"]
        for opportunity in result["opportunities"]:
            lines.append(f"#{opportunity['id']}: {opportunity['title']}")
            lines.append(f"Why now: {opportunity['why_now']}")
            lines.append(f"Angle: {opportunity['post_angle']}")
        lines.append("")
        lines.append("Use DRAFT <id> when you want me to write one.")
        return "\n".join(lines)

    def _list_message(self) -> str:
        opportunities = self.list_opportunities()
        if not opportunities:
            return "No opportunities have been found yet. Use SCAN first."
        lines = ["Recent opportunities:"]
        for opportunity in opportunities:
            lines.append(
                f"#{opportunity['id']}: {opportunity['title']} "
                f"({opportunity['status']})"
            )
        return "\n".join(lines)

    def _help_message(self) -> str:
        return (
            "Commands:\n"
            "TRACK <keywords or X query>\n"
            "TOPIC\n"
            "SCAN\n"
            "LIST\n"
            "DRAFT <id>\n"
            "DRAFT <id>: make it more factual\n"
            "BRIEF"
        )

    def _collect_sources(self, topic_query: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        self._last_x_errors = []
        if (
            self.settings.enable_x_watchlist
            and self.settings.x_bearer_token
            and self.settings.x_watch_handles
        ):
            try:
                items.extend(
                    self.x_client.search_watchlist_posts(
                        self.settings.x_watch_handles,
                        self.settings.max_watchlist_results,
                    )
                )
            except Exception as exc:
                self._last_x_errors.append(f"watchlist: {exc}")
        if self.settings.enable_x_timeline:
            try:
                items.extend(
                    self.x_client.fetch_home_timeline(
                        self.settings.max_timeline_results,
                    )
                )
            except Exception as exc:
                self._last_x_errors.append(f"timeline: {exc}")
        if self.settings.enable_x_scan and self.settings.x_bearer_token:
            try:
                items.extend(
                    self.x_client.search_recent_posts(
                        topic_query,
                        self.settings.max_search_results,
                    )
                )
            except Exception as exc:
                self._last_x_errors.append(f"topic search: {exc}")
        if self.settings.enable_web_scan:
            items.extend(self.web_client.fetch_items())
        return self._select_items(items)

    def _openai_research_sources(self, topic_query: str) -> list[dict[str, Any]]:
        records = self.researcher.research(topic_query)
        items: list[dict[str, Any]] = []
        for record in records:
            source_url = str(record.get("source_url", "")).strip()
            title = str(record.get("title", "")).strip()
            if not source_url or not title:
                continue
            source_name = str(record.get("source_name", "OpenAI web research")).strip()
            text = "\n".join(
                value
                for value in [
                    title,
                    str(record.get("what_happened", "")).strip(),
                    str(record.get("why_it_matters", "")).strip(),
                ]
                if value
            )
            items.append(
                {
                    "id": source_url,
                    "source_type": "openai_web_research",
                    "title": title,
                    "text": text,
                    "created_at": str(record.get("published_at", "")),
                    "author_name": source_name,
                    "author_username": source_name.lower().replace(" ", "-")[:80],
                    "public_metrics": {"like_count": 0, "retweet_count": 0, "quote_count": 0},
                    "score": float(record.get("confidence", 0.75) or 0.75) * 1_000,
                    "url": source_url,
                }
            )
        return items

    def _post_ready_sources(
        self,
        discovered: list[dict[str, Any]],
        verified_brief: dict[str, Any],
    ) -> list[dict[str, Any]]:
        ready_urls = {
            str(item.get("source_url", ""))
            for item in verified_brief.get("items", [])
            if item.get("eligible") and item.get("source_level") in {"primary", "web_researched", "reputable"}
        }
        return [item for item in discovered if item.get("url") in ready_urls]

    def _research_status(self) -> dict[str, Any]:
        return {
            "enabled": self.researcher.enabled,
            "configured": self.researcher.configured,
            "error": self.researcher.last_error,
        }

    def _select_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        author_counts: dict[str, int] = {}
        seen_urls: set[str] = set()
        # A web-research response often uses a date-only publication date while
        # RSS entries use a timestamp.  Sort by recency first, then promote the
        # direct research results so they are not accidentally pushed out by a
        # breaking-news cluster from Google News.
        ranked_items = sorted(items, key=lambda value: value.get("created_at", ""), reverse=True)
        ranked_items.sort(key=lambda value: value.get("source_type") != "openai_web_research")
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
        for item in ranked_items:
            buckets[self._source_category(item)].append(item)

        # Select breadth-first rather than letting a fast-moving AI or chip
        # headline cluster monopolise the inbox. A focused mode still works:
        # when every item is in one category, this reduces to normal recency.
        # Keep a larger candidate pool here. The verification step below this
        # selection can then choose trusted stories from every category instead
        # of being forced to use the first unverified headline in a feed.
        candidate_limit = 36
        while len(selected) < candidate_limit:
            added = False
            for category in categories:
                candidates = buckets[category]
                while candidates:
                    item = candidates.pop(0)
                    username = item.get("author_username", item.get("author_name", "unknown"))
                    url = item["url"]
                    if url in seen_urls:
                        continue
                    # RSS items share the feed URL as their author. Keep a small batch
                    # from a curated feed while limiting repetitive sources.
                    per_source_limit = 4 if item.get("source_type") == "web" else 1
                    if author_counts.get(username, 0) >= per_source_limit:
                        continue
                    selected.append(item)
                    author_counts[username] = author_counts.get(username, 0) + 1
                    seen_urls.add(url)
                    added = True
                    break
                if len(selected) == candidate_limit:
                    break
            if not added:
                break
        return selected

    def _source_category(self, item: dict[str, Any]) -> str:
        text = " ".join(
            (str(item.get("title", "")), str(item.get("text", "")))
        ).lower()
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

    def _manual_source_item(
        self,
        *,
        source_text: str,
        source_url: str,
        source_title: str,
    ) -> dict[str, Any]:
        clean_text = " ".join(source_text.split())
        title = source_title.strip() or clean_text[:90] or "Manual source"
        url = source_url.strip() or "manual://source"
        return {
            "id": hashlib.sha256(f"{url}|{clean_text}".encode("utf-8")).hexdigest()[:16],
            "source_type": "manual",
            "title": title,
            "text": clean_text,
            "created_at": "",
            "author_name": "manual input",
            "author_username": "manual",
            "public_metrics": {"like_count": 0, "retweet_count": 0, "quote_count": 0},
            "score": 0,
            "url": url,
        }

    def _manual_opportunity_payload(
        self,
        opportunity: dict[str, Any],
        source_item: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        return {
            "id": index,
            "status": "manual",
            "topic_query": "manual signal",
            "title": str(opportunity.get("title", source_item["title"])),
            "category": str(opportunity.get("category", "General Tech")),
            "why_now": str(opportunity.get("why_now", "")),
            "post_angle": str(opportunity.get("post_angle", "")),
            "confidence": float(opportunity.get("confidence", 0.5)),
            "sources": [source_item],
            "draft_text": None,
            "draft_notes": None,
            "created_at": "",
        }

    def _items_for_opportunity(
        self,
        opportunity: dict[str, Any],
        selected_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        source_ids = {
            str(source_id)
            for source_id in (
                opportunity.get("source_ids", [])
                or opportunity.get("source_post_ids", [])
            )
        }
        matched = [item for item in selected_items if item["id"] in source_ids]
        return matched or selected_items[:3]

    def _fingerprint(
        self,
        opportunity: dict[str, Any],
        source_items: list[dict[str, Any]],
        topic_query: str,
    ) -> str:
        joined = "|".join(
            [
                topic_query,
                str(opportunity.get("title", "")).lower(),
                *[item["id"] for item in source_items],
            ]
        )
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def _opportunity_payload(self, row: Any) -> dict[str, Any]:
        if row is None:
            raise RuntimeError("Opportunity lookup failed immediately after save.")
        return {
            "id": row["id"],
            "status": row["status"],
            "topic_query": row["topic_query"],
            "title": row["title"],
            "category": row["category"],
            "why_now": row["why_now"],
            "post_angle": row["post_angle"],
            "confidence": row["confidence"],
            "sources": json.loads(row["source_json"]),
            "draft_text": row["draft_text"],
            "draft_notes": row["draft_notes"],
            "created_at": row["created_at"],
        }

    def _normalize_query(self, topic_query: str) -> str:
        compact = " ".join(topic_query.split())
        if " lang:" in compact.lower() or compact.lower().startswith("lang:"):
            return compact
        return f"({compact}) lang:en -is:retweet"

    def _diverse_opportunities(
        self,
        opportunities: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        seen_categories: set[str] = set()
        for opportunity in opportunities:
            category = opportunity.get("category", "General Tech")
            if category in seen_categories:
                continue
            selected.append(opportunity)
            seen_categories.add(category)
            if len(selected) == limit:
                return selected

        for opportunity in opportunities:
            if opportunity in selected:
                continue
            selected.append(opportunity)
            if len(selected) == limit:
                return selected
        return selected
