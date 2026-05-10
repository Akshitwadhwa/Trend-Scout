from __future__ import annotations

import email.utils
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
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
        for url in self.settings.web_feed_urls:
            try:
                items.extend(self._fetch_feed(url))
            except requests.RequestException as exc:
                self.last_errors.append(f"{url}: {exc}")
                continue
            except ET.ParseError as exc:
                self.last_errors.append(f"{url}: {exc}")
                continue

        items.sort(key=lambda item: item["created_at"], reverse=True)
        return items[: self.settings.max_web_results]

    def _fetch_feed(self, url: str) -> list[dict[str, Any]]:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        if root.tag.endswith("rss"):
            return self._parse_rss(root, url)
        return self._parse_atom(root, url)

    def _parse_rss(self, root: ET.Element, feed_url: str) -> list[dict[str, Any]]:
        items = []
        for item in root.findall("./channel/item"):
            title = self._text(item, "title")
            link = self._text(item, "link")
            summary = self._text(item, "description")
            created_at = self._parse_date(
                self._text(item, "pubDate") or self._text(item, "updated")
            )
            if title and link:
                items.append(self._item(feed_url, title, link, summary, created_at))
        return items

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
    ) -> dict[str, Any]:
        return {
            "id": url,
            "source_type": "web",
            "title": title,
            "text": f"{title}\n{summary}".strip(),
            "created_at": created_at,
            "author_name": feed_url,
            "author_username": feed_url,
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
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
