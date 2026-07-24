from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import email.utils
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from typing import Any

import requests

from app.config import Settings


class WebFeedClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.last_errors: list[str] = []

    def fetch_items(self) -> list[dict[str, Any]]:
        self.last_errors = []
        if not self.settings.web_feed_urls:
            return []

        items: list[dict[str, Any]] = []

        def fetch_one(url: str) -> tuple[str, list[dict[str, Any]], Exception | None]:
            try:
                feed_items = self._fetch_feed(url)
                if self.settings.web_keywords:
                    feed_items = [item for item in feed_items if self._matches_keywords(item)]
                return url, feed_items, None
            except (requests.RequestException, ET.ParseError) as exc:
                return url, [], exc

        max_workers = min(6, len(self.settings.web_feed_urls))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_one, url) for url in self.settings.web_feed_urls]
            for future in as_completed(futures):
                url, feed_items, error = future.result()
                if error is not None:
                    self.last_errors.append(f"{url}: {error}")
                    continue
                items.extend(feed_items)

        items.sort(key=lambda item: item["created_at"], reverse=True)
        return items[: self.settings.max_web_results]

    def _matches_keywords(self, item: dict[str, Any]) -> bool:
        haystack = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("text", "")),
                str(item.get("author_name", "")),
            ]
        ).lower()
        return any(keyword.lower() in haystack for keyword in self.settings.web_keywords)

    def fetch_reply_scout_items(
        self,
        handles: list[str],
        *,
        max_results_per_handle: int = 10,
    ) -> list[dict[str, Any]]:
        """Fetch public account posts through web/RSS mirrors, not X API.

        This intentionally does not call xurl, Twitter/X API search, or any OAuth
        path. It uses public web RSS mirrors where available and converts the
        returned entries into the same source-item shape used by ReplyScout.
        """

        self.last_errors = []
        scraped: list[dict[str, Any]] = []
        for handle in handles:
            clean_handle = handle.strip().lstrip("@")
            if not clean_handle:
                continue

            handle_items: list[dict[str, Any]] = []
            handle_errors: list[str] = []
            for url in self._reply_scout_feed_urls(clean_handle):
                try:
                    feed_items = self._fetch_feed(url)
                except (requests.RequestException, ET.ParseError, ValueError) as exc:
                    handle_errors.append(f"{url}: {exc}")
                    continue

                handle_items = [
                    self._reply_scout_item(item, clean_handle)
                    for item in feed_items
                    if item.get("text") and item.get("url")
                ][:max_results_per_handle]
                if handle_items:
                    break

            if not handle_items:
                try:
                    handle_items = self._fetch_reply_scout_profile(clean_handle)[:max_results_per_handle]
                except requests.RequestException as exc:
                    handle_errors.append(f"profile scrape: {exc}")

            if handle_items:
                scraped.extend(handle_items)
            elif handle_errors:
                self.last_errors.append(f"@{clean_handle}: " + " | ".join(handle_errors[:2]))

        scraped.sort(key=lambda item: (item.get("score", 0), item.get("created_at", "")), reverse=True)
        return scraped[: self.settings.max_web_results]

    def _reply_scout_feed_urls(self, handle: str) -> list[str]:
        return [
            f"https://nitter.net/{handle}/rss",
            f"https://xcancel.com/{handle}/rss",
            f"https://twiiit.com/{handle}/rss",
            f"https://rsshub.app/twitter/user/{handle}",
        ]

    def _fetch_reply_scout_profile(self, handle: str) -> list[dict[str, Any]]:
        url = f"https://r.jina.ai/http://https://x.com/{handle}"
        timeout_seconds = max(3, min(int(getattr(self.settings, "web_feed_timeout_seconds", 8)), 30))
        response = requests.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        posts = self._parse_jina_profile_posts(response.text)
        now = datetime.now(timezone.utc).isoformat()
        return [
            {
                "id": f"https://x.com/{handle}#{index}",
                "source_type": "web_reply_scout",
                "title": post,
                "text": post,
                "created_at": now,
                "author_name": f"@{handle}",
                "author_username": handle,
                "public_metrics": {"like_count": 0, "retweet_count": 0, "reply_count": 0, "quote_count": 0},
                "score": 1_000_000 - index,
                "url": f"https://x.com/{handle}",
            }
            for index, post in enumerate(posts, start=1)
        ]

    def _parse_jina_profile_posts(self, markdown: str) -> list[str]:
        marker = re.search(r"^## .*posts\s*$", markdown, flags=re.MULTILINE | re.IGNORECASE)
        if not marker:
            return []
        body = markdown[marker.end() :]
        body = re.split(r"^## ", body, maxsplit=1, flags=re.MULTILINE)[0]
        chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", body) if chunk.strip()]
        posts: list[str] = []
        skip_exact = {"quote", "readers added context", "show more", "repost", "like"}
        for chunk in chunks:
            plain = self._clean_feed_text(re.sub(r"!?\[[^\]]*\]\([^)]*\)", "", chunk))
            if not plain or plain.lower() in skip_exact:
                continue
            if plain.startswith("@") or len(plain) < 12:
                continue
            posts.append(plain)
            if len(posts) >= 20:
                break
        return posts

    def _reply_scout_item(self, item: dict[str, Any], handle: str) -> dict[str, Any]:
        text = self._clean_feed_text(str(item.get("text", "")))
        created_at = str(item.get("created_at", ""))
        return {
            "id": str(item.get("id") or item.get("url") or f"{handle}:{created_at}"),
            "source_type": "web_reply_scout",
            "title": str(item.get("title", "")),
            "text": text,
            "created_at": created_at,
            "author_name": f"@{handle}",
            "author_username": handle,
            "public_metrics": {"like_count": 0, "retweet_count": 0, "reply_count": 0, "quote_count": 0},
            "score": self._recency_score(created_at),
            "url": str(item.get("url", "")),
        }

    def _clean_feed_text(self, value: str) -> str:
        return " ".join(unescape(value).split())

    def _recency_score(self, created_at: str) -> float:
        try:
            parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
        age_seconds = max((datetime.now(timezone.utc) - parsed).total_seconds(), 0)
        return max(0.0, 1_000_000.0 - age_seconds)

    def _fetch_feed(self, url: str) -> list[dict[str, Any]]:
        timeout_seconds = max(3, min(int(getattr(self.settings, "web_feed_timeout_seconds", 8)), 30))
        response = requests.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        content = response.content
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            # Some otherwise-useful publisher feeds contain unescaped ampersands
            # in URLs or headlines. Repair only invalid entities, then parse
            # again so a single bad character does not discard the whole feed.
            repaired = re.sub(
                rb"&(?!#?[0-9a-zA-Z]+;)",
                b"&amp;",
                content,
            )
            root = ET.fromstring(repaired)
        if root.tag.endswith("rss"):
            return self._parse_rss(root, url)
        return self._parse_atom(root, url)

    def _parse_rss(self, root: ET.Element, feed_url: str) -> list[dict[str, Any]]:
        items = []
        for item in root.findall("./channel/item"):
            title = self._text(item, "title")
            link = self._text(item, "link")
            summary = self._text(item, "description")
            source_name, publisher_url = self._rss_source(item)
            created_at = self._parse_date(
                self._text(item, "pubDate") or self._text(item, "updated")
            )
            if title and link:
                items.append(
                    self._item(
                        feed_url,
                        title,
                        link,
                        summary,
                        created_at,
                        source_name,
                        publisher_url,
                    )
                )
        return items

    def _rss_source(self, item: ET.Element) -> tuple[str, str]:
        """Keep the original publisher behind a Google News RSS result.

        Google News article links live on news.google.com, but the RSS ``source``
        tag includes the original publisher and its domain.  Keeping both lets the
        verification layer distinguish an OpenAI/Reuters story from an unknown blog.
        """
        source = item.find("source")
        if source is None:
            return "", ""
        name = " ".join((source.text or "").split())
        return name, str(source.attrib.get("url", "")).strip()

    def _parse_atom(self, root: ET.Element, feed_url: str) -> list[dict[str, Any]]:
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", namespace) or root.findall("entry")
        items = []
        for entry in entries:
            title = self._text(entry, "title", namespace)
            link = self._atom_link(entry, namespace)
            summary = (
                self._text(entry, "summary", namespace)
                or self._text(entry, "content", namespace)
            )
            created_at = self._parse_date(
                self._text(entry, "published", namespace)
                or self._text(entry, "updated", namespace)
            )
            if title and link:
                items.append(self._item(feed_url, title, link, summary, created_at))
        return items

    def _item(
        self,
        feed_url: str,
        title: str,
        url: str,
        summary: str,
        created_at: str,
        source_name: str = "",
        publisher_url: str = "",
    ) -> dict[str, Any]:
        return {
            "id": url,
            "source_type": "web",
            "title": title,
            "text": f"{title}\n{summary}".strip(),
            "created_at": created_at,
            "author_name": source_name or feed_url,
            "author_username": source_name or feed_url,
            "publisher_url": publisher_url,
            "public_metrics": {"like_count": 0, "retweet_count": 0, "quote_count": 0},
            "score": 0,
            "url": url,
        }

    def _text(
        self,
        element: ET.Element,
        tag: str,
        namespace: dict[str, str] | None = None,
    ) -> str:
        namespace = namespace or {}
        child = None
        if namespace:
            child = element.find(f"atom:{tag}", namespace)
        if child is None:
            child = element.find(tag)
        if child is None:
            child = element.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
        if child is None or child.text is None:
            return ""
        return " ".join(child.text.split())

    def _atom_link(self, entry: ET.Element, namespace: dict[str, str]) -> str:
        link = entry.find("atom:link", namespace)
        if link is None:
            link = entry.find("link")
        if link is None:
            link = entry.find("{http://www.w3.org/2005/Atom}link")
        if link is None:
            return ""
        return link.attrib.get("href", "")

    def _parse_date(self, value: str) -> str:
        if not value:
            return datetime.now(timezone.utc).isoformat()
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = email.utils.parsedate_to_datetime(value)
            except (TypeError, ValueError):
                return datetime.now(timezone.utc).isoformat()
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
