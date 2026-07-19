from datetime import datetime, timedelta, timezone

from app.verified_brief import VerifiedBriefBuilder


def source(url: str, title: str, created_at: str) -> dict:
    return {
        "url": url,
        "title": title,
        "text": f"{title}\nA short source summary.",
        "created_at": created_at,
        "source_type": "web",
        "author_name": "feed",
    }


def test_verified_brief_prioritizes_fresh_primary_sources():
    now = datetime.now(timezone.utc)
    brief = VerifiedBriefBuilder(max_age_hours=48).build(
        [
            source("https://openai.com/news/example", "OpenAI release", now.isoformat()),
            source("https://example.test/story", "Unverified story", now.isoformat()),
            source(
                "https://techcrunch.com/story",
                "Old reporting",
                (now - timedelta(hours=60)).isoformat(),
            ),
        ]
    )

    assert brief["ready_count"] == 1
    assert brief["items"][0]["source_level"] == "primary"
    assert brief["items"][0]["eligible"] is True
    assert brief["items"][1]["source_level"] == "discovery"
    assert brief["items"][2]["eligible"] is False


def test_openai_research_is_not_marked_primary_for_an_unknown_domain():
    now = datetime.now(timezone.utc)
    item = source("https://example.test/story", "Cloud-researched story", now.isoformat())
    item["source_type"] = "openai_web_research"

    brief = VerifiedBriefBuilder().build([item])

    assert brief["items"][0]["source_level"] == "web_researched"


def test_google_news_requires_a_recognized_publisher():
    now = datetime.now(timezone.utc)
    trusted = source("https://news.google.com/rss/articles/one", "Kimi release", now.isoformat())
    trusted["author_name"] = "Axios"
    unknown = source("https://news.google.com/rss/articles/two", "Unverified claim", now.isoformat())
    unknown["author_name"] = "Random Blog"

    brief = VerifiedBriefBuilder().build([trusted, unknown])

    levels = {item["title"]: item["source_level"] for item in brief["items"]}
    assert levels["Kimi release"] == "reputable"
    assert levels["Unverified claim"] == "discovery"


def test_google_news_uses_original_official_publisher_domain():
    now = datetime.now(timezone.utc)
    official = source("https://news.google.com/rss/articles/one", "GPT release", now.isoformat())
    official["author_name"] = "OpenAI"
    official["publisher_url"] = "https://openai.com"

    brief = VerifiedBriefBuilder().build([official])

    assert brief["items"][0]["source_level"] == "primary"
