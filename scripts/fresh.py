from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.ai_writer import TrendWriter
from app.config import load_settings
from app.db import Database
from app.output_writer import OutputWriter
from app.reply_scout import DEFAULT_REPLY_SCOUT_HANDLES
from app.web_client import WebFeedClient
from app.workflow import Workflow
from app.x_client import XClient


TOP_AI_ACCOUNT_HANDLES = [
    "karpathy",
    "sama",
    "AndrewYNg",
    "fchollet",
    "ylecun",
    "demishassabis",
    "OpenAI",
    "thsottiaux",
    "AnthropicAI",
    "GoogleDeepMind",
    "perplexity_ai",
    "lmarena_ai",
    "huggingface",
    "emollick",
    "simonw",
    "goodside",
    "lilianweng",
    "_akhaliq",
    "dair_ai",
    "rasbt",
    "jeremyphoward",
    "ID_AA_Carmack",
    "hardmaru",
    "bindureddy",
]

NVIDIA_FEEDS = [
    "https://news.google.com/rss/search?q=NVIDIA%20GTC%20Taipei%202026%20OR%20Computex%202026%20Jensen%20Huang%20when:7d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=NVIDIA%20RTX%20Spark%20AI%20PCs%20Windows%20laptops%20when:7d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=NVIDIA%20Vera%20CPU%20agents%20Vera%20Rubin%20AI%20factory%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=NVIDIA%20Rubin%20Blackwell%20NVL72%20NVLink%20Spectrum%20AI%20infrastructure%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=NVIDIA%20Microsoft%20AI%20PC%20N1X%20Arm%20CPU%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=NVIDIA%20AI%20chips%20data%20center%20inference%20GPU%20CUDA%20when:7d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://nvidianews.nvidia.com/news.xml",
    "https://blogs.nvidia.com/feed/",
]

NVIDIA_KEYWORDS = [
    "nvidia",
    "jensen huang",
    "gtc taipei",
    "computex",
    "rtx spark",
    "ai pc",
    "n1x",
    "vera",
    "rubin",
    "vera rubin",
    "blackwell",
    "nvlink",
    "spectrum",
    "dgx",
    "cuda",
    "gpu",
    "ai chips",
    "ai factory",
    "data center",
    "inference",
    "superchip",
    "windows laptops",
]

TESLA_FEEDS = [
    "https://news.google.com/rss/search?q=Tesla%20latest%20news%20EV%20deliveries%20earnings%20when:7d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Tesla%20FSD%20robotaxi%20autonomous%20driving%20when:7d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Tesla%20Optimus%20robot%20AI%20manufacturing%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Tesla%20India%20launch%20factory%20showroom%20EV%20when:30d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Tesla%20Model%20Y%20Model%203%20Cybertruck%20price%20demand%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Tesla%20Supercharger%20charging%20energy%20Megapack%20battery%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://ir.tesla.com/rss/news-releases.xml",
]

TESLA_KEYWORDS = [
    "tesla",
    "elon musk",
    "model y",
    "model 3",
    "cybertruck",
    "fsd",
    "full self-driving",
    "robotaxi",
    "autonomous driving",
    "optimus",
    "humanoid robot",
    "supercharger",
    "charging",
    "megapack",
    "powerwall",
    "battery",
    "ev",
    "electric vehicle",
    "deliveries",
    "earnings",
    "tesla india",
    "gigafactory",
]


