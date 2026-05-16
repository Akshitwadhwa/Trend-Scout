from pathlib import Path

from app.output_writer import OutputWriter


class SettingsStub:
    def __init__(self, root: Path) -> None:
        self.output_dir = root / "outputs"
        self.high_ctr_dir = root / "out"
        self.json_dir = root / "json"


def test_save_reply_scout_pack_writes_exact_source_and_copy_paste_replies(tmp_path):
    writer = OutputWriter(SettingsStub(tmp_path))
    exact_source = "We are launching a new model today. It is faster and cheaper for developers."
    result = writer.save_reply_scout_pack(
        reply_pack={
            "summary": "summary",
            "items": [
                {
                    "rank": 1,
                    "engagement_score": 15350,
                    "source_tweet": {
                        "id": "123",
                        "author_name": "Sam Altman",
                        "author_username": "sama",
                        "text": exact_source,
                        "url": "https://x.com/sama/status/123",
                        "created_at": "2026-05-16T10:00:00Z",
                        "public_metrics": {"like_count": 10000},
                    },
                    "reply_options": [
                        {"rank": 1, "format": "useful_addition", "text": "Useful reply", "why_it_can_work": "Adds value."}
                    ],
                    "quote_post_options": [
                        {"rank": 1, "format": "contrarian", "text": "Useful quote", "why_it_can_work": "Adds view."}
                    ],
                    "repost_note": "Use repost button.",
                }
            ],
        }
    )

    assert result["markdown"].endswith("-reply-scout.md")
    assert result["copy_paste_replies"].endswith("-copy-paste-replies.txt")
    assert result["json"].endswith("-reply-scout.json")
    markdown = Path(result["markdown"]).read_text(encoding="utf-8")
    replies = Path(result["copy_paste_replies"]).read_text(encoding="utf-8")
    assert exact_source in markdown
    assert "https://x.com/sama/status/123" in markdown
    assert replies == "Useful reply\n"
