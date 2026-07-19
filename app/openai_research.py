from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import requests

from app.config import Settings


class OpenAIWebResearcher:
    """Optional current-web research. Disabled unless the user opts in locally."""

    def __init__(self, settings: Settings) -> None:
        self.enabled = bool(getattr(settings, "enable_openai_research", False))
        self.api_key = str(getattr(settings, "openai_api_key", "")).strip()
        self.model = str(getattr(settings, "openai_research_model", "gpt-5")).strip()
        self.timeout = int(getattr(settings, "openai_research_timeout_seconds", 120))
        self.last_error = ""

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.api_key)

    def research(self, topic_query: str) -> list[dict[str, Any]]:
        self.last_error = ""
        if not self.configured:
            return []
        today = datetime.now(timezone.utc).date().isoformat()
        prompt = (
            "Research the newest important technology developments from the past 48 hours. "
            "Focus on releases and updates from OpenAI, Anthropic, Google DeepMind/Gemini, Meta AI/Llama, "
            "xAI/Grok, Kimi/Moonshot, DeepSeek, Qwen/Alibaba, Mistral, Hugging Face, plus developer tools, chips, consumer devices, startups, and tech policy. "
            "and India-relevant technology when there is a real connection. Prefer the original company newsroom, "
            "research lab, regulator, or product release page over reporting. Do not include rumours. "
            "Every item needs one direct source URL and an explicit publication date. "
            "Return JSON only with this shape: "
            '{"items":[{"title":"...","what_happened":"...","why_it_matters":"...",'
            '"published_at":"YYYY-MM-DD","source_name":"...","source_url":"https://...",'
            '"category":"AI|Developer tools|Chips|Consumer tech|Startups|Policy","confidence":0.0}]}. '
            f"Today is {today}. Topic focus: {topic_query}"
        )
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "tools": [{"type": "web_search"}],
                    "input": prompt,
                    "store": False,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            return self._items_from_response(payload)
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            self.last_error = str(exc)
            return []

    def _items_from_response(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        text = str(payload.get("output_text", "")).strip()
        if not text:
            raise RuntimeError("OpenAI web research returned no text.")
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("OpenAI web research did not return JSON.")
        parsed = json.loads(text[start : end + 1])
        items = parsed.get("items", [])
        if not isinstance(items, list):
            raise RuntimeError("OpenAI web research JSON has no items list.")
        return [item for item in items[:8] if isinstance(item, dict) and item.get("source_url") and item.get("title")]
