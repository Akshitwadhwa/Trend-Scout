from pathlib import Path


def test_cloud_cycle_keeps_rolling_inbox_memory():
    script = Path(__file__).resolve().parents[1] / "scripts" / "cloud_trend_cycle.py"

    source = script.read_text(encoding="utf-8")

    assert "verified_max_age_hours=72" in source
    assert "refresh_trend_inbox(retention_hours=72, replace_existing=True)" in source
    assert "https://www.apple.com/newsroom/rss-feed.rss" in source
    assert "https://github.blog/feed/" in source
    assert "https://api.github.com/repos/openai/openai-python/releases" in source
    assert "https://huggingface.co/api/models" in source
    assert "https://www.reddit.com/r/artificial/new.json" in source
