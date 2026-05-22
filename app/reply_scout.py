from __future__ import annotations

from typing import Any


DEFAULT_REPLY_SCOUT_HANDLES = [
    "sama",
    "AnthropicAI",
    "elonmusk",
    "nvidia",
    "OpenAI",
    "thsottiaux",
    "GoogleDeepMind",
    "karpathy",
    "gdb",
    "bindureddy",
    "perplexity_ai",
    "lmarena_ai",
    "huggingface",
    "emollick",
    "IndianTechGuide",
]

SLOP_PHRASES = [
    "game-changer",
    "revolutionary",
    "this changes everything",
    "the future of",
    "unlocking new possibilities",
]


class ReplyScout:
    """Build a response/repost pack from exact source tweets.

    The source tweet text is preserved exactly for review. Generated replies and
    quote posts are original copy-paste text for manual use; this class does not
    auto-post or copy another user's text as the user's own post.
    """

    def build_pack(
        self,
        source_tweets: list[dict[str, Any]],
        *,
        limit: int = 10,
    ) -> dict[str, Any]:
        ranked = sorted(
            source_tweets,
            key=lambda tweet: (self._engagement_score(tweet), tweet.get("created_at", "")),
            reverse=True,
        )[:limit]
        return {
            "summary": "Reply-scout pack: exact source tweets plus copy-paste replies and quote-post options for manual engagement.",
            "items": [self._item(tweet, index) for index, tweet in enumerate(ranked, start=1)],
        }

    def _item(self, tweet: dict[str, Any], rank: int) -> dict[str, Any]:
        source = self._source_tweet(tweet)
        engagement_score = self._engagement_score(tweet)
        return {
            "rank": rank,
            "engagement_score": engagement_score,
            "source_tweet": source,
            "reply_options": self._reply_options(source),
            "quote_post_options": self._quote_post_options(source),
            "repost_note": "Use X's repost button for the original. Use quote options only if adding your own view.",
        }

    def _source_tweet(self, tweet: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(tweet.get("id", "")),
            "author_name": str(tweet.get("author_name", tweet.get("author_username", ""))),
            "author_username": str(tweet.get("author_username", "unknown")),
            "text": str(tweet.get("text", "")),
            "url": str(tweet.get("url", "")),
            "created_at": str(tweet.get("created_at", "")),
            "public_metrics": tweet.get("public_metrics", {}) or {},
        }

    def _reply_options(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        topic = self._topic(source["text"])
        author = source["author_username"]
        options = [
            (
                "useful_addition",
                f"The underrated part here is distribution. If {topic} becomes cheaper/easier, the winners will be the teams that turn it into a real workflow, not just a demo.",
            ),
            (
                "india_angle",
                f"India angle: this matters most if it lowers cost or friction for small teams. Adoption here usually follows price + trust + clear use case, not hype.",
            ),
            (
                "developer_angle",
                f"Developer takeaway: the edge moves to people who can test this in real products quickly, measure the output, and ship the useful parts before the noise settles.",
            ),
            (
                "sharp_question",
                f"The key question now: does this change daily workflow for builders, or is it mostly a capability announcement? That difference matters.",
            ),
        ]
        return [
            {
                "rank": index,
                "format": label,
                "text": self._clean(self._trim(text)),
                "why_it_can_work": f"Adds a specific angle under @{author}'s original post without copying it.",
            }
            for index, (label, text) in enumerate(options, start=1)
        ]

    def _quote_post_options(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        topic = self._topic(source["text"])
        options = [
            (
                "contrarian",
                f"The signal here is not {topic} itself. It is what happens when this gets cheap enough for normal teams to use every week.",
            ),
            (
                "india_founder",
                "For Indian founders, the real test is simple: does this reduce cost, speed up shipping, or open a distribution edge? If yes, it is worth testing immediately.",
            ),
            (
                "developer",
                "The best developers will not just use this. They will build evaluation, review, and shipping loops around it. That is where the leverage is.",
            ),
        ]
        return [
            {
                "rank": index,
                "format": label,
                "text": self._clean(self._trim(text)),
                "why_it_can_work": "Works as a quote post because it adds a standalone point to the original tweet.",
            }
            for index, (label, text) in enumerate(options, start=1)
        ]

    def _engagement_score(self, tweet: dict[str, Any]) -> float:
        metrics = tweet.get("public_metrics", {}) or {}
        fallback_score = float(tweet.get("score", 0) or 0)
        metric_score = (
            float(metrics.get("like_count", 0) or 0)
            + float(metrics.get("retweet_count", 0) or 0) * 2
            + float(metrics.get("reply_count", 0) or 0) * 1.5
            + float(metrics.get("quote_count", 0) or 0) * 2
        )
        return max(fallback_score, metric_score)

    def _topic(self, text: str) -> str:
        clean = " ".join(text.split())
        if not clean:
            return "this update"
        words = clean.split()
        return " ".join(words[:8]).rstrip(".,:;!? ")

    def _clean(self, text: str) -> str:
        clean = text
        lower = clean.lower()
        if any(phrase in lower for phrase in SLOP_PHRASES):
            clean = clean.replace("game-changer", "important signal")
            clean = clean.replace("Game-changer", "Important signal")
            clean = clean.replace("revolutionary", "useful")
            clean = clean.replace("Revolutionary", "Useful")
            clean = clean.replace("this changes everything", "this changes the workflow")
            clean = clean.replace("This changes everything", "This changes the workflow")
            clean = clean.replace("unlocking new possibilities", "opening practical use cases")
        return clean

    def _trim(self, value: str, limit: int = 260) -> str:
        clean = " ".join(value.split())
        if len(clean) <= limit:
            return clean
        return clean[: limit - 1].rstrip() + "..."
