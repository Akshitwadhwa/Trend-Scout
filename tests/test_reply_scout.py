from app.reply_scout import DEFAULT_REPLY_SCOUT_HANDLES, ReplyScout


def source_tweet(**overrides):
    base = {
        "id": "123",
        "source_type": "x_watchlist",
        "text": "We are launching a new model today. It is faster and cheaper for developers.",
        "created_at": "2026-05-16T10:00:00Z",
        "author_name": "Sam Altman",
        "author_username": "sama",
        "public_metrics": {
            "like_count": 10000,
            "retweet_count": 2000,
            "reply_count": 900,
            "quote_count": 500,
        },
        "score": 15350,
        "url": "https://x.com/sama/status/123",
    }
    base.update(overrides)
    return base


def test_default_reply_scout_handles_include_user_requested_accounts():
    handles = {handle.lower() for handle in DEFAULT_REPLY_SCOUT_HANDLES}

    assert "sama" in handles
    assert "anthropicai" in handles
    assert "elonmusk" in handles
    assert "nvidia" in handles
    assert "openai" in handles


def test_reply_scout_preserves_source_tweet_exactly_and_url():
    exact_text = "Claude Opus 4.1 is now available to all paid users. Try it today."
    scout = ReplyScout()

    pack = scout.build_pack([source_tweet(text=exact_text, author_username="AnthropicAI")], limit=1)

    item = pack["items"][0]
    assert item["source_tweet"]["text"] == exact_text
    assert item["source_tweet"]["url"] == "https://x.com/sama/status/123"
    assert item["source_tweet"]["author_username"] == "AnthropicAI"


def test_reply_scout_sorts_high_engagement_tweets_first():
    scout = ReplyScout()
    low = source_tweet(id="low", author_username="nvidia", score=10, public_metrics={"like_count": 10})
    high = source_tweet(id="high", author_username="elonmusk", score=20000, public_metrics={"like_count": 20000})

    pack = scout.build_pack([low, high], limit=2)

    assert [item["source_tweet"]["id"] for item in pack["items"]] == ["high", "low"]


def test_reply_scout_outputs_copy_paste_reply_and_quote_variants():
    scout = ReplyScout()

    pack = scout.build_pack([source_tweet()], limit=1)
    item = pack["items"][0]

    assert item["engagement_score"] > 0
    assert len(item["reply_options"]) >= 3
    assert len(item["quote_post_options"]) >= 2
    assert all(option["text"] for option in item["reply_options"])
    assert all(len(option["text"]) <= 260 for option in item["reply_options"])
    assert all("game-changer" not in option["text"].lower() for option in item["reply_options"])
