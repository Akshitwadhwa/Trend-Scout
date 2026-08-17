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
        self.settings = settings
        self.enabled = bool(getattr(settings, "enable_openai_drafts", False))
        self.api_key = str(getattr(settings, "openai_api_key", "")).strip()
        self.model = str(getattr(settings, "openai_draft_model", "gpt-5")).strip()

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.api_key)

    def draft(self, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.configured or not topics:
            return []
        voice_profile = self._voice_profile()
        source_text = "\n\n".join(
            "\n".join(
                [
                    f"Story slot: {index}",
                    f"Title: {item.get('title', '')}",
                    f"What happened: {item.get('what_happened', '')}",
                    f"Source: {item.get('source_name', '')}",
                    f"URL: {item.get('source_url', '')}",
                ]
            )
            for index, item in enumerate(topics[:10], start=1)
        )
        prompt = (
            "Write exactly one original, self-contained X post for each source story below. "
            "This is a real person's account, not a tech-news account. Do not write a mini press release or a generic "
            "explainer. Start with the concrete fact, then add one believable personal take on why it matters, what "
            "feels overrated, or what you would watch next. A cautious or sceptical opinion is better than a forced "
            "positive one. The reader should understand the news even if they missed it.\n\n"
            "Voice rules:\n"
            "- Write as if this was typed quickly after seeing the news: clear, slightly informal, and not overly polished.\n"
            "- Normal lowercase, contractions, short fragments, and one imperfectly natural sentence are fine.\n"
            "- It is fine to say 'i think', 'i'm curious', or 'i don't buy it yet' when it is an opinion, but never invent use of a product or a personal achievement.\n"
            "- Give one thought, not a list, lesson, thread, or conclusion.\n"
            "- Avoid consultant language: 'significant shift', 'represents', 'landscape', 'leverage', 'transformative', 'game changer', 'the key takeaway', 'this shows', and 'not X but Y'.\n"
            "- Avoid emojis, hashtags, semicolons, engagement bait, fake urgency, and sentence templates such as 'the real question is'.\n"
            "- Use only supplied facts; do not make up numbers, capabilities, releases, or personal experience.\n"
            "- Do not make every post the same length or sentence shape. Follow this batch mix: slots 1 and 6 are short (90-140 characters); slots 2, 4, 7 and 9 are normal (150-210 characters); all remaining slots are fuller context (220-275 characters).\n"
            "- Vary the opening across the batch: sometimes lead with the fact, sometimes a plain reaction, a useful contrast, a concrete user impact, or a short question. Do not reuse an opening pattern or the same company as the main subject more than once when other stories are available.\n"
            "- Mix the editorial lens across the batch: global AI, India tech, Cursor/Composer and developer tools, hardware/chips, Tesla/EVs and mobility, robotics, consumer apps, gaming, cybersecurity, startups/business, and practical everyday use. If the source set lacks a category, do not invent one; use the closest available angle and vary the lens.\n"
            "- A longer post must add context that helps a non-expert understand what changed. A short post should still contain a concrete fact, not a vague teaser.\n\n"
            "Creator voice profile (style calibration only; never copy its wording):\n"
            f"{voice_profile}\n\n"
            "Return JSON only: {\"drafts\":[{\"title\":\"source title\",\"text\":\"tweet\",\"source_url\":\"url\",\"category\":\"one short category\",\"length_band\":\"short|normal|full\",\"angle\":\"fact|reaction|contrast|impact|question\"}]}. Preserve story-slot order.\n\n"
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
        return self._diversify(parsed, len(topics))

    def _diversify(self, drafts: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        """Keep malformed, duplicate, and visibly templated batches out of Telegram."""
        selected: list[dict[str, Any]] = []
        seen_text: set[str] = set()
        seen_openings: set[str] = set()
        seen_subjects: set[str] = set()
        for item in drafts:
            text = " ".join(str(item.get("text", "")).split()).strip()
            if not text or len(text) > 280:
                continue
            normalized = text.casefold()
            opening = " ".join(text.casefold().split()[:5])
            title = str(item.get("title", "")).casefold()
            subject = next((word for word in title.split() if len(word) >= 5), "")
            if normalized in seen_text or opening in seen_openings:
                continue
            if subject and subject in seen_subjects and len(drafts) > limit:
                continue
            item = dict(item)
            item["text"] = text
            item.setdefault("length_band", self._length_band(len(text)))
            selected.append(item)
            seen_text.add(normalized)
            seen_openings.add(opening)
            if subject:
                seen_subjects.add(subject)
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _length_band(length: int) -> str:
        if length <= 140:
            return "short"
        if length <= 210:
            return "normal"
        return "full"

    def _voice_profile(self) -> str:
        path = Path(self.settings.database_path).parent / "voice-profile.md"
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            value = ""
        return value[:5_000] or "No custom examples saved yet. Use the voice rules above."

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
