from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


GENERIC_SLOP_PHRASES = [
    "game-changer",
    "game changer",
    "revolutionary",
    "ai is transforming",
    "the future of",
    "this could change everything",
    "in today's fast-paced world",
    "in today’s fast-paced world",
    "it remains to be seen",
    "only time will tell",
    "unlocking new possibilities",
]


class AudienceMode(StrEnum):
    INDIA_FOUNDERS = "india_founders"
    INDIA_DEVELOPERS = "india_developers"
    INDIA_STUDENTS = "india_students"
    INDIAN_CREATORS = "indian_creators"
    BUYERS = "buyers"
    GENERAL_TECH = "general_tech"


@dataclass(frozen=True)
class ScoreWeights:
    novelty: int = 14
    audience_fit: int = 20
    curiosity: int = 12
    practical_value: int = 14
    source_strength: int = 14
    postability: int = 8
    engagement_probability: int = 10
    profile_follow_potential: int = 8


X_ALGORITHM_PRINCIPLES = [
    "retrieve broad candidates, then rank and filter hard",
    "optimize for likely replies, reposts, likes, profile clicks, follows, dwell time, and saves/bookmarks",
    "early high-quality engagement matters more than generic reach bait",
    "post-selection filters can suppress spammy, duplicate, unsafe, or low-quality engagement-bait posts",
    "conversation quality and creator-audience fit help posts travel beyond followers",
]


