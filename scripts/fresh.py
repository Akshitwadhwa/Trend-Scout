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
    "cursor_ai",
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

AI_RADAR_FEEDS = [
    "https://news.google.com/rss/search?q=OpenAI%20OR%20Anthropic%20OR%20Claude%20OR%20ChatGPT%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Google%20DeepMind%20OR%20Gemini%20OR%20Meta%20AI%20OR%20Llama%20OR%20xAI%20OR%20Grok%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Kimi%20OR%20Moonshot%20OR%20DeepSeek%20OR%20Qwen%20OR%20Mistral%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Cursor%20AI%20OR%20Cursor%20Composer%20OR%20Cursor%20Grok%20when:2h&hl=en-IN&gl=IN&ceid=IN:en",
    "https://huggingface.co/blog/feed.xml",
]

AI_RADAR_KEYWORDS = [
    "openai", "chatgpt", "gpt", "anthropic", "claude", "google deepmind", "gemini",
    "meta ai", "llama", "xai", "grok", "kimi", "moonshot", "deepseek", "qwen",
    "mistral", "hugging face", "ai model", "model release", "api", "agent", "benchmark",
    "open weights", "reasoning", "coding model", "multimodal", "cursor", "cursor ai", "composer",
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

WEARABLES_FEEDS = [
    "https://news.google.com/rss/search?q=Garmin%20wearables%20fitness%20watch%20OR%20Garmin%20Forerunner%20OR%20Garmin%20Fenix%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=WHOOP%20fitness%20tracker%20recovery%20subscription%20OR%20WHOOP%20health%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Oura%20Ring%20sleep%20readiness%20health%20tracking%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Apple%20Watch%20health%20fitness%20watchOS%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Samsung%20Health%20Galaxy%20Watch%20fitness%20when:14d&hl=en-IN&gl=IN&ceid=IN:en",
]

WEARABLES_KEYWORDS = [
    "garmin", "whoop", "oura", "oura ring", "apple watch", "watchos", "samsung health", "galaxy watch",
    "fitness tracker", "fitness watch", "smartwatch", "wearable", "wearables", "health tracking", "recovery",
    "readiness", "sleep tracking", "heart rate", "hrv", "training load", "gps", "running", "cycling",
]


DEFAULT_STYLES = {
    "fresh": "factual, statement-led, concrete, high CTR, no hype",
    "top-ai": (
        "factual, statement-led, concrete, high CTR, no hype, based on signals from top AI accounts, "
        "do not copy their wording, turn each signal into an original factual X post"
    ),
    "ai-radar": (
        "current AI and developer-tool news, casual and sharp student developer voice, name the model or company, "
        "explain what changed and one honest implication, no hype, no fake benchmark claims"
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
    "wearables": (
        "current wearable and fitness-tech news, casual and sharp student creator voice, name the company or product, "
        "explain the concrete change so a non-expert understands it, then add one honest buyer or user implication; "
        "Garmin vs WHOOP vs Oura vs Apple Watch vs Samsung Health where relevant, no hype, no fake health claims"
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
        choices=["fresh", "top-ai", "ai-radar", "india", "growth", "nvidia", "tesla", "wearables", "reply-scout"],
        default="fresh",
        help="fresh=normal scan, top-ai=signals from top AI accounts, ai-radar=latest model/company release radar, india=latest India-aware tech posts, growth=X-algorithm-aware impression/CTR/follower-growth pack, nvidia=NVIDIA event/chips/AI factory scan, tesla=Tesla EV/FSD/Optimus/energy scan, wearables=on-demand Garmin/WHOOP/Oura/Apple Watch/Samsung Health scan, reply-scout=high-signal source tweets plus copy-paste replies",
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
    if args.mode == "ai-radar":
        return replace(
            settings,
            topic_query=(
                "OpenAI ChatGPT GPT Anthropic Claude Google DeepMind Gemini Meta AI Llama "
                "xAI Grok Kimi Moonshot DeepSeek Qwen Mistral Hugging Face model release API agent"
            ),
            enable_x_scan=False,
            enable_x_watchlist=False,
            enable_x_timeline=False,
            enable_web_scan=True,
            max_web_results=max(80, settings.max_web_results),
            web_feed_urls=AI_RADAR_FEEDS,
            web_keywords=AI_RADAR_KEYWORDS,
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
    if args.mode == "wearables":
        return replace(
            settings,
            topic_query=(
                "Garmin WHOOP Oura Ring Apple Watch watchOS Samsung Health Galaxy Watch "
                "wearables fitness tracker smartwatch recovery sleep tracking HRV training load"
            ),
            enable_x_scan=False,
            enable_x_watchlist=False,
            enable_x_timeline=False,
            enable_web_scan=True,
            max_web_results=max(80, settings.max_web_results),
            web_feed_urls=WEARABLES_FEEDS,
            web_keywords=WEARABLES_KEYWORDS,
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
        "ai-radar": "Latest AI model radar pack created",
        "india": "Latest India-aware high-CTR pack created",
        "growth": "X-algorithm-aware growth pack created",
        "nvidia": "NVIDIA event high-CTR pack created",
        "tesla": "Tesla high-CTR pack created",
        "wearables": "Wearables and fitness-tech high-CTR pack created",
    }[args.mode]
    print(label)
    print(f"Sources found: {source_count}")
    if scan.get("cloud_source_count") is not None:
        print(f"OpenAI web-researched sources: {scan.get('cloud_source_count', 0)}")
    if scan.get("discovered_count", source_count) > source_count:
        counts = scan.get("verified_brief", {}).get("source_counts", {})
        print(
            "Quality gate: "
            f"{source_count} post-ready of {scan['discovered_count']} discovered "
            f"(primary {counts.get('primary', 0)}, web-researched {counts.get('web_researched', 0)}, "
            f"reputable {counts.get('reputable', 0)}, discovery {counts.get('discovery', 0)})."
        )
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
    verified = result["output_files"].get("verified_brief")
    if verified:
        print(verified["markdown"])
    research = scan.get("openai_research", {})
    if research.get("enabled") and not research.get("configured"):
        print("OpenAI web research is enabled but no API key is configured; using free verified sources only.")
    if research.get("error"):
        print(f"OpenAI web research warning: {research['error']}")
    if created_count == 0:
        print("No post-ready topics were found. Open the verified brief: discovery stories are visible there, but are not turned into tweets until their source is trustworthy.")


if __name__ == "__main__":
    main()
