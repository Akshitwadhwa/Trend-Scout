from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.cloud_inbox import CloudInboxReader
from app.config import load_settings
from app.db import Database


def parse_since(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read the latest GitHub trend inbox and filter already-delivered stories."
    )
    parser.add_argument("--hours", type=int, default=12, help="Maximum story age (default: 12).")
    parser.add_argument(
        "--new-since",
        help="Only return stories published after this ISO-8601 timestamp.",
    )
    parser.add_argument(
        "--mark-delivered",
        nargs="*",
        metavar="SOURCE_KEY",
        help="Mark source keys delivered after Telegram successfully sends them.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    settings = load_settings()
    db = Database(settings.database_path)
    db.init()

    if args.mark_delivered is not None:
        inserted = db.mark_stories_delivered(
            [{"source_key": key} for key in args.mark_delivered]
        )
        print(json.dumps({"marked_delivered": inserted}, ensure_ascii=False))
        return

    since = parse_since(args.new_since) if args.new_since else None
    result = CloudInboxReader(settings).fetch(
        retention_hours=args.hours,
        new_since=since,
        delivered_keys=db.delivered_story_keys(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

