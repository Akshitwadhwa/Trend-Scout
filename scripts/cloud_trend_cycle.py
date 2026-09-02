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


# The cloud inbox is intentionally broad. Focused modes such as ai-radar,
# wearables, or NVIDIA are run only when the creator explicitly asks for them.
# Separate Google News queries make the free hourly scan less likely to become
# an AI-only feed when one topic dominates the news cycle. The wider mix also
# covers technology that reaches people outside developer tooling: mobility,
# robotics, energy, gaming, security, and India-specific launches.
CLOUD_MIXED_FEEDS = [
    "https://news.google.com/rss/search?q=site%3Aopenai.com%20OR%20site%3Aanthropic.com%20OR%20site%3Adeepmind.google%20AI%20model%20when:12h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=OpenAI%20OR%20Anthropic%20OR%20Gemini%20OR%20AI%20model%20when:3d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=NVIDIA%20OR%20AMD%20OR%20GPU%20OR%20semiconductor%20OR%20chip%20when:3d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Apple%20OR%20Samsung%20OR%20smartphone%20OR%20wearable%20OR%20consumer%20tech%20when:3d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Apple%20iPhone%20OR%20iPad%20OR%20Mac%20OR%20Apple%20Watch%20OR%20Vision%20Pro%20launch%20when:12h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=developer%20tools%20OR%20GitHub%20OR%20software%20release%20OR%20cybersecurity%20when:3d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Cursor%20AI%20OR%20Cursor%20Composer%20OR%20coding%20agents%20when:3d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Tesla%20OR%20EV%20OR%20robotaxi%20OR%20electric%20vehicle%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=robotics%20OR%20drones%20OR%20automation%20OR%20industrial%20robots%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=India%20tech%20startup%20UPI%20digital%20public%20infrastructure%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=gaming%20console%20PlayStation%20Xbox%20Nintendo%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=cybersecurity%20privacy%20data%20breach%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://ir.tesla.com/rss/news-releases.xml",
    "https://news.google.com/rss/search?q=tech%20startup%20OR%20funding%20OR%20antitrust%20OR%20technology%20regulation%20when:3d&hl=en-IN&gl=IN&ceid=IN:en",
    # Official sources make the free inbox more useful on quiet news days.
    "https://www.apple.com/newsroom/rss-feed.rss",
    "https://news.samsung.com/global/feed",
    "https://newsroom.intel.com/feed/",
    "https://blogs.microsoft.com/feed/",
    "https://github.blog/feed/",
    "https://about.fb.com/feed/",
]
CLOUD_API_URLS = [
    # Public release metadata from projects people actually use.
    "https://api.github.com/repos/openai/openai-python/releases?per_page=10",
    "https://api.github.com/repos/anthropics/claude-code/releases?per_page=10",
    "https://api.github.com/repos/googleapis/python-genai/releases?per_page=10",
    "https://api.github.com/repos/huggingface/transformers/releases?per_page=10",
    "https://api.github.com/repos/ollama/ollama/releases?per_page=10",
    # Recently modified public models, plus discussion signals from Reddit.
    "https://huggingface.co/api/models?sort=lastModified&direction=-1&limit=40&filter=text-generation",
    "https://www.reddit.com/r/artificial/new.json?limit=25",
    "https://www.reddit.com/r/MachineLearning/new.json?limit=25",
    "https://www.reddit.com/r/hardware/new.json?limit=25",
    "https://www.reddit.com/r/technology/new.json?limit=25",
]
CLOUD_MIXED_KEYWORDS = [
    # Avoid the bare word "chip": Google News also returns food stories such
    # as potato chips. Keep the hardware terms specific enough for the inbox.
    "openai", "anthropic", "gemini", "ai model", "nvidia", "amd", "gpu", "ai chip", "semiconductor",
    "apple", "samsung", "smartphone", "wearable", "consumer tech", "developer tools", "github", "cursor", "composer",
    "software", "cybersecurity", "privacy", "data breach", "startup", "funding", "antitrust", "regulation",
    "tesla", "ev", "electric vehicle", "robotaxi", "charging", "battery", "robotics", "drones", "automation",
    "india tech", "upi", "digital public infrastructure", "gaming", "playstation", "xbox", "nintendo",
    "hugging face", "transformers", "ollama", "claude code", "python genai", "machine learning",
]


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    mode = type("Args", (), {"mode": "fresh", "limit": 12, "handles": "", "style": ""})()
    settings = settings_for_mode(load_settings(), mode)
    # This cloud job is deliberately collection-only. It must never spend on
    # a cloud LLM or rely on the laptop's local Ollama server.
    settings = replace(
        settings,
        topic_query="mixed current technology news",
        enable_ollama=False,
        enable_openai_research=False,
        enable_openai_drafts=False,
        enable_x_scan=False,
        enable_x_watchlist=False,
        enable_x_timeline=False,
        enable_web_scan=True,
        max_web_results=max(100, settings.max_web_results),
        web_feed_urls=CLOUD_MIXED_FEEDS,
        web_api_urls=CLOUD_API_URLS,
        web_keywords=CLOUD_MIXED_KEYWORDS,
    )
    workflow = build_workflow(settings)
    # The SQLite topic value can outlive a previous focused local run. The
    # scheduled cloud job must always use its own broad topic configuration.
    workflow.db.set_topic_query(settings.topic_query)
    # Replace the inbox on every run. Telegram must never draft from a story
    # that was left behind by a failed/stopped scheduler run. If this scan
    # finds no verified stories, an empty inbox is safer than stale content.
    scan = workflow.refresh_trend_inbox(retention_hours=12, replace_existing=True)

    print(json.dumps({
        "saved_topics": scan["inbox_count"],
        "discovered_topics": scan["discovered_count"],
        "cloud_sources": scan["cloud_source_count"],
        "web_feed_errors": scan["web_feed_errors"],
        "source_levels": scan["verified_brief"].get("source_counts", {}),
        "drafts": 0,
        "telegram_sent": False,
        "mode": "free_source_collection",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
