from pathlib import Path


def test_cloud_cycle_keeps_rolling_inbox_memory():
    script = Path(__file__).resolve().parents[1] / "scripts" / "cloud_trend_cycle.py"

    source = script.read_text(encoding="utf-8")

    assert "refresh_trend_inbox(retention_hours=48, replace_existing=False)" in source
    assert "quiet hourly scan must never\n    # erase the previous verified stories" in source
    assert "https://www.apple.com/newsroom/rss-feed.rss" in source
    assert "https://github.blog/feed/" in source
