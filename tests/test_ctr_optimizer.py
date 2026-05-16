from app.ctr_optimizer import AudienceMode, CTROptimizer, GENERIC_SLOP_PHRASES, X_ALGORITHM_PRINCIPLES


def opportunity(**overrides):
    base = {
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
    }
    base.update(overrides)
    return base


def test_scores_viral_ctr_before_generation():
    optimizer = CTROptimizer()

    strong = opportunity()
    weak = opportunity(
        id=2,
        title="General thoughts about technology",
        why_now="Technology is always changing.",
        post_angle="AI is transforming the future and unlocking new possibilities.",
        confidence=0.3,
        sources=[],
    )

    ranked = optimizer.rank_opportunities([weak, strong], limit=2)

    assert ranked[0]["id"] == 1
    assert ranked[0]["viral_score"] >= 70
    assert ranked[0]["viral_score"] > ranked[1]["viral_score"]
    assert "audience fit" in ranked[0]["score_breakdown"]
    assert "engagement probability" in ranked[0]["score_breakdown"]
    assert "profile follow potential" in ranked[0]["score_breakdown"]


def test_generates_hook_variants_and_ranks_best_hook():
    optimizer = CTROptimizer()
    hooks = optimizer.generate_hooks(opportunity(), AudienceMode.INDIA_FOUNDERS)

    assert len(hooks) >= 5
    assert hooks[0]["score"] >= hooks[-1]["score"]
    assert any("India" in hook["text"] or "Indian" in hook["text"] for hook in hooks)
    assert all(len(hook["text"]) <= 140 for hook in hooks)


def test_no_generic_slop_filter_rewrites_or_rejects_bad_phrases():
    optimizer = CTROptimizer()
    slop = "AI is transforming the future and unlocking new possibilities for everyone. This is a game-changer."

    cleaned = optimizer.clean_generic_slop(slop, opportunity())

    assert cleaned != slop
    assert not any(phrase in cleaned.lower() for phrase in GENERIC_SLOP_PHRASES)
    assert "OpenAI" in cleaned or "API" in cleaned or "cost" in cleaned.lower()


def test_audience_modes_create_distinct_posts_for_india_founders_devs_students():
    optimizer = CTROptimizer()
    opp = opportunity()

    founder = optimizer.build_ready_tweet(opp, AudienceMode.INDIA_FOUNDERS)
    dev = optimizer.build_ready_tweet(opp, AudienceMode.INDIA_DEVELOPERS)
    student = optimizer.build_ready_tweet(opp, AudienceMode.INDIA_STUDENTS)

    assert founder != dev != student
    assert "founder" in founder.lower() or "startup" in founder.lower()
    assert "developer" in dev.lower() or "dev" in dev.lower() or "ship" in dev.lower()
    assert "student" in student.lower() or "career" in student.lower() or "portfolio" in student.lower()
    assert all(len(tweet) <= 260 for tweet in [founder, dev, student])


def test_build_ctr_items_filters_low_quality_and_outputs_variants():
    optimizer = CTROptimizer(min_viral_score=70)
    items = optimizer.build_ctr_items(
        [
            opportunity(),
            opportunity(
                id=2,
                title="The future of tech",
                why_now="Technology keeps evolving.",
                post_angle="This could change everything in today's fast-paced world.",
                confidence=0.2,
                sources=[],
            ),
        ],
        audience_modes=[AudienceMode.INDIA_FOUNDERS, AudienceMode.INDIA_DEVELOPERS, AudienceMode.INDIA_STUDENTS],
    )

    assert len(items) == 1
    item = items[0]
    assert item["opportunity_id"] == 1
    assert item["ctr_score"] >= 70
    assert len(item["hooks"]) >= 5
    assert len(item["ready_to_post_tweets"]) >= 3
    assert {tweet["audience_mode"] for tweet in item["ready_to_post_tweets"]} >= {
        "india_founders",
        "india_developers",
        "india_students",
    }
    assert item["x_algorithm_notes"]["ranking_factors_used"] == X_ALGORITHM_PRINCIPLES
    assert "follows" in item["x_algorithm_notes"]["primary_goal"]
