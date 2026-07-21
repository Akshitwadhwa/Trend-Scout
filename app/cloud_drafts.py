from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from app.config import Settings


class CloudDraftWriter:
    """Optional cloud draft writer for GitHub Actions; it never posts to X."""

    def __init__(self, settings: Settings) -> None:
        self.enabled = bool(getattr(settings, "enable_openai_drafts", False))
        self.api_key = str(getattr(settings, "openai_api_key", "")).strip()
        self.model = str(getattr(settings, "openai_draft_model", "gpt-5")).strip()

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.api_key)

    def draft(self, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.configured or not topics:
            return []
        source_text = "\n\n".join(
            "\n".join(
                [
                    f"Title: {item.get('title', '')}",
                    f"What happened: {item.get('what_happened', '')}",
                    f"Source: {item.get('source_name', '')}",
                    f"URL: {item.get('source_url', '')}",
                ]
            )
            for item in topics[:5]
        )
        prompt = (
            "Write exactly one original, self-contained X post for each source story below. "
            "Each post must name the company/product, explain what changed in plain English, and give one concrete "
            "developer or everyday-user implication. Keep each post 170-260 characters, casual and human. "
            "Use only supplied facts. No hashtags, emojis, clickbait, fake personal experience, or invented details. "
            "Return JSON only: {\"drafts\":[{\"title\":\"source title\",\"text\":\"tweet\",\"source_url\":\"url\"}]}.\n\n"
            f"Stories:\n{source_text}"
        )
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "input": prompt,
                "store": False,
                "reasoning": {"effort": "low"},
                "text": {"verbosity": "low"},
            },
            timeout=(10, 90),
        )
        response.raise_for_status()
        parsed = self._parse(response.json())
        return [
            item
            for item in parsed
            if item.get("text") and len(str(item["text"])) <= 280
        ][: len(topics)]

    def _parse(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        text = str(payload.get("output_text", "")).strip()
        if not text:
            parts = []
            for item in payload.get("output", []):
                if not isinstance(item, dict) or item.get("type") != "message":
                    continue
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "output_text":
                        parts.append(str(content.get("text", "")))
            text = "\n".join(parts).strip()
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("OpenAI cloud draft writer returned no JSON.")
        payload = json.loads(text[start : end + 1])
        drafts = payload.get("drafts", [])
        return [item for item in drafts if isinstance(item, dict)] if isinstance(drafts, list) else []


class DraftInbox:
    """Keeps a small, reviewable cloud draft history in a JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save_batch(self, drafts: list[dict[str, Any]]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        existing = self._read().get("batches", [])
        batch = {"generated_at": now, "drafts": drafts}
        payload = {"updated_at": now, "batches": [batch, *existing][:24]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return payload

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}
