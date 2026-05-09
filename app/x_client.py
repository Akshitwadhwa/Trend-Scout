from __future__ import annotations

from typing import Any

import requests

from app.config import Settings


class XClient:
    search_url = "https://api.x.com/2/tweets/search/recent"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

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
