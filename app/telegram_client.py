from __future__ import annotations

from typing import Any

import requests

from app.config import Settings


class TelegramClient:
    """Optional, manual-only delivery of approved draft text to Telegram."""

    def __init__(self, settings: Settings) -> None:
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id

    @property
    def configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_messages(self, messages: list[str]) -> list[dict[str, Any]]:
        if not self.configured:
            raise RuntimeError(
                "Telegram is not configured. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env."
            )

        sent: list[dict[str, Any]] = []
        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        for text in messages:
            clean = text.strip()
            if not clean:
                continue
            if len(clean) > 4096:
                raise ValueError("Each Telegram message must be 4,096 characters or shorter.")
            response = requests.post(
                endpoint,
                json={"chat_id": self.chat_id, "text": clean},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok"):
                raise RuntimeError(str(payload.get("description", "Telegram rejected the message.")))
            sent.append(payload.get("result", {}))
        return sent