class CTROptimizer:
    def __init__(self, min_viral_score: int = 60) -> None:
        self.min_viral_score = min_viral_score
        self.weights = ScoreWeights()

    def rank_opportunities(
        self,
        opportunities: list[dict[str, Any]],
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        scored = []
        for opportunity in opportunities:
            payload = dict(opportunity)
            score, breakdown = self.score_opportunity(opportunity)
            payload["viral_score"] = score
            payload["score_breakdown"] = breakdown
            scored.append(payload)
        scored.sort(key=lambda item: item["viral_score"], reverse=True)
        return scored[:limit]

    def score_opportunity(self, opportunity: dict[str, Any]) -> tuple[int, dict[str, int]]:
        text = self._opportunity_text(opportunity)
        sources = opportunity.get("sources", []) or []
        confidence = float(opportunity.get("confidence", 0.5) or 0.5)

        breakdown = {
            "novelty": self._score_novelty(text),
            "audience fit": self._score_audience_fit(text),
            "curiosity": self._score_curiosity(text),
            "practical value": self._score_practical_value(text),
            "source strength": self._score_source_strength(sources, confidence),
            "postability": self._score_postability(opportunity),
            "engagement probability": self._score_engagement_probability(text),
            "profile follow potential": self._score_profile_follow_potential(text),
        }
        weighted = (
            breakdown["novelty"] * self.weights.novelty
            + breakdown["audience fit"] * self.weights.audience_fit
            + breakdown["curiosity"] * self.weights.curiosity
            + breakdown["practical value"] * self.weights.practical_value
            + breakdown["source strength"] * self.weights.source_strength
            + breakdown["postability"] * self.weights.postability
            + breakdown["engagement probability"] * self.weights.engagement_probability
            + breakdown["profile follow potential"] * self.weights.profile_follow_potential
        ) / 100
        penalty = self._generic_slop_penalty(text)
        score = max(1, min(100, round(weighted - penalty)))
        return score, breakdown

    def build_ctr_items(
        self,
        opportunities: list[dict[str, Any]],
        *,
        audience_modes: list[AudienceMode] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        modes = audience_modes or [
            AudienceMode.INDIA_FOUNDERS,
            AudienceMode.INDIA_DEVELOPERS,
            AudienceMode.INDIA_STUDENTS,
        ]
        items = []
        for opportunity in self.rank_opportunities(opportunities, limit=limit):
            viral_score = int(opportunity["viral_score"])
            if viral_score < self.min_viral_score:
                continue
            hooks = self.generate_hooks(opportunity, modes[0])
            ready_tweets = []
            for rank, mode in enumerate(modes, start=1):
                tweet = self.build_ready_tweet(opportunity, mode)
                ready_tweets.append(
                    {
                        "rank": rank,
                        "audience_mode": mode.value,
                        "format": self._format_for_mode(mode),
                        "score": max(1, viral_score - rank + 1),
                        "tweet": tweet,
                        "why_it_works": self._why_mode_works(mode),
                    }
                )
            best = ready_tweets[0]
            items.append(
                {
                    "opportunity_id": opportunity["id"],
                    "category": opportunity.get("category", "General Tech"),
                    "title": opportunity["title"],
                    "viral_score": viral_score,
                    "score_breakdown": opportunity["score_breakdown"],
                    "best_angle": opportunity.get("post_angle", ""),
                    "best_hook": hooks[0]["text"],
                    "best_ready_to_post": best["tweet"],
                    "format_comparison": [
                        {
                            "format": item["format"],
                            "score": item["score"],
                            "tweet": item["tweet"],
                            "why_it_works": item["why_it_works"],
                        }
                        for item in ready_tweets
                    ],
                    "ready_to_post_tweets": ready_tweets,
                    "india_angle": self._india_angle(opportunity),
                    "india_relevance_score": self._score_audience_fit(self._opportunity_text(opportunity)),
                    "india_long_tweets": [
                        {
                            "rank": index,
                            "audience_mode": mode.value,
                            "tweet": self._trim(self.build_ready_tweet(opportunity, mode), 275),
                            "why_it_works": self._why_mode_works(mode),
                        }
                        for index, mode in enumerate(modes, start=1)
                    ],
                    "hooks": [hook["text"] for hook in hooks],
                    "hook_variants": hooks,
                    "post_variants": [item["tweet"] for item in ready_tweets],
                    "poll": {
                        "question": f"What matters most in {opportunity.get('category', 'tech')} adoption?",
                        "options": ["Price", "Trust", "Speed", "Distribution"],
                    },
                    "mini_thread": self._mini_thread(opportunity),
                    "visual_card_idea": self._visual_idea(opportunity),
                    "ctr_score": viral_score,
                    "impression_score": max(1, min(100, viral_score - 3 + self._source_velocity_bonus(opportunity.get("sources", [])) + self._algorithm_distribution_bonus(opportunity))),
                    "risk_score": self._risk_score(opportunity),
                    "x_algorithm_notes": {
                        "ranking_factors_used": X_ALGORITHM_PRINCIPLES,
                        "primary_goal": "earn saves/profile clicks/follows with factual, low-hype posts",
                    },
                    "why_this_can_work": "Passed X-algorithm-aware scoring: clear fact pattern, audience fit, save potential, profile-follow reason, and low generic-slop risk.",
                }
            )
        return items

    def generate_hooks(
        self,
        opportunity: dict[str, Any],
        audience_mode: AudienceMode = AudienceMode.GENERAL_TECH,
    ) -> list[dict[str, Any]]:
        category = opportunity.get("category", "tech")
        topic = self._short_topic(opportunity)
        audience = self._audience_label(audience_mode)
        templates = [
            f"{topic} is a {category} signal, not just another launch update.",
            f"{audience} should read {topic} as a cost, workflow, or distribution signal.",
            f"{topic} changes the adoption math for {audience}.",
            f"The concrete signal in {topic}: distribution may matter more than the demo.",
            f"For India, the relevant part of {topic} is adoption cost and workflow impact.",
            f"{topic} creates a margin question for teams building around {category}.",
            f"{topic} is mainly a workflow-change story, not a hype cycle story.",
            f"Pricing, adoption, and daily usage matter more here than the launch post.",
            f"For {category}, the real signal is adoption speed and production usage.",
            f"{audience} can use {topic} as a practical market signal this month.",
        ]
        hooks = []
        for text in templates:
            clean = self._trim(text, 140)
            hooks.append({"text": clean, "score": self._hook_score(clean, opportunity)})
        hooks.sort(key=lambda hook: hook["score"], reverse=True)
        return hooks

    def clean_generic_slop(self, text: str, opportunity: dict[str, Any]) -> str:
        clean = " ".join(text.split())
        if not any(phrase in clean.lower() for phrase in GENERIC_SLOP_PHRASES):
            return self._trim(clean)
        category = opportunity.get("category", "Tech")
        angle = opportunity.get("post_angle", "").strip() or opportunity.get("why_now", "").strip()
        title = opportunity.get("title", category)
        replacement = f"{title}: {angle}"
        return self._trim(replacement)

    def build_ready_tweet(
        self,
        opportunity: dict[str, Any],
        audience_mode: AudienceMode = AudienceMode.GENERAL_TECH,
    ) -> str:
        category = opportunity.get("category", "Tech")
        angle = self.clean_generic_slop(str(opportunity.get("post_angle", "")), opportunity)
        if audience_mode == AudienceMode.INDIA_FOUNDERS:
            tweet = f"Indian founders should track this {category} shift: {angle} The practical edge is cheaper experiments, faster shipping, and stronger distribution."
        elif audience_mode == AudienceMode.INDIA_DEVELOPERS:
            tweet = f"Developer signal: {angle} Lower costs move the advantage toward teams that can ship, test, and review AI features faster."
        elif audience_mode == AudienceMode.INDIA_STUDENTS:
            tweet = f"For Indian students, this {category} signal matters because {angle} The career edge is a portfolio built around real workflows, not only certificates."
        elif audience_mode == AudienceMode.INDIAN_CREATORS:
            tweet = f"For Indian creators, {category} becomes useful when {angle} The advantage goes to creators who turn it into repeatable workflows."
        elif audience_mode == AudienceMode.BUYERS:
            tweet = f"Buyer angle: {angle} Adoption depends on price, trust, and whether the product becomes useful in daily workflows."
        else:
            tweet = f"{category}: {angle} The real signal is whether this changes cost, workflow, or distribution."
        return self.clean_generic_slop(tweet, opportunity)

    def _opportunity_text(self, opportunity: dict[str, Any]) -> str:
        parts = [
            str(opportunity.get("category", "")),
            str(opportunity.get("title", "")),
            str(opportunity.get("why_now", "")),
            str(opportunity.get("post_angle", "")),
        ]
        for source in opportunity.get("sources", []) or []:
            parts.extend([str(source.get("title", "")), str(source.get("author_username", ""))])
        return " ".join(parts).lower()

    def _score_novelty(self, text: str) -> int:
        score = 35
        score += 20 if any(word in text for word in ["today", "announced", "launch", "release", "pricing", "new", "cuts", "changes"]) else 0
        score += 15 if any(word in text for word in ["api", "model", "developer", "startup", "india", "cost"]) else 0
        score -= 25 if any(word in text for word in ["always changing", "future of tech", "technology keeps evolving"]) else 0
        return self._bound(score)

    def _score_audience_fit(self, text: str) -> int:
        score = 35
        score += 20 if any(word in text for word in ["india", "indian", "bengaluru", "upi", "rupees"]) else 0
        score += 18 if any(word in text for word in ["founder", "startup", "developer", "student", "creator", "buyer"]) else 0
        score += 16 if any(word in text for word in ["cost", "pricing", "ship", "jobs", "career", "portfolio", "api"]) else 0
        return self._bound(score)

    def _score_curiosity(self, text: str) -> int:
        score = 35
        score += 12 if any(word in text for word in ["why", "signal", "shift", "quiet", "less about", "real question"]) else 0
        score += 12 if any(word in text for word in ["lower", "cheaper", "cuts", "competing", "migration"]) else 0
        return self._bound(score)

    def _score_practical_value(self, text: str) -> int:
        score = 30
        score += 18 if any(word in text for word in ["cost", "pricing", "ship", "workflow", "features", "api"]) else 0
        score += 14 if any(word in text for word in ["students", "developers", "founders", "startups", "buyers"]) else 0
        return self._bound(score)

    def _score_engagement_probability(self, text: str) -> int:
        score = 30
        score += 16 if any(word in text for word in ["question", "why", "should", "would", "debate", "takeaway"]) else 0
        score += 14 if any(word in text for word in ["save", "bookmark", "checklist", "framework", "playbook", "steps"]) else 0
        score += 12 if any(word in text for word in ["compare", "vs", "cheaper", "pricing", "migration", "tradeoff"]) else 0
        score += 10 if any(word in text for word in ["builders", "developers", "founders", "students", "creators"]) else 0
        score -= 18 if any(word in text for word in ["click here", "must read", "viral", "follow me", "like and repost"]) else 0
        return self._bound(score)

    def _score_profile_follow_potential(self, text: str) -> int:
        score = 30
        score += 16 if any(word in text for word in ["india", "indian", "bengaluru", "rupees", "upi"]) else 0
        score += 14 if any(word in text for word in ["developer", "founder", "student", "creator", "buyer", "career"]) else 0
        score += 12 if any(word in text for word in ["practical", "workflow", "portfolio", "shipping", "distribution", "cost"]) else 0
        score += 8 if any(word in text for word in ["ai", "openai", "claude", "gemini", "agent", "api"]) else 0
        return self._bound(score)

    def _score_source_strength(self, sources: list[dict[str, Any]], confidence: float) -> int:
        score = round(confidence * 45)
        for source in sources:
            if source.get("source_type") in {"x_watchlist", "manual"}:
                score += 18
            username = str(source.get("author_username", "")).lower()
            if username in {"openai", "anthropicai", "googledeepmind", "karpathy", "sama", "andrewyng"}:
                score += 14
            metrics = source.get("public_metrics") or {}
            engagement = int(metrics.get("like_count", 0) or 0) + int(metrics.get("retweet_count", 0) or 0) * 2 + int(metrics.get("quote_count", 0) or 0) * 2
            if engagement >= 500:
                score += 12
        return self._bound(score)

    def _score_postability(self, opportunity: dict[str, Any]) -> int:
        angle = str(opportunity.get("post_angle", ""))
        title = str(opportunity.get("title", ""))
        score = 35
        score += 20 if 30 <= len(angle) <= 220 else 0
        score += 10 if 10 <= len(title) <= 90 else 0
        score -= self._generic_slop_penalty(angle)
        return self._bound(score)

    def _generic_slop_penalty(self, text: str) -> int:
        lower = text.lower()
        return min(45, sum(12 for phrase in GENERIC_SLOP_PHRASES if phrase in lower))

    def _hook_score(self, hook: str, opportunity: dict[str, Any]) -> int:
        score, _ = self.score_opportunity(opportunity)
        hook_lower = hook.lower()
        score += 8 if any(word in hook_lower for word in ["india", "indian", "building"]) else 0
        score += 6 if any(word in hook_lower for word in ["not", "quiet", "underrated", "watch"]) else 0
        score -= 10 if len(hook) > 125 else 0
        return self._bound(score)

    def _short_topic(self, opportunity: dict[str, Any]) -> str:
        title = str(opportunity.get("title", "this update"))
        return self._trim(title, 54)

    def _audience_label(self, mode: AudienceMode) -> str:
        labels = {
            AudienceMode.INDIA_FOUNDERS: "Indian founders",
            AudienceMode.INDIA_DEVELOPERS: "Indian developers",
            AudienceMode.INDIA_STUDENTS: "Indian students",
            AudienceMode.INDIAN_CREATORS: "Indian creators",
            AudienceMode.BUYERS: "buyers",
            AudienceMode.GENERAL_TECH: "builders",
        }
        return labels[mode]

    def _format_for_mode(self, mode: AudienceMode) -> str:
        formats = {
            AudienceMode.INDIA_FOUNDERS: "founder/business angle",
            AudienceMode.INDIA_DEVELOPERS: "developer takeaway",
            AudienceMode.INDIA_STUDENTS: "student/career angle",
            AudienceMode.INDIAN_CREATORS: "creator workflow angle",
            AudienceMode.BUYERS: "buyer angle",
            AudienceMode.GENERAL_TECH: "practical takeaway",
        }
        return formats[mode]

    def _why_mode_works(self, mode: AudienceMode) -> str:
        return f"Targets {self._audience_label(mode)} with a specific factual implication instead of generic hype."

    def _india_angle(self, opportunity: dict[str, Any]) -> str:
        category = opportunity.get("category", "tech")
        return f"For India, the {category} angle is adoption: price, distribution, trust, developer workflow, jobs, and whether smaller teams can act on it."

    def _mini_thread(self, opportunity: dict[str, Any]) -> list[str]:
        return [
            self._trim(f"1/ {opportunity.get('title', 'This tech signal')}"),
            self._trim(f"2/ Why now: {opportunity.get('why_now', '')}"),
            self._trim(f"3/ Takeaway: {opportunity.get('post_angle', '')}"),
        ]

    def _visual_idea(self, opportunity: dict[str, Any]) -> str:
        return f"Two-column card: old workflow vs new workflow for {opportunity.get('category', 'this topic')}."

    def _risk_score(self, opportunity: dict[str, Any]) -> int:
        text = self._opportunity_text(opportunity)
        risk = 12
        risk += 15 if any(word in text for word in ["rumor", "reportedly", "lawsuit", "layoff"]) else 0
        risk += self._generic_slop_penalty(text)
        return self._bound(risk)

    def _source_velocity_bonus(self, sources: list[dict[str, Any]]) -> int:
        bonus = 0
        for source in sources or []:
            if source.get("source_type") in {"x_watchlist", "web_reply_scout"}:
                bonus += 4
        return min(8, bonus)

    def _algorithm_distribution_bonus(self, opportunity: dict[str, Any]) -> int:
        text = self._opportunity_text(opportunity)
        bonus = 0
        bonus += 3 if self._score_engagement_probability(text) >= 60 else 0
        bonus += 3 if self._score_profile_follow_potential(text) >= 60 else 0
        bonus += 2 if self._risk_score(opportunity) <= 25 else 0
        return bonus

    def _trim(self, value: str, limit: int = 260) -> str:
        clean = " ".join(value.split())
        if len(clean) <= limit:
            return clean
        return clean[: limit - 1].rstrip() + "..."

    def _bound(self, value: int | float) -> int:
        return max(1, min(100, round(value)))
