from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import load_settings
from scripts.fresh import build_workflow, settings_for_mode


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    mode = type("Args", (), {"mode": "ai-radar", "limit": 5, "handles": "", "style": ""})()
    settings = settings_for_mode(load_settings(), mode)
    # This cloud job is deliberately collection-only. It must never spend on
    # a cloud LLM or rely on the laptop's local Ollama server.
    settings = replace(settings, enable_ollama=False, enable_openai_research=False)
    workflow = build_workflow(settings)
    scan = workflow.refresh_trend_inbox(retention_hours=48)

    print(json.dumps({
        "saved_topics": scan["inbox_count"],
        "cloud_sources": scan["cloud_source_count"],
        "drafts": 0,
        "telegram_sent": False,
        "mode": "free_source_collection",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
