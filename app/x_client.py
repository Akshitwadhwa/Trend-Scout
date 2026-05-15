from __future__ import annotations

import json
import subprocess
from typing import Any

import requests

from app.config import Settings


class XClient:
    search_url = "https://api.x.com/2/tweets/search/recent"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def search_watchlist_posts(
        self,
        handles: list[str],
        max_results: int,
    ) -> list[dict[str, Any]]:
        clean_handles = [self._clean_handle(handle) for handle in handles]
        clean_handles = [handle for handle in clean_handles if handle]
        if not clean_handles:
            return []
        query = "(" + " OR ".join(f"from:{handle}" for handle in clean_handles) + ") lang:en -is:retweet"
        posts = self.search_recent_posts(query, max_results)
        for post in posts:
            post["source_type"] = "x_watchlist"
            post["watchlist_handle"] = post.get("author_username", "")
        return posts

    def search_recent_posts(self, query: str, max_results: int) -> list[dict[str, Any]]:
        if not self.settings.x_bearer_token:
            raise RuntimeError("Missing X_BEARER_TOKEN for recent search.")

        response = requests.get(
            self.search_url,
            headers={"Authorization": f"Bearer {self.settings.x_bearer_token}"},
            params={
                "query": query,
                "max_results": max_results,
                "tweet.fields": "author_id,created_at,lang,public_metrics",
                "expansions": "author_id",
                "user.fields": "name,username,verified",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        users = {
            user["id"]: user for user in payload.get("includes", {}).get("users", [])
        }

        posts: list[dict[str, Any]] = []
        for item in payload.get("data", []):
            metrics = item.get("public_metrics", {})
            author = users.get(item.get("author_id"), {})
            username = author.get("username", "unknown")
            score = (
                metrics.get("like_count", 0)
                + metrics.get("retweet_count", 0) * 2
                + metrics.get("reply_count", 0) * 1.5
                + metrics.get("quote_count", 0) * 2
            )
            posts.append(
                {
                    "id": item["id"],
                    "source_type": "x",
                    "text": item["text"],
                    "created_at": item.get("created_at", ""),
                    "lang": item.get("lang", ""),
                    "author_name": author.get("name", username),
                    "author_username": username,
                    "author_verified": author.get("verified", False),
                    "public_metrics": metrics,
                    "score": score,
                    "url": f"https://x.com/{username}/status/{item['id']}",
                }
            )

        posts.sort(key=lambda post: (post["score"], post["created_at"]), reverse=True)
        return posts

    def fetch_home_timeline(self, max_results: int) -> list[dict[str, Any]]:
        """Fetch the authenticated user's X home timeline through xurl.

        This intentionally uses xurl instead of asking Hermes/the app to handle
        OAuth secrets. The user authenticates xurl locally once, then this app
        reads JSON from the CLI.
        """
        try:
            completed = subprocess.run(
                ["xurl", "timeline", "-n", str(max_results)],
                check=True,
                capture_output=True,
                text=True,
                timeout=45,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("xurl is not installed. Install/authenticate xurl first.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "xurl timeline failed").strip()
            raise RuntimeError(detail) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("xurl timeline timed out") from exc

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("xurl timeline returned non-JSON output") from exc

        return self._posts_from_xurl_payload(payload)

    def _posts_from_xurl_payload(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        users = {
            user.get("id"): user
            for user in payload.get("includes", {}).get("users", [])
            if user.get("id")
        }
        posts: list[dict[str, Any]] = []
        for item in payload.get("data", []) or []:
            author = users.get(item.get("author_id"), {})
            username = author.get("username", item.get("author_username", "unknown"))
            metrics = item.get("public_metrics", {}) or {}
            score = (
                metrics.get("like_count", 0)
                + metrics.get("retweet_count", 0) * 2
                + metrics.get("reply_count", 0) * 1.5
                + metrics.get("quote_count", 0) * 2
            )
            post_id = str(item.get("id", ""))
            if not post_id or not item.get("text"):
                continue
            posts.append(
                {
                    "id": post_id,
                    "source_type": "x_timeline",
                    "text": item["text"],
                    "created_at": item.get("created_at", ""),
                    "lang": item.get("lang", ""),
                    "author_name": author.get("name", username),
                    "author_username": username,
                    "author_verified": author.get("verified", False),
                    "public_metrics": metrics,
                    "score": score,
                    "url": f"https://x.com/{username}/status/{post_id}",
                }
            )
        posts.sort(key=lambda post: (post["score"], post["created_at"]), reverse=True)
        return posts

    def _clean_handle(self, handle: str) -> str:
        return handle.strip().lstrip("@")
