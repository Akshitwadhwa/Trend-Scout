from pathlib import Path

from app.output_writer import OutputWriter


class SettingsStub:
    def __init__(self, root: Path) -> None:
        self.output_dir = root / "outputs"
        self.high_ctr_dir = root / "out"
        self.json_dir = root / "json"


def test_save_ctr_pack_splits_markdown_and_json(tmp_path):
    writer = OutputWriter(SettingsStub(tmp_path))
    result = writer.save_ctr_pack(
        ctr_pack={
            "summary": "summary",
            "items": [
                {
                    "category": "Apple",
                    "title": "Apple Watch health",
                    "best_angle": "Health trust",
                    "best_hook": "Apple Watch is becoming a health trust story.",
                    "hooks": ["Apple Watch is becoming a health trust story."],
                    "post_variants": ["Apple Watch is becoming a health trust story."],
                    "poll": {"question": "Trust Apple Watch health?", "options": ["Yes", "Not yet"]},
                    "reply_post": "The trust layer matters most.",
                    "mini_thread": ["One", "Two", "Three"],
                    "visual_card_idea": "Apple Watch plus trust meter",
                    "why_this_can_work": "Clear topic and debate.",
                    "ctr_score": 90,
                    "impression_score": 85,
                    "reply_score": 80,
                    "risk_score": 10,
                }
            ],
        },
        opportunities=[],
    )

    assert result["markdown"].endswith(".md")
    assert result["json"].endswith(".json")
    assert Path(result["markdown"]).parent.name == "out"
    assert Path(result["json"]).parent.name == "json"
    assert Path(result["markdown"]).exists()
    assert Path(result["json"]).exists()
