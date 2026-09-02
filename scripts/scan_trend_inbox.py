from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import load_settings
from scripts.fresh import build_workflow, settings_for_mode


def main() -> None:
    parser = argparse.ArgumentParser(description="Save a source-backed local tech trend inbox.")
    parser.add_argument("--retention-hours", type=int, default=12)
    parser.add_argument(
        "--with-openai",
        action="store_true",
        help="Use the optional paid OpenAI web-research step for this scan.",
    )
    args = parser.parse_args()

    load_dotenv()
    mode = argparse.Namespace(mode="ai-radar", limit=5, handles="", style="")
    settings = settings_for_mode(load_settings(), mode)
    if not args.with_openai:
        settings = replace(settings, enable_openai_research=False)

    result = build_workflow(settings).refresh_trend_inbox(
        retention_hours=args.retention_hours,
    )
    print("Trend inbox updated")
    print(f"New distinct sources: {result['discovered_count']}")
    print(f"OpenAI web-researched sources: {result['cloud_source_count']}")
    print(f"Saved post-ready topics: {result['inbox_count']}")
    print(result["inbox_path"])
    if result["web_feed_errors"]:
        print("Feed warnings:")
        for error in result["web_feed_errors"]:
            print(f"- {error}")


if __name__ == "__main__":
    main()
