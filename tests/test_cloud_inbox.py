from datetime import datetime, timedelta, timezone

from app.cloud_inbox import CloudInboxReader
from app.db import Database


class SettingsStub:
    cloud_inbox_url = "https://raw.example.test/trend-inbox.json"
    cloud_inbox_timeout_seconds = 15


class ResponseStub:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def story(title, published_at, *, level="primary", url=None):
    return {
        "title": title,
        "published_at": published_at,
        "source_level": level,
        "source_name": "OpenAI",
        "source_url": url or f"https://openai.com/{title.lower().replace(' ', '-')}",
        "what_happened": "A source-backed update.",
    }


def test_cloud_reader_filters_old_undated_unverified_and_delivered(monkeypatch):
    now = datetime.now(timezone.utc)
    payload = {
        "updated_at": now.isoformat(),
        "scanned_at": now.isoformat(),
        "items": [
            story("Fresh release", (now - timedelta(hours=2)).isoformat()),
            story("Old release", (now - timedelta(hours=13)).isoformat()),
            story("Undated release", ""),
            story("Unverified release", now.isoformat(), level="discovery"),
        ],
    }
    monkeypatch.setattr(
        "app.cloud_inbox.requests.get",
        lambda *args, **kwargs: ResponseStub(payload),
    )

    result = CloudInboxReader(SettingsStub()).fetch(
        retention_hours=12,
        delivered_keys={CloudInboxReader.source_key(payload["items"][0]["source_url"], "Fresh release")},
    )

    assert result["items"] == []
    assert result["rejected"]["old"] == 1
    assert result["rejected"]["missing_date"] == 1
    assert result["rejected"]["unverified"] == 1
    assert result["rejected"]["delivered"] == 1


def test_database_persists_delivered_story_keys(tmp_path):
    db = Database(tmp_path / "bot.db")
    db.init()

    assert db.mark_stories_delivered([
        {"source_key": "abc", "title": "Fresh", "source_url": "https://example.test/fresh"},
        {"source_key": "abc", "title": "Fresh", "source_url": "https://example.test/fresh"},
    ]) == 1
    assert db.delivered_story_keys() == {"abc"}


def test_cloud_reader_supports_new_since_timestamp(monkeypatch):
    now = datetime.now(timezone.utc)
    payload = {
        "updated_at": now.isoformat(),
        "items": [
            story("Older fresh story", (now - timedelta(hours=3)).isoformat()),
            story("Newer fresh story", (now - timedelta(minutes=20)).isoformat()),
        ],
    }
    monkeypatch.setattr(
        "app.cloud_inbox.requests.get",
        lambda *args, **kwargs: ResponseStub(payload),
    )

    result = CloudInboxReader(SettingsStub()).fetch(
        retention_hours=12,
        new_since=now - timedelta(hours=1),
    )

    assert [item["title"] for item in result["items"]] == ["Newer fresh story"]
