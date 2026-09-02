"""On-demand, free-source wearable-tech scan for Telegram and Post Lab."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import load_settings
from scripts.fresh import build_workflow, settings_for_mode


CACHE_META = ROOT_DIR / "data" / "wearables-cache-meta.json"


def cache_is_fresh(max_age_minutes: int) -> bool:
    try:
        payload = json.loads(CACHE_META.read_text(encoding="utf-8"))
        if payload.get("profile") != "wearables-v1":
            return False
        updated = datetime.fromisoformat(str(payload["updated_at"]).replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return updated >= datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    except (KeyError, OSError, ValueError):
        return False


def write_cache_meta() -> None:
    CACHE_META.write_text(
        json.dumps({"profile": "wearables-v1", "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Ignore the short-lived local wearable cache")
    parser.add_argument("--max-age-minutes", type=int, default=360)
    args = parser.parse_args()
    load_dotenv(ROOT_DIR / ".env")
    max_age_minutes = max(1, min(args.max_age_minutes, 1_440))
    inbox_path = ROOT_DIR / "data" / "wearables-inbox.json"
    if not args.refresh and inbox_path.exists() and cache_is_fresh(max_age_minutes):
        payload = json.loads(inbox_path.read_text(encoding="utf-8"))
        print(json.dumps({
            "mode": "wearables",
            "cache": "hit",
            "saved_topics": len(payload.get("items", [])),
            "inbox_path": str(inbox_path),
        }, ensure_ascii=False))
        return
    mode = type("Args", (), {"mode": "wearables", "limit": 8, "handles": "", "style": ""})()
    settings = settings_for_mode(load_settings(), mode)
    settings = replace(
        settings,
        enable_ollama=False,
        enable_openai_research=False,
        enable_openai_drafts=False,
    )
    result = build_workflow(settings).refresh_trend_inbox(
        retention_hours=12,
        inbox_filename="wearables-inbox.json",
        replace_existing=True,
    )
    write_cache_meta()
    print(json.dumps({
        "mode": "wearables",
        "cache": "refreshed",
        "saved_topics": result["inbox_count"],
        "free_sources": result["discovered_count"],
        "inbox_path": result["inbox_path"],
        "warnings": result.get("web_feed_errors", [])[:5],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
