from datetime import datetime, timedelta, timezone

from app.trend_inbox import TrendInbox


def item(title: str, published_at: str, source_level: str = "primary") -> dict:
    return {
        "title": title,
        "published_at": published_at,
        "source_level": source_level,
        "source_name": "OpenAI",
        "source_url": "https://openai.com/news/example",
        "what_happened": "A release happened.",
    }


def test_inbox_keeps_only_recent_post_ready_items(tmp_path):
    now = datetime.now(timezone.utc)
    inbox = TrendInbox(tmp_path / "trend-inbox.json", retention_hours=48)

    saved = inbox.merge(
        {
            "items": [
                item("Fresh release", now.isoformat()),
                item("Old release", (now - timedelta(hours=50)).isoformat()),
                item("Unverified release", now.isoformat(), "discovery"),
            ]
        }
    )

    assert [entry["title"] for entry in saved["items"]] == ["Fresh release"]
