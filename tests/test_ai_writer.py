from app.ai_writer import TrendWriter


class SettingsStub:
    openai_api_key = ""
    openai_model = "gpt-test"


def test_fallback_ctr_pack_uses_optimizer_scoring_and_audience_modes():
    writer = TrendWriter(SettingsStub())
    pack = writer.build_ctr_pack(
        opportunities=[
            {
                "id": 1,
                "category": "AI",
                "title": "OpenAI cuts API pricing for smaller teams",
                "why_now": "OpenAI announced lower API prices today and developers are comparing migration costs.",
                "post_angle": "Lower inference costs make AI features easier to ship for small Indian startups and students.",
                "confidence": 0.8,
                "sources": [
                    {
                        "source_type": "x_watchlist",
                        "author_username": "OpenAI",
                        "title": "OpenAI pricing update",
                        "url": "https://x.com/openai/status/1",
                        "public_metrics": {"like_count": 900, "retweet_count": 200, "quote_count": 80},
                    }
                ],
            },
            {
                "id": 2,
                "category": "General Tech",
                "title": "The future of tech",
                "why_now": "Technology keeps evolving.",
                "post_angle": "This could change everything in today's fast-paced world.",
                "confidence": 0.2,
                "sources": [],
            },
        ],
        style="India founders, developers, students",
    )

    assert pack["summary"].startswith("CTR-optimized")
    assert len(pack["items"]) == 1
    item = pack["items"][0]
    assert item["opportunity_id"] == 1
    assert item["viral_score"] >= 70
    assert len(item["hook_variants"]) >= 5
    assert {tweet["audience_mode"] for tweet in item["ready_to_post_tweets"]} >= {
        "india_founders",
        "india_developers",
        "india_students",
    }
