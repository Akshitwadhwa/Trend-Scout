from pathlib import Path

from app.web_client import WebFeedClient


class SettingsStub:
    web_feed_urls: list[str] = []
    web_keywords: list[str] = []
    max_web_results = 20


class ResponseStub:
    content = b"""<?xml version='1.0'?><rss><channel><item><title>AI tools & models</title><link>https://example.com/?a=1&b=2</link><description>Fresh update</description><pubDate>Fri, 17 Jul 2026 12:00:00 +0000</pubDate></item></channel></rss>"""

    def raise_for_status(self) -> None:
        return None


def test_feed_parser_recovers_common_unescaped_ampersands(monkeypatch):
    client = WebFeedClient(SettingsStub())
    monkeypatch.setattr("app.web_client.requests.get", lambda *_args, **_kwargs: ResponseStub())

    items = client._fetch_feed("https://example.com/feed")

    assert items[0]["title"] == "AI tools & models"
    assert items[0]["url"] == "https://example.com/?a=1&b=2"


def test_missing_or_invalid_feed_dates_are_not_marked_as_now():
    client = WebFeedClient(SettingsStub())

    assert client._parse_date("") == ""
    assert client._parse_date("not-a-date") == ""


def test_fetch_items_filters_broad_feeds_to_requested_keywords(monkeypatch):
    settings = SettingsStub()
    settings.web_feed_urls = ["https://example.com/feed"]
    settings.web_keywords = ["garmin", "whoop"]
    client = WebFeedClient(settings)
    monkeypatch.setattr(
        client,
        "_fetch_feed",
        lambda _url: [
            {"title": "Garmin adds a training feature", "text": "New running data", "created_at": "2026-07-24T10:00:00+00:00"},
            {"title": "Apple Maps update", "text": "Navigation platform news", "created_at": "2026-07-24T11:00:00+00:00"},
        ],
    )

    items = client.fetch_items()

    assert [item["title"] for item in items] == ["Garmin adds a training feature"]


def test_fetch_items_can_use_api_sources_without_rss_feeds(monkeypatch):
    settings = SettingsStub()
    settings.web_api_urls = ["https://api.github.com/repos/openai/openai-python/releases?per_page=10"]
    settings.max_web_results = 5
    client = WebFeedClient(settings)
    monkeypatch.setattr(
        client,
        "_fetch_api",
        lambda _url: [
            {
                "title": "GitHub release: openai/openai-python v1.0.0",
                "text": "New release",
                "created_at": "2026-07-24T12:00:00+00:00",
            }
        ],
    )

    items = client.fetch_items()

    assert len(items) == 1
    assert items[0]["title"].startswith("GitHub release:")
