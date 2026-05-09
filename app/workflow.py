from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.ai_writer import TrendWriter
from app.config import Settings
from app.db import Database
from app.output_writer import OutputWriter
from app.web_client import WebFeedClient
from app.x_client import XClient


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
    ) -> None:
        self.settings = settings
        self.db = db
        self.x_client = x_client
        self.web_client = web_client
        self.writer = writer
        self.output_writer = output_writer

    def scan(self) -> dict[str, Any]:
        topic_query = self.db.get_topic_query(self.settings.topic_query)
        selected = self._collect_sources(topic_query)
        if not selected:
            return {"status": "no_sources", "topic_query": topic_query, "opportunities": []}

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
            "x_source_count": len(
                [item for item in selected if item.get("source_type") == "x"]
            ),
            "web_source_count": len(
                [item for item in selected if item.get("source_type") == "web"]
            ),
            "web_feed_errors": self.web_client.last_errors[:5],
            "created_count": len(created),
            "duplicate_count": duplicates,
            "opportunities": created,
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
        return {
            "status": "ok",
            "scan": scan_result,
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
            "DRAFT <id>: write it more contrarian\n"
            "BRIEF"
        )

    def _collect_sources(self, topic_query: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if self.settings.enable_x_scan and self.settings.x_bearer_token:
            try:
                items.extend(
                    self.x_client.search_recent_posts(
                        topic_query,
                        self.settings.max_search_results,
                    )
                )
            except Exception:
                pass
        if self.settings.enable_web_scan:
            items.extend(self.web_client.fetch_items())
        return self._select_items(items)

    def _select_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        seen_authors: set[str] = set()
        seen_urls: set[str] = set()
        for item in sorted(items, key=lambda value: value.get("created_at", ""), reverse=True):
            username = item.get("author_username", item.get("author_name", "unknown"))
            url = item["url"]
            if url in seen_urls:
                continue
            if username in seen_authors:
                continue
            selected.append(item)
            seen_authors.add(username)
            seen_urls.add(url)
            if len(selected) == 12:
                break
        return selected

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
