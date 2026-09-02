from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import load_settings
from scripts.fresh import build_workflow

load_dotenv(ROOT_DIR / ".env")

feeds = [
    "https://news.google.com/rss/search?q=OpenAI%20Codex%20OR%20ChatGPT%20agents%20OR%20AI%20agents%20when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=OpenAI%20product%20updates%20OR%20Codex%20developer%20tools%20OR%20coding%20agents%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=thsottiaux%20OR%20sama%20OpenAI%20Codex%20AI%20agents%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Anthropic%20Claude%20agents%20developer%20tools%20model%20release%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Google%20DeepMind%20Gemini%20AI%20model%20release%20developer%20tools%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Nvidia%20AI%20chips%20cloud%20inference%20AI%20infrastructure%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=AI%20startups%20funding%20India%20developers%20founders%20students%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
]

settings = load_settings()
settings = replace(
    settings,
    topic_query=(
        'OpenAI Codex ChatGPT AI agents coding agents developer tools Anthropic Claude '
        'Google DeepMind Gemini Nvidia AI chips cloud model releases AI infra India developers founders students'
    ),
    enable_web_scan=True,
    enable_x_scan=False,
    enable_x_watchlist=False,
    enable_x_timeline=False,
    max_web_results=80,
    verified_max_age_hours=12,
    web_feed_urls=feeds,
    web_keywords=[
        "OpenAI", "Codex", "ChatGPT", "agent", "AI agents", "coding agent", "developer tools",
        "sama", "thsottiaux", "Anthropic", "Claude", "Google DeepMind", "Gemini", "Nvidia",
        "chips", "cloud", "model release", "AI infrastructure", "India", "developers", "founders", "students",
    ],
)
workflow = build_workflow(settings)
style = (
    "factual, statement-led, concrete, high CTR, high impressions, OpenAI/Codex/devtools aware, all important AI updates, "
    "use thsottiaux and sama as OpenAI/Codex signal sources when relevant, useful for Indian founders/developers/"
    "creators/students, practical implications, no hype, no generic takes"
)
result = workflow.fresh_optimize(style=style, limit=10)
texts = result.get("output_files", {}).get("x_post_message_texts", [])[:6]
summary = {
    "status": result.get("status"),
    "scan": result.get("scan", {}),
    "tweet_texts": texts,
    "tweet_count": len(texts),
    "output_files": result.get("output_files", {}),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
