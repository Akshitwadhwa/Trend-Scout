from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings


class OutputWriter:
    def __init__(self, settings: Settings) -> None:
        self.output_dir = settings.output_dir
        self.high_ctr_dir = settings.high_ctr_dir
        self.json_dir = settings.json_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.high_ctr_dir.mkdir(parents=True, exist_ok=True)
        self.json_dir.mkdir(parents=True, exist_ok=True)

    def save_draft(self, drafted: dict[str, Any]) -> dict[str, str]:
        opportunity_id = drafted["id"]
        slug = self._slugify(drafted["title"])
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        category = self._slugify(drafted.get("category", "general-tech"))
        base_name = f"tweet-{opportunity_id}-{timestamp}-{category}-{slug}"
        markdown_path = self.output_dir / f"{base_name}.md"
        json_path = self.json_dir / f"{base_name}.json"

        markdown_path.write_text(self._markdown(drafted), encoding="utf-8")
        json_path.write_text(
            json.dumps(drafted, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

        return {
            "markdown": str(markdown_path),
            "json": str(json_path),
        }

    def save_content_pack(
        self,
        *,
        content_pack: dict[str, Any],
        opportunities: list[dict[str, Any]],
    ) -> dict[str, str]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        markdown_path = self.output_dir / f"{timestamp}-tech-content-pack.md"
        json_path = self.json_dir / f"{timestamp}-tech-content-pack.json"
        best_path = self.output_dir / f"{timestamp}-best-posts-ranked.md"

        pack = {
            "generated_at": timestamp,
            "content_pack": content_pack,
            "opportunities": opportunities,
        }
        markdown_path.write_text(
            self._content_pack_markdown(content_pack, opportunities),
            encoding="utf-8",
        )
        best_path.write_text(
            self._best_posts_markdown(content_pack),
            encoding="utf-8",
        )
        json_path.write_text(json.dumps(pack, ensure_ascii=True, indent=2), encoding="utf-8")

        category_paths = self._save_category_files(timestamp, content_pack)
        return {
            "markdown": str(markdown_path),
            "json": str(json_path),
            "best_posts": str(best_path),
            "category_files": category_paths,
        }

    def save_ctr_pack(
        self,
        *,
        ctr_pack: dict[str, Any],
        opportunities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        main_path = self.high_ctr_dir / f"{timestamp}-high-ctr-pack.md"
        hooks_path = self.high_ctr_dir / f"{timestamp}-hooks.md"
        polls_path = self.high_ctr_dir / f"{timestamp}-polls.md"
        replies_path = self.high_ctr_dir / f"{timestamp}-reply-opportunities.md"
        threads_path = self.high_ctr_dir / f"{timestamp}-threads.md"
        visual_path = self.high_ctr_dir / f"{timestamp}-visual-card-ideas.md"
        json_path = self.json_dir / f"{timestamp}-high-ctr-pack.json"

        payload = {
            "generated_at": timestamp,
            "ctr_pack": ctr_pack,
            "opportunities": opportunities,
        }
        main_path.write_text(self._ctr_pack_markdown(ctr_pack, opportunities), encoding="utf-8")
        hooks_path.write_text(self._hooks_markdown(ctr_pack), encoding="utf-8")
        polls_path.write_text(self._polls_markdown(ctr_pack), encoding="utf-8")
        replies_path.write_text(self._replies_markdown(ctr_pack), encoding="utf-8")
        threads_path.write_text(self._threads_markdown(ctr_pack), encoding="utf-8")
        visual_path.write_text(self._visuals_markdown(ctr_pack), encoding="utf-8")
        json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

        category_files = self._save_ctr_category_files(timestamp, ctr_pack)
        return {
            "markdown": str(main_path),
            "hooks": str(hooks_path),
            "polls": str(polls_path),
            "replies": str(replies_path),
            "threads": str(threads_path),
            "visuals": str(visual_path),
            "category_files": category_files,
            "json": str(json_path),
        }

    def clear_generated_files(self) -> dict[str, int]:
        return {
            "outputs": self._clear_directory(self.output_dir, ".md"),
            "out": self._clear_directory(self.high_ctr_dir, ".md"),
            "json": self._clear_directory(self.json_dir, ".json"),
        }

    def _markdown(self, drafted: dict[str, Any]) -> str:
        sources = drafted.get("sources", [])
        source_lines = []
        for source in sources:
            title = source.get("title") or source.get("author_username") or "source"
            source_lines.append(f"- {title}: {source['url']}")

        return "\n".join(
            [
                f"# Tweet Draft #{drafted['id']}",
                "",
                "## Tweet",
                "",
                drafted.get("draft_text") or "",
                "",
                "## Notes",
                "",
                drafted.get("draft_notes") or "",
                "",
                "## Opportunity",
                "",
                f"Category: {drafted.get('category', 'General Tech')}",
                f"Title: {drafted['title']}",
                f"Why now: {drafted['why_now']}",
                f"Angle: {drafted['post_angle']}",
                f"Confidence: {drafted['confidence']}",
                "",
                "## Sources",
                "",
                "\n".join(source_lines),
                "",
            ]
        )

    def _content_pack_markdown(
        self,
        content_pack: dict[str, Any],
        opportunities: list[dict[str, Any]],
    ) -> str:
        lines = [
            "# Daily Tech Content Pack",
            "",
            "## Summary",
            "",
            content_pack.get("summary", ""),
            "",
            "## Ranked Posts",
            "",
        ]
        for post in content_pack.get("posts", []):
            lines.extend(self._post_section(post))
        lines.extend(["", "## Source Opportunities", ""])
        for opportunity in opportunities:
            lines.extend(
                [
                    f"### #{opportunity['id']} - {opportunity['title']}",
                    "",
                    f"Category: {opportunity.get('category', 'General Tech')}",
                    f"Confidence: {opportunity.get('confidence')}",
                    f"Why now: {opportunity.get('why_now')}",
                    f"Angle: {opportunity.get('post_angle')}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _best_posts_markdown(self, content_pack: dict[str, Any]) -> str:
        lines = ["# Best Posts Ranked", ""]
        for post in content_pack.get("posts", []):
            rank = post.get("rank", "?")
            lines.extend(
                [
                    f"## {rank}. {post.get('category', 'General Tech')} - {post.get('format', 'post')}",
                    "",
                    post.get("post", ""),
                    "",
                    f"Hook: {post.get('hook', '')}",
                    f"Why it can work: {post.get('why_it_can_work', '')}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _save_category_files(
        self,
        timestamp: str,
        content_pack: dict[str, Any],
    ) -> list[str]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for post in content_pack.get("posts", []):
            category = post.get("category", "General Tech")
            grouped.setdefault(category, []).append(post)

        paths = []
        for category, posts in grouped.items():
            path = self.output_dir / f"{timestamp}-{self._slugify(category)}-tweets.md"
            lines = [f"# {category} Tweets", ""]
            for post in posts:
                lines.extend(self._post_section(post))
            path.write_text("\n".join(lines), encoding="utf-8")
            paths.append(str(path))
        return paths

    def _ctr_pack_markdown(
        self,
        ctr_pack: dict[str, Any],
        opportunities: list[dict[str, Any]],
    ) -> str:
        lines = [
            "# High CTR X Pack",
            "",
            "## Summary",
            "",
            ctr_pack.get("summary", ""),
            "",
            "## Ranked CTR Ideas",
            "",
        ]
        for index, item in enumerate(self._ranked_ctr_items(ctr_pack), start=1):
            lines.extend(self._ctr_item_section(item, index))
        lines.extend(["", "## Source Opportunities", ""])
        for opportunity in opportunities:
            lines.extend(
                [
                    f"### #{opportunity['id']} - {opportunity['title']}",
                    "",
                    f"Category: {opportunity.get('category', 'General Tech')}",
                    f"Confidence: {opportunity.get('confidence')}",
                    f"Why now: {opportunity.get('why_now')}",
                    f"Angle: {opportunity.get('post_angle')}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _hooks_markdown(self, ctr_pack: dict[str, Any]) -> str:
        lines = ["# Hooks", ""]
        for item in self._ranked_ctr_items(ctr_pack):
            lines.extend([f"## {item.get('category')} - {item.get('title')}", ""])
            for hook in item.get("hooks", []):
                lines.append(f"- {hook}")
            lines.append("")
        return "\n".join(lines)

    def _polls_markdown(self, ctr_pack: dict[str, Any]) -> str:
        lines = ["# Polls", ""]
        for item in self._ranked_ctr_items(ctr_pack):
            poll = item.get("poll") or {}
            if not poll:
                continue
            lines.extend([f"## {item.get('category')} - {item.get('title')}", "", poll.get("question", ""), ""])
            for option in poll.get("options", []):
                lines.append(f"- {option}")
            lines.append("")
        return "\n".join(lines)

    def _replies_markdown(self, ctr_pack: dict[str, Any]) -> str:
        lines = ["# Reply Opportunities", ""]
        for item in self._ranked_ctr_items(ctr_pack):
            lines.extend(
                [
                    f"## {item.get('category')} - {item.get('title')}",
                    "",
                    item.get("reply_post", ""),
                    "",
                ]
            )
        return "\n".join(lines)

    def _threads_markdown(self, ctr_pack: dict[str, Any]) -> str:
        lines = ["# Mini Threads", ""]
        for item in self._ranked_ctr_items(ctr_pack):
            lines.extend([f"## {item.get('category')} - {item.get('title')}", ""])
            for index, post in enumerate(item.get("mini_thread", []), start=1):
                lines.append(f"{index}. {post}")
            lines.append("")
        return "\n".join(lines)

    def _visuals_markdown(self, ctr_pack: dict[str, Any]) -> str:
        lines = ["# Visual Card Ideas", ""]
        for item in self._ranked_ctr_items(ctr_pack):
            lines.extend(
                [
                    f"## {item.get('category')} - {item.get('title')}",
                    "",
                    item.get("visual_card_idea", ""),
                    "",
                ]
            )
        return "\n".join(lines)

    def _save_ctr_category_files(
        self,
        timestamp: str,
        ctr_pack: dict[str, Any],
    ) -> list[str]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in ctr_pack.get("items", []):
            grouped.setdefault(item.get("category", "General Tech"), []).append(item)

        paths = []
        for category, items in grouped.items():
            path = self.high_ctr_dir / f"{timestamp}-{self._slugify(category)}-high-ctr.md"
            lines = [f"# {category} High CTR Ideas", ""]
            for index, item in enumerate(items, start=1):
                lines.extend(self._ctr_item_section(item, index))
            path.write_text("\n".join(lines), encoding="utf-8")
            paths.append(str(path))
        return paths

    def _ctr_item_section(self, item: dict[str, Any], index: int) -> list[str]:
        lines = [
            f"### {index}. {item.get('category', 'General Tech')} - {item.get('title', '')}",
            "",
            f"CTR score: {item.get('ctr_score')}",
            f"Impression score: {item.get('impression_score')}",
            f"Reply score: {item.get('reply_score')}",
            f"Risk score: {item.get('risk_score')}",
            "",
            f"Best angle: {item.get('best_angle', '')}",
            f"Best hook: {item.get('best_hook', '')}",
            "",
            "Post variants:",
        ]
        for variant in item.get("post_variants", []):
            lines.append(f"- {variant}")
        lines.extend(["", "Top hooks:"])
        for hook in item.get("hooks", [])[:10]:
            lines.append(f"- {hook}")
        poll = item.get("poll") or {}
        if poll:
            lines.extend(["", f"Poll: {poll.get('question', '')}"])
            for option in poll.get("options", []):
                lines.append(f"- {option}")
        lines.extend(["", f"Reply post: {item.get('reply_post', '')}", "", "Mini-thread:"])
        for thread_post in item.get("mini_thread", []):
            lines.append(f"- {thread_post}")
        lines.extend(
            [
                "",
                f"Visual card idea: {item.get('visual_card_idea', '')}",
                f"Why this can work: {item.get('why_this_can_work', '')}",
                "",
            ]
        )
        return lines

    def _ranked_ctr_items(self, ctr_pack: dict[str, Any]) -> list[dict[str, Any]]:
        return sorted(
            ctr_pack.get("items", []),
            key=lambda item: (
                item.get("ctr_score", 0),
                item.get("impression_score", 0),
                item.get("reply_score", 0),
            ),
            reverse=True,
        )

    def _clear_directory(self, path: Path, suffix: str) -> int:
        deleted = 0
        path.mkdir(parents=True, exist_ok=True)
        for item in path.iterdir():
            if item.name == ".gitkeep" or not item.is_file():
                continue
            if item.suffix == suffix:
                item.unlink()
                deleted += 1
        return deleted

    def _post_section(self, post: dict[str, Any]) -> list[str]:
        lines = [
            f"### Rank {post.get('rank', '?')} - {post.get('category', 'General Tech')} / {post.get('format', 'post')}",
            "",
            f"Hook: {post.get('hook', '')}",
            "",
            post.get("post", ""),
            "",
        ]
        poll_options = post.get("poll_options") or []
        if poll_options:
            lines.extend(["Poll options:", *[f"- {option}" for option in poll_options], ""])
        thread = post.get("thread") or []
        if thread:
            lines.extend(["Thread:", *[f"{index}. {item}" for index, item in enumerate(thread, start=1)], ""])
        lines.extend(
            [
                f"Visual idea: {post.get('visual_idea', '')}",
                f"Why it can work: {post.get('why_it_can_work', '')}",
                "",
            ]
        )
        return lines

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
        return slug[:64] or "draft"