DEFAULT_STYLES = {
    "fresh": "factual, statement-led, concrete, high CTR, no hype",
    "top-ai": (
        "factual, statement-led, concrete, high CTR, no hype, based on signals from top AI accounts, "
        "do not copy their wording, turn each signal into an original factual X post"
    ),
    "india": (
        "factual, statement-led, high CTR, India-aware, latest India angle, useful for Indian tech audience, "
        "buyers, founders, creators, developers, students, pricing, jobs, regulation where relevant, no hype"
    ),
    "growth": (
        "factual, statement-led, high CTR, high impressions, follower growth, X algorithm aware, "
        "optimize for saves/bookmarks, profile clicks, follows, Indian developers/founders/students, "
        "use OpenAI Codex/devtools update signals including thsottiaux when relevant, no hype"
    ),
    "nvidia": (
        "factual, statement-led, high CTR, NVIDIA event aware, explain concrete facts and implications for AI PCs, chips, "
        "AI factories, cloud costs, Indian developers/founders/students, infrastructure, no hype"
    ),
    "tesla": (
        "factual, statement-led, high CTR, Tesla-aware, explain concrete facts and implications for EVs, "
        "FSD/robotaxi, Optimus, energy storage, charging, India buyers, auto market, no hype"
    ),
    "reply-scout": (
        "scrape high-signal public web account feeds and produce exact source posts plus copy-paste replies/quotes; "
        "manual repost/reply workflow, no auto-posting"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate X Trend Scout high-CTR posts."
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["fresh", "top-ai", "india", "growth", "nvidia", "tesla", "reply-scout"],
        default="fresh",
        help="fresh=normal scan, top-ai=signals from top AI accounts, india=latest India-aware tech posts, growth=X-algorithm-aware impression/CTR/follower-growth pack, nvidia=NVIDIA event/chips/AI factory scan, tesla=Tesla EV/FSD/Optimus/energy scan, reply-scout=high-signal source tweets plus copy-paste replies",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--style", default="")
    parser.add_argument(
        "--handles",
        default="",
        help="Comma-separated handles for top-ai or reply-scout mode. Defaults to each mode's curated account list.",
    )
    return parser.parse_args()


def build_workflow(settings) -> Workflow:
    db = Database(settings.database_path)
    db.init()
    return Workflow(
        settings=settings,
        db=db,
        x_client=XClient(settings),
        web_client=WebFeedClient(settings),
        writer=TrendWriter(settings),
        output_writer=OutputWriter(settings),
    )


def selected_handles(args: argparse.Namespace, default_handles: list[str]) -> list[str]:
    return [
        handle.strip().lstrip("@")
        for handle in (args.handles.split(",") if args.handles else default_handles)
        if handle.strip()
    ]


def settings_for_mode(settings, args: argparse.Namespace):
    if args.mode == "top-ai":
        handles = selected_handles(args, TOP_AI_ACCOUNT_HANDLES)
        return replace(
            settings,
            topic_query="top AI account signals",
            enable_x_watchlist=True,
            enable_x_scan=False,
            enable_x_timeline=False,
            enable_web_scan=False,
            x_watch_handles=handles,
            max_watchlist_results=max(args.limit * 3, settings.max_watchlist_results),
        )
    if args.mode == "india":
        return replace(
            settings,
            topic_query=(
                '(AI OR openai OR claude OR gemini OR startups OR "developer tools" OR chips OR '
                'iphone OR samsung OR wearables OR "tech jobs" OR hiring OR layoffs) '
                '(india OR indian OR bengaluru OR bangalore OR mumbai OR delhi OR upi OR aadhaar OR '
                'jio OR airtel OR flipkart OR zomato OR swiggy OR ola OR paytm OR zepto) lang:en -is:retweet'
            ),
        )
    if args.mode == "growth":
        return replace(
            settings,
            topic_query=(
                '(AI OR openai OR claude OR gemini OR agents OR "developer tools" OR startups OR '
                'chips OR "tech jobs" OR careers OR funding OR regulation) '
                '(india OR indian OR bengaluru OR founders OR developers OR students OR creators OR buyers OR pricing)'
            ),
            enable_x_scan=False,
            enable_x_watchlist=False,
            enable_x_timeline=False,
            enable_web_scan=True,
        )
    if args.mode == "nvidia":
        return replace(
            settings,
            topic_query=(
                'NVIDIA Jensen Huang GTC Taipei Computex RTX Spark AI PCs Vera CPU '
                'Vera Rubin Blackwell NVLink Spectrum DGX CUDA GPU AI chips AI factory inference'
            ),
            enable_x_scan=False,
            enable_x_watchlist=False,
            enable_x_timeline=False,
            enable_web_scan=True,
            max_web_results=max(80, settings.max_web_results),
            web_feed_urls=NVIDIA_FEEDS,
            web_keywords=NVIDIA_KEYWORDS,
        )
    if args.mode == "tesla":
        return replace(
            settings,
            topic_query=(
                "Tesla Elon Musk Model Y Model 3 Cybertruck FSD robotaxi autonomous driving "
                "Optimus Supercharger Megapack battery EV deliveries earnings Tesla India"
            ),
            enable_x_scan=False,
            enable_x_watchlist=False,
            enable_x_timeline=False,
            enable_web_scan=True,
            max_web_results=max(80, settings.max_web_results),
            web_feed_urls=TESLA_FEEDS,
            web_keywords=TESLA_KEYWORDS,
        )
    return settings


def print_reply_scout_result(result: dict) -> None:
    print("Reply scout pack created from public web scrape")
    print(f"Sources found: {result.get('source_count', 0)}")
    if result.get("web_scrape_errors"):
        print("Web scrape warnings:")
        for error in result["web_scrape_errors"]:
            print(f"- {error}")
    print(result["output_files"]["markdown"])
    print(result["output_files"]["copy_paste_replies"])


def main() -> None:
    args = parse_args()
    load_dotenv()
    settings = settings_for_mode(load_settings(), args)
    workflow = build_workflow(settings)
    if args.mode == "reply-scout":
        handles = selected_handles(args, DEFAULT_REPLY_SCOUT_HANDLES)
        workflow.output_writer.clear_generated_files()
        result = workflow.reply_scout(handles=handles, limit=args.limit)
        print_reply_scout_result(result)
        if result.get("source_count", 0) == 0:
            print("No source posts were found from public web mirrors. Try fewer/different --handles or rerun later.")
        return
    style = args.style.strip() or DEFAULT_STYLES[args.mode]
    result = workflow.fresh_optimize(
        style=style,
        limit=args.limit,
    )
    scan = result.get("scan", {})
    created_count = scan.get("created_count", 0)
    source_count = scan.get("source_count", 0)
    x_watchlist_count = scan.get("x_watchlist_source_count", 0)
    x_timeline_count = scan.get("x_timeline_source_count", 0)
    x_errors = scan.get("x_scan_errors", [])
    errors = scan.get("web_feed_errors", [])

    label = {
        "fresh": "Fresh high-CTR pack created",
        "top-ai": "Top AI account high-CTR pack created",
        "india": "Latest India-aware high-CTR pack created",
        "growth": "X-algorithm-aware growth pack created",
        "nvidia": "NVIDIA event high-CTR pack created",
        "tesla": "Tesla high-CTR pack created",
    }[args.mode]
    print(label)
    print(f"Sources found: {source_count}")
    print(f"Tracked-account posts: {x_watchlist_count}")
    print(f"Timeline posts: {x_timeline_count}")
    print(f"New opportunities: {created_count}")
    if x_errors:
        print("X warnings:")
        for error in x_errors:
            print(f"- {error}")
    if errors:
        print("Feed warnings:")
        for error in errors:
            print(f"- {error}")
    print(result["output_files"]["markdown"])
    if result["output_files"].get("ready_tweets"):
        print(result["output_files"]["ready_tweets"])
    if result["output_files"].get("india_tweets"):
        print(result["output_files"]["india_tweets"])
    if created_count == 0:
        print("No post-ready topics were found. Check feed/network access, X API access, or broaden WEB_KEYWORDS.")


if __name__ == "__main__":
    main()
