from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.ai_writer import TrendWriter
from app.config import load_settings
from app.db import Database
from app.output_writer import OutputWriter
from app.web_client import WebFeedClient
from app.workflow import Workflow
from app.x_client import XClient


def main() -> None:
    load_dotenv()
    settings = load_settings()
    db = Database(settings.database_path)
    db.init()
    workflow = Workflow(
        settings=settings,
        db=db,
        x_client=XClient(settings),
        web_client=WebFeedClient(settings),
        writer=TrendWriter(settings),
        output_writer=OutputWriter(settings),
    )
    result = workflow.fresh_optimize(
        style="sharp, practical, high CTR, high reply potential, no fake hype",
        limit=10,
    )
    scan = result.get("scan", {})
    created_count = scan.get("created_count", 0)
    source_count = scan.get("source_count", 0)
    x_watchlist_count = scan.get("x_watchlist_source_count", 0)
    x_errors = scan.get("x_scan_errors", [])
    errors = scan.get("web_feed_errors", [])

    print("Fresh high-CTR pack created")
    print(f"Sources found: {source_count}")
    print(f"Tracked-account posts: {x_watchlist_count}")
    print(f"New opportunities: {created_count}")
    if x_errors:
        print("X warnings:")
        for error in x_errors:
            print(f"- {error}")
    if errors:
        print("Feed warnings:")
        for error in errors:
            print(f"- {error}")
    print(result["output_files"]["markdown"])
    if result["output_files"].get("ready_tweets"):
        print(result["output_files"]["ready_tweets"])
    if created_count == 0:
        print("No post-ready topics were found. Check feed/network access or broaden WEB_KEYWORDS.")


if __name__ == "__main__":
    main()
