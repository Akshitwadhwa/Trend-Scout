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
                    "best_ready_to_post": "Apple Watch is becoming less of a gadget and more of a trust layer for health.",
                    "format_comparison": [
                        {
                            "format": "contrarian",
                            "score": 94,
                            "tweet": "Apple Watch is becoming less of a gadget and more of a trust layer for health.",
                            "why_it_works": "It reframes the product.",
                        }
                    ],
                    "ready_to_post_tweets": [
                        {
                            "rank": 1,
                            "format": "contrarian",
                            "score": 94,
                            "tweet": "Apple Watch is becoming less of a gadget and more of a trust layer for health.",
                            "why_it_works": "It is complete and copy-paste ready.",
                        }
                    ],
                    "india_angle": "Apple Watch health features matter for Indian premium wearable buyers.",
                    "india_relevance_score": 88,
                    "india_long_tweets": [
                        {
                            "rank": 1,
                            "tweet": "For India, Apple Watch is not just a premium gadget story anymore. If health tracking keeps getting better, the real debate becomes whether Indian buyers see it as a phone accessory or a serious preventive-health device.",
                            "why_it_works": "It localizes the topic for Indian buyers.",
                        }
                    ],
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
    assert result["ready_tweets"].endswith(".md")
    assert result["india_tweets"].endswith(".md")
    assert result["json"].endswith(".json")
    assert Path(result["markdown"]).parent.name == "out"
    assert Path(result["ready_tweets"]).parent.name == "out"
    assert Path(result["india_tweets"]).parent.name == "out"
    assert Path(result["json"]).parent.name == "json"
    assert Path(result["markdown"]).exists()
    assert Path(result["ready_tweets"]).exists()
    assert Path(result["india_tweets"]).exists()
    assert Path(result["json"]).exists()
    assert "Copy-Paste Ready Tweets" in Path(result["ready_tweets"]).read_text(encoding="utf-8")
    assert "India Tech Tweets" in Path(result["india_tweets"]).read_text(encoding="utf-8")


def test_clear_generated_files_keeps_gitkeep(tmp_path):
    writer = OutputWriter(SettingsStub(tmp_path))
    for folder, suffix in [
        (writer.output_dir, ".md"),
        (writer.high_ctr_dir, ".md"),
        (writer.json_dir, ".json"),
    ]:
        (folder / ".gitkeep").write_text("", encoding="utf-8")
        (folder / f"old{suffix}").write_text("old", encoding="utf-8")

    result = writer.clear_generated_files()

    assert result == {"outputs": 1, "out": 1, "json": 1}
    assert (writer.output_dir / ".gitkeep").exists()
    assert not (writer.output_dir / "old.md").exists()
