from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(
        description="Generate high-CTR tweets from pasted text without using X API keys."
    )
    parser.add_argument("--text", help="Tweet, post, article excerpt, or raw idea.")
    parser.add_argument("--file", help="Path to a text file containing the source signal.")
    parser.add_argument("--url", default="", help="Optional source URL.")
    parser.add_argument("--title", default="", help="Optional source title.")
    parser.add_argument(
        "--style",
        default="sharp, practical, high CTR, India-aware, copy-paste ready, no fake hype",
    )
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    source_text = args.text or ""
    if args.file:
        source_text = Path(args.file).read_text(encoding="utf-8")
    if not source_text.strip():
        source_text = sys.stdin.read()
    if not source_text.strip():
        raise SystemExit("Paste text with --text, --file, or stdin.")

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
    result = workflow.optimize_manual_source(
        source_text=source_text,
        source_url=args.url,
        source_title=args.title,
        style=args.style,
        limit=args.limit,
    )

    print("Manual signal pack created")
    print(f"Opportunities: {result['opportunity_count']}")
    print(result["output_files"]["ready_tweets"])
    print(result["output_files"]["x_post_messages"])
    for path in result["output_files"].get("x_post_message_files", []):
        print(path)
    print(result["output_files"]["india_tweets"])


if __name__ == "__main__":
    main()
