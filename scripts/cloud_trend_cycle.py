from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.cloud_drafts import CloudDraftWriter, DraftInbox
from app.config import load_settings
from app.telegram_client import TelegramClient
from scripts.fresh import build_workflow, settings_for_mode


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    mode = type("Args", (), {"mode": "ai-radar", "limit": 5, "handles": "", "style": ""})()
    settings = settings_for_mode(load_settings(), mode)
    settings = replace(settings, enable_ollama=False, enable_openai_research=bool(settings.openai_api_key))
    workflow = build_workflow(settings)
    scan = workflow.refresh_trend_inbox(retention_hours=48)
    inbox_path = settings.database_path.parent / "trend-inbox.json"
    inbox = json.loads(inbox_path.read_text(encoding="utf-8")) if inbox_path.exists() else {"items": []}
    drafts = CloudDraftWriter(settings).draft(inbox.get("items", []))
    DraftInbox(settings.database_path.parent / "draft-inbox.json").save_batch(drafts)

    telegram = TelegramClient(settings)
    if telegram.configured and drafts:
        message = "Latest Trend Scout drafts — review before posting:\n\n" + "\n\n---\n\n".join(
            str(item.get("text", "")) for item in drafts
        )
        telegram.send_messages([message[:4096]])

    print(json.dumps({
        "saved_topics": scan["inbox_count"],
        "cloud_sources": scan["cloud_source_count"],
        "drafts": len(drafts),
        "telegram_sent": bool(telegram.configured and drafts),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
