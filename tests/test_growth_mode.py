import argparse
from pathlib import Path

from app.config import Settings
from scripts.fresh import DEFAULT_STYLES, parse_args, settings_for_mode


def settings_stub() -> Settings:
    return Settings(
        app_name="test",
        app_base_url="http://localhost",
        database_path=Path("bot.db"),
        output_dir=Path("outputs"),
        high_ctr_dir=Path("out"),
        json_dir=Path("json"),
        enable_scheduler=False,
        check_interval_minutes=120,
        max_search_results=20,
        max_watchlist_results=20,
        max_timeline_results=30,
        max_web_results=30,
        topic_query="default",
        enable_x_scan=True,
        enable_x_watchlist=True,
        enable_x_timeline=True,
        enable_web_scan=False,
        x_watch_handles=[],
        web_feed_urls=[],
        web_keywords=[],
        x_bearer_token="",
        openai_api_key="",
        openai_model="test-model",
    )


def test_growth_mode_is_available_in_cli(monkeypatch):
    monkeypatch.setattr("sys.argv", ["fresh.py", "growth", "--limit", "3"])

    args = parse_args()

    assert args.mode == "growth"
    assert args.limit == 3
    assert "follower growth" in DEFAULT_STYLES["growth"]


def test_growth_mode_uses_web_scan_not_x_api():
    args = argparse.Namespace(mode="growth", limit=10, handles="", style="")

    settings = settings_for_mode(settings_stub(), args)

    assert settings.enable_web_scan is True
    assert settings.enable_x_scan is False
    assert settings.enable_x_watchlist is False
    assert settings.enable_x_timeline is False
    assert "developers" in settings.topic_query
