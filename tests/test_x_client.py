from typing import Any, cast
from types import SimpleNamespace

from app.x_client import XClient


def test_xurl_timeline_payload_becomes_source_items():
    client = XClient(cast(Any, SimpleNamespace(x_bearer_token="")))

    posts = client._posts_from_xurl_payload(
        {
            "data": [
                {
                    "id": "123",
                    "text": "AI agents are moving from demos to boring daily workflows.",
                    "author_id": "u1",
                    "created_at": "2026-05-15T10:00:00Z",
                    "lang": "en",
                    "public_metrics": {
                        "like_count": 10,
                        "retweet_count": 2,
                        "reply_count": 4,
                        "quote_count": 1,
                    },
                }
            ],
            "includes": {
                "users": [
                    {
                        "id": "u1",
                        "name": "Builder",
                        "username": "builder",
                        "verified": True,
                    }
                ]
            },
        }
    )

    assert posts == [
        {
            "id": "123",
            "source_type": "x_timeline",
            "text": "AI agents are moving from demos to boring daily workflows.",
            "created_at": "2026-05-15T10:00:00Z",
            "lang": "en",
            "author_name": "Builder",
            "author_username": "builder",
            "author_verified": True,
            "public_metrics": {
                "like_count": 10,
                "retweet_count": 2,
                "reply_count": 4,
                "quote_count": 1,
            },
            "score": 22.0,
            "url": "https://x.com/builder/status/123",
        }
    ]
