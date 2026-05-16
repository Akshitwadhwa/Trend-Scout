from pathlib import Path

from app.workflow import Workflow


class SettingsStub:
    max_web_results = 50


class XClientShouldNotBeUsed:
    def search_watchlist_posts(self, *args, **kwargs):  # pragma: no cover - should never run
        raise AssertionError("reply-scout must scrape web feeds, not call X API")


class WebClientStub:
    last_errors = []

    def __init__(self):
        self.calls = []

    def fetch_reply_scout_items(self, handles, *, max_results_per_handle):
        self.calls.append((handles, max_results_per_handle))
        return [
            {
                "id": "web-1",
                "source_type": "web_reply_scout",
                "text": "Exact public web scraped post text.",
                "created_at": "2026-05-16T10:00:00+00:00",
                "author_name": "@sama",
                "author_username": "sama",
                "public_metrics": {},
                "score": 100,
                "url": "https://x.com/sama/status/123",
            }
        ]


class OutputWriterStub:
    def save_reply_scout_pack(self, *, reply_pack):
        self.reply_pack = reply_pack
        return {
            "markdown": str(Path("out/reply-scout.md")),
            "copy_paste_replies": str(Path("out/copy-paste-replies.txt")),
            "json": str(Path("json/reply-scout.json")),
        }


def test_reply_scout_uses_web_scraper_not_x_client():
    web_client = WebClientStub()
    output_writer = OutputWriterStub()
    workflow = Workflow(
        settings=SettingsStub(),
        db=None,
        x_client=XClientShouldNotBeUsed(),
        web_client=web_client,
        writer=None,
        output_writer=output_writer,
    )

    result = workflow.reply_scout(handles=["sama"], limit=5)

    assert result["status"] == "ok"
    assert web_client.calls == [(["sama"], 5)]
    assert result["source_count"] == 1
    assert result["web_scrape_errors"] == []
    assert output_writer.reply_pack["items"][0]["source_tweet"]["text"] == "Exact public web scraped post text."
