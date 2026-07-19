from pathlib import Path

from app.web_client import WebFeedClient


class SettingsStub:
    web_feed_urls: list[str] = []
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
