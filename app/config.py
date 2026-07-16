from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _read_csv(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_base_url: str
    database_path: Path
    output_dir: Path
    high_ctr_dir: Path
    json_dir: Path
    enable_scheduler: bool
    check_interval_minutes: int
    max_search_results: int
    max_watchlist_results: int
    max_timeline_results: int
    max_web_results: int
    topic_query: str
    enable_x_scan: bool
    enable_x_watchlist: bool
    enable_x_timeline: bool
    enable_web_scan: bool
    x_watch_handles: list[str]
    web_feed_urls: list[str]
    web_keywords: list[str]
    x_bearer_token: str
    openai_api_key: str
    openai_model: str
    enable_ollama: bool = True
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:1b"
    ollama_timeout_seconds: int = 90
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


def load_settings() -> Settings:
    database_path = Path(
        os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "bot.db"))
    ).expanduser()
    if not database_path.is_absolute():
        database_path = (BASE_DIR / database_path).resolve()

    output_dir = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs"))).expanduser()
    if not output_dir.is_absolute():
        output_dir = (BASE_DIR / output_dir).resolve()

    high_ctr_dir = Path(os.getenv("HIGH_CTR_DIR", str(BASE_DIR / "out"))).expanduser()
    if not high_ctr_dir.is_absolute():
        high_ctr_dir = (BASE_DIR / high_ctr_dir).resolve()

    json_dir = Path(os.getenv("JSON_DIR", str(BASE_DIR / "json"))).expanduser()
    if not json_dir.is_absolute():
        json_dir = (BASE_DIR / json_dir).resolve()

    return Settings(
        app_name=os.getenv("APP_NAME", "X Trend Scout"),
        app_base_url=os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        database_path=database_path,
        output_dir=output_dir,
        high_ctr_dir=high_ctr_dir,
        json_dir=json_dir,
        enable_scheduler=_read_bool("ENABLE_SCHEDULER", True),
        check_interval_minutes=_read_int("CHECK_INTERVAL_MINUTES", 120),
        max_search_results=_read_int("MAX_SEARCH_RESULTS", 20),
        max_watchlist_results=_read_int("MAX_WATCHLIST_RESULTS", 20),
        max_timeline_results=_read_int("MAX_TIMELINE_RESULTS", 30),
        max_web_results=_read_int("MAX_WEB_RESULTS", 30),
        topic_query=os.getenv(
            "TOPIC_QUERY",
            '(claude OR anthropic OR chatgpt OR openai OR codex OR "apple intelligence" '
            'OR "apple ai" OR gemini OR deepmind) lang:en -is:retweet',
        ),
        enable_x_scan=_read_bool("ENABLE_X_SCAN", True),
        enable_x_watchlist=_read_bool("ENABLE_X_WATCHLIST", True),
        enable_x_timeline=_read_bool("ENABLE_X_TIMELINE", False),
        enable_web_scan=_read_bool("ENABLE_WEB_SCAN", True),
        x_watch_handles=_read_csv("X_WATCH_HANDLES"),
        web_feed_urls=_read_csv("WEB_FEED_URLS"),
        web_keywords=_read_csv("WEB_KEYWORDS"),
        x_bearer_token=os.getenv("X_BEARER_TOKEN", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.2").strip(),
        enable_ollama=_read_bool("ENABLE_OLLAMA", True),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "gemma3:1b").strip(),
        ollama_timeout_seconds=_read_int("OLLAMA_TIMEOUT_SECONDS", 90),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    )
