from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import Settings
from app.ctr_optimizer import AudienceMode, CTROptimizer, X_ALGORITHM_PRINCIPLES


class TrendWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def find_opportunities(
        self,
        *,
        topic_query: str,
        source_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not source_items:
            return []

        if self.client is None:
            return self._fallback_opportunities(topic_query, source_items)

        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=self._opportunity_prompt(topic_query, source_items),
        )
        payload = self._extract_json(response.output_text)
        opportunities = payload.get("opportunities", [])
        if not isinstance(opportunities, list):
            raise RuntimeError("The model returned opportunities in an unexpected format.")
        return opportunities[:8]

    def draft_post(
        self,
        *,
        opportunity: dict[str, Any],
        source_items: list[dict[str, Any]],
        style: str = "",
    ) -> dict[str, str]:
        if self.client is None:
            text = (
                f"{opportunity['title']}: {opportunity['post_angle']} "
                "This feels worth watching as the next product cycle unfolds."
            )
            return {
                "draft": self._trim_post(text),
                "notes": "Fallback draft because OPENAI_API_KEY is not configured.",
            }

        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=self._draft_prompt(opportunity, source_items, style),
        )
        payload = self._extract_json(response.output_text)
        draft = self._trim_post(payload.get("draft", "").strip())
        notes = payload.get("notes", "").strip()
        if not draft:
            raise RuntimeError("The model did not return a usable draft.")
        return {"draft": draft, "notes": notes}

    def build_content_pack(
        self,
        *,
        opportunities: list[dict[str, Any]],
        style: str = "",
    ) -> dict[str, Any]:
        if not opportunities:
            return {"posts": [], "summary": "No opportunities available."}

        if self.client is None:
            return self._fallback_content_pack(opportunities)

        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=self._content_pack_prompt(opportunities, style),
        )
        payload = self._extract_json(response.output_text)
        posts = payload.get("posts", [])
        if not isinstance(posts, list):
            raise RuntimeError("The model returned posts in an unexpected format.")
        return {
            "summary": payload.get("summary", ""),
            "posts": posts[:12],
        }

    def build_ctr_pack(
        self,
        *,
        opportunities: list[dict[str, Any]],
        style: str = "",
    ) -> dict[str, Any]:
        if not opportunities:
            return {"summary": "No opportunities available.", "items": []}

        if self.client is None:
            return self._fallback_ctr_pack(opportunities)

        optimizer = CTROptimizer(min_viral_score=60)
        opportunities = optimizer.rank_opportunities(opportunities, limit=12)
        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=self._ctr_pack_prompt(opportunities, style),
        )
        payload = self._extract_json(response.output_text)
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise RuntimeError("The model returned CTR items in an unexpected format.")
        return {
            "summary": payload.get("summary", ""),
            "items": items[:12],
        }

    def _fallback_opportunities(
        self,
        topic_query: str,
        source_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        opportunities: list[dict[str, Any]] = []
        for item in source_items[:3]:
            metrics = item["public_metrics"]
            title = self._trim_text(item["text"], 82)
            opportunities.append(
                {
                    "title": title,
                    "category": self._infer_category(item["text"]),
                    "why_now": (
                        f"This post is gaining visible engagement under your tracked query: "
                        f"{topic_query}."
                    ),
                    "post_angle": "Add your view on why this matters for builders and product teams.",
                    "confidence": 0.55,
                    "source_ids": [item["id"]],
                    "score_hint": (
                        metrics.get("like_count", 0)
                        + metrics.get("retweet_count", 0) * 2
                        + metrics.get("quote_count", 0) * 2
                    ),
                }
            )
        return opportunities

    def _opportunity_prompt(
        self,
        topic_query: str,
        source_items: list[dict[str, Any]],
    ) -> str:
        lines = []
        for idx, item in enumerate(source_items, start=1):
            metrics = item["public_metrics"]
            source_type = item.get("source_type", "x")
            author = item.get("author_username", item.get("author_name", "unknown"))
            lines.append(
                (
                    f"{idx}. id={item['id']} | source={source_type} | author={author} | "
                    f"created_at={item['created_at']} | likes={metrics.get('like_count', 0)} | "
                    f"reposts={metrics.get('retweet_count', 0)} | quotes={metrics.get('quote_count', 0)} | "
                    f"url={item['url']}\n"
                    f"text: {item['text']}"
                )
            )

        joined_sources = "\n\n".join(lines)
        return (
            "You are a tech trend scout for someone who wants to post thoughtful X content.\n"
            "Review recent X posts and web feed items, then identify potentially new or accelerating topics worth posting about.\n"
            "If source=x_watchlist, treat it as a signal from a tracked AI account. Look for narratives, debates, research shifts, model releases, benchmark drama, agent/tooling ideas, and opinions that can become original posts.\n"
            "If source=manual, treat it as a user-provided signal from a tweet, post, article, or observation. Extract multiple possible angles from it and make them publishable.\n"
            "Do not simply summarize the tracked account. Turn the signal into a fresh angle the user can post, with attribution only when it genuinely helps credibility.\n"
            "Prefer concrete product shifts, launches, device rumors, platform moves, health/wearable changes, startup moves, chips, NVIDIA AI infrastructure, developer tools, job-market shifts, layoffs, hiring changes, and visible debates.\n"
            "For NVIDIA topics, look for specific angles around GTC/Computex, Jensen Huang, AI factories, RTX Spark/AI PCs, Vera, Rubin, Blackwell, NVLink, Spectrum, DGX, CUDA, inference costs, developer workflows, and India cloud/startup implications.\n"
            "For layoffs and job-market content, avoid fearmongering. Focus on useful angles: skills, resilience, hiring signals, AI impact, market cycles, student strategy, and how builders can become harder to ignore.\n"
            "Return a diverse set of categories when evidence supports it: Apple, Samsung, Wearables, Whoop, Smartwatches, Health tech, Consumer devices, NVIDIA, Chips, AI infrastructure, Startups, Developer tools, AI, Claude, Codex, OpenAI, Layoffs, Careers, Hiring, Gaming, EVs, AR/VR.\n"
            "Each opportunity must include a category field naming what it is about.\n"
            "Avoid generic evergreen topics. Do not invent facts beyond the source posts.\n"
            "Return valid JSON only with this exact shape:\n"
            '{"opportunities":[{"title":"short topic","category":"Apple/Samsung/Wearables/etc",'
            '"why_now":"why it may be timely",'
            '"post_angle":"the angle the user could take","confidence":0.0,'
            '"source_ids":["source id or url"]}]}\n\n'
            f"Tracked query:\n{topic_query}\n\n"
            f"Source posts:\n{joined_sources}"
        )

    def _draft_prompt(
        self,
        opportunity: dict[str, Any],
        source_items: list[dict[str, Any]],
        style: str,
    ) -> str:
        lines = []
        for item in source_items:
            source_type = item.get("source_type", "x")
            author = item.get("author_username", item.get("author_name", "unknown"))
            lines.append(
                f"- {source_type} | {author} ({item['url']}): {item['text']}"
            )
        joined_sources = "\n".join(lines)
        style_line = style.strip() or "factual, statement-led, concrete, practical, no hype"
        return (
            "Write one X post based on this opportunity.\n"
            "Make the subject clear in the tweet: mention the specific lane when relevant, such as Apple, Samsung, Whoop, watches, health tech, wearables, NVIDIA, chips, AI infrastructure, startups, developer tools, AI, layoffs, hiring, or careers.\n"
            "Keep it under 260 characters. Do not copy source wording. Do not add fake specifics.\n"
            "Tone rules: write like a factual statement, not a hype post. Lead with what happened, what changed, or what the signal is. Avoid exaggerated claims, drama, rhetorical questions, and motivational language.\n"
            "Return valid JSON only with this exact shape:\n"
            '{"draft":"final post text","notes":"brief reason this angle works"}\n\n'
            f"Style:\n{style_line}\n\n"
            f"Opportunity:\n{json.dumps(opportunity, ensure_ascii=True)}\n\n"
            f"Source posts:\n{joined_sources}"
        )

    def _content_pack_prompt(
        self,
        opportunities: list[dict[str, Any]],
        style: str,
    ) -> str:
        compact = []
        for opportunity in opportunities:
            compact.append(
                {
                    "id": opportunity["id"],
                    "category": opportunity.get("category", "General Tech"),
                    "title": opportunity["title"],
                    "why_now": opportunity["why_now"],
                    "post_angle": opportunity["post_angle"],
                    "confidence": opportunity["confidence"],
                    "viral_score": opportunity.get("viral_score"),
                    "score_breakdown": opportunity.get("score_breakdown", {}),
                    "sources": [
                        {
                            "title": source.get("title") or source.get("author_username"),
                            "url": source["url"],
                        }
                        for source in opportunity.get("sources", [])[:3]
                    ],
                }
            )
        style_line = style.strip() or "factual, statement-led, practical, high-signal"
        return (
            "Build a daily X content pack from these tech opportunities.\n"
            "Prioritize reach through clear facts, concrete implications, useful context, and specific category framing.\n"
            "Create variety across formats: fact summary, market signal, practical implication, India angle, explainer, poll, and mini-thread.\n"
            "Tone rules: statement-led, direct, factual, low-drama. Do not write hot takes, hype, rhetorical questions, or vague motivational posts.\n"
            "Do not invent facts beyond the opportunities and sources. Keep single posts under 260 characters.\n"
            "For poll options, use 2-4 short options. For threads, use exactly 3 posts.\n"
            "Return valid JSON only with this exact shape:\n"
            '{"summary":"one paragraph","posts":[{"rank":1,"opportunity_id":1,'
            '"category":"Apple","format":"market signal","hook":"short factual hook",'
            '"post":"single post text or first post","poll_options":["A","B"],'
            '"thread":["post 1","post 2","post 3"],"visual_idea":"simple visual idea",'
            '"why_it_can_work":"brief reach rationale"}]}\n\n'
            f"Style:\n{style_line}\n\n"
            f"Opportunities:\n{json.dumps(compact, ensure_ascii=True)}"
        )

    def _ctr_pack_prompt(
        self,
        opportunities: list[dict[str, Any]],
        style: str,
    ) -> str:
        compact = []
        for opportunity in opportunities:
            compact.append(
                {
                    "id": opportunity["id"],
                    "category": opportunity.get("category", "General Tech"),
                    "title": opportunity["title"],
                    "why_now": opportunity["why_now"],
                    "post_angle": opportunity["post_angle"],
                    "confidence": opportunity["confidence"],
                    "viral_score": opportunity.get("viral_score"),
                    "score_breakdown": opportunity.get("score_breakdown", {}),
                    "sources": [
                        {
                            "title": source.get("title") or source.get("author_username"),
                            "url": source["url"],
                        }
                        for source in opportunity.get("sources", [])[:3]
                    ],
                }
            )
        style_line = style.strip() or "factual, statement-led, concrete, practical, high CTR"
        algorithm_principles = "\n".join(f"- {principle}" for principle in X_ALGORITHM_PRINCIPLES)
        return (
            "Create a high-CTR and high-impression X optimization pack from these tech opportunities.\n"
            "Use this X algorithm model from the current developer-tooling cheat sheet: retrieve broad candidates -> rank -> filter -> serve. Phoenix/ranker-like scores reward likely replies, reposts, likes, profile clicks, follows, dwell time, saves/bookmarks, and creator-audience fit; selection filters can suppress spam, duplicates, unsafe posts, and low-quality bait.\n"
            f"X algorithm principles to apply:\n{algorithm_principles}\n"
            "First, respect the provided viral_score and score_breakdown, including engagement probability and profile follow potential. Prioritize high-scoring opportunities and ignore weak/generic ones unless they have a clear fresh angle.\n"
            "Goal: maximize scroll-stop, saves/bookmarks, profile clicks, follows, and reposts through concrete facts and useful implications, not clickbait or fake claims.\n"
            "Global tone rule: make posts sound like clear factual statements. Prefer 'X did Y, which signals Z' over jokes, hype, questions, or motivational framing.\n"
            "For each opportunity, generate and rank hook variants before choosing the final tweet.\n"
            "Use these audience modes explicitly: india_founders, india_developers, india_students. Each opportunity should have distinct ready-to-post tweets for those audiences when relevant.\n"
            "Apply a hard no-generic-slop filter: never use phrases like game-changer, revolutionary, AI is transforming, the future of, this could change everything, in today's fast-paced world, it remains to be seen, only time will tell, or unlocking new possibilities.\n"
            "For each opportunity, generate fully assembled, copy-paste-ready tweets. Do not make the user combine hooks and bodies manually.\n"
            "Compare the best X formats for each topic: fact summary, market signal, money/value implication, comparison, timeline/roadmap signal, practical takeaway, India implication, developer implication, and save-worthy checklist.\n"
            "Pick one winner as best_ready_to_post, then provide 5 finished tweet options with format labels, scores, and why each works.\n"
            "Also create an India-specific section for each topic: an india_angle, india_relevance_score, and 3 longer India-focused tweets for Indian tech audiences.\n"
            "India-focused tweets should connect the topic to Indian buyers, students, creators, founders, developers, startups, pricing in rupees, UPI/fintech, Apple/Samsung buyers, wearables, health tech, jobs, or consumer behavior when relevant.\n"
            "Also generate 10 hooks, 3 single-post variants, 1 poll, 1 mini-thread, 1 visual-card idea, and scores.\n"
            "Hooks should be specific and fact-led. Avoid vague hooks like 'This is interesting' and avoid question-led hooks unless the source itself is uncertain.\n"
            "Prefer posts that give a reason to follow the account: repeated niche expertise, practical frameworks, Indian tech context, developer/founder judgment, or a useful saved reference.\n"
            "Every ready-to-post tweet and single post variant must be under 260 characters. India-focused tweets should be 220-275 characters. Poll options must be 2-4 short choices. Mini-threads must have exactly 3 posts.\n"
            "Scores are 1-100: ctr_score, impression_score, risk_score. Lower risk is better.\n"
            "Return valid JSON only with this exact shape:\n"
            '{"summary":"one paragraph","items":[{"opportunity_id":1,"category":"Apple",'
            '"title":"topic","best_angle":"angle","best_hook":"hook",'
            '"best_ready_to_post":"complete tweet ready to paste",'
            '"format_comparison":[{"format":"fact summary","score":92,"tweet":"complete tweet",'
            '"why_it_works":"short reason"}],'
            '"ready_to_post_tweets":[{"rank":1,"format":"money/value","score":95,'
            '"tweet":"complete tweet","why_it_works":"short reason"}],'
            '"india_angle":"why this matters for India tech audience",'
            '"india_relevance_score":85,'
            '"india_long_tweets":[{"rank":1,"tweet":"longer India-focused complete tweet",'
            '"why_it_works":"short reason"}],'
            '"hooks":["hook1"],"post_variants":["v1","v2","v3"],'
            '"poll":{"question":"question","options":["A","B"]},'
            '"mini_thread":["p1","p2","p3"],'
            '"visual_card_idea":"visual idea","ctr_score":90,"impression_score":85,'
            '"risk_score":20,"why_this_can_work":"reason"}]}\n\n'
            f"Style:\n{style_line}\n\n"
            f"Opportunities:\n{json.dumps(compact, ensure_ascii=True)}"
        )

    def _fallback_ctr_pack(self, opportunities: list[dict[str, Any]]) -> dict[str, Any]:
        optimizer = CTROptimizer(min_viral_score=60)
        items = optimizer.build_ctr_items(
            opportunities,
            audience_modes=[
                AudienceMode.INDIA_FOUNDERS,
                AudienceMode.INDIA_DEVELOPERS,
                AudienceMode.INDIA_STUDENTS,
            ],
            limit=8,
        )
        return {
            "summary": "CTR-optimized fallback pack using viral scoring, ranked hooks, no-slop filtering, and India audience modes.",
            "items": items,
        }

    def _fallback_content_pack(self, opportunities: list[dict[str, Any]]) -> dict[str, Any]:
        posts = []
        for index, opportunity in enumerate(opportunities[:8], start=1):
            category = opportunity.get("category", "General Tech")
            posts.append(
                {
                    "rank": index,
                    "opportunity_id": opportunity["id"],
                    "category": category,
                    "format": "fact summary",
                    "hook": opportunity["title"],
                    "post": self._trim_post(
                        f"{category}: {opportunity['post_angle']} Worth watching because "
                        f"{opportunity['why_now']}"
                    ),
                    "poll_options": [],
                    "thread": [],
                    "visual_idea": f"Simple card: {category} + one bold takeaway",
                    "why_it_can_work": "Fallback pack generated without OpenAI.",
                }
            )
        return {"summary": "Fallback content pack.", "posts": posts}

    def _extract_json(self, text: str) -> dict[str, Any]:
        candidate = text.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise RuntimeError(f"Model output was not valid JSON: {candidate}") from None
            return json.loads(candidate[start : end + 1])

    def _trim_post(self, value: str, limit: int = 260) -> str:
        clean = " ".join(value.split())
        if len(clean) <= limit:
            return clean
        return clean[: limit - 1].rstrip() + "..."

    def _trim_text(self, value: str, limit: int) -> str:
        clean = " ".join(value.split())
        if len(clean) <= limit:
            return clean
        return clean[: limit - 1].rstrip() + "..."

    def _infer_category(self, value: str) -> str:
        text = value.lower()
        categories = [
            ("NVIDIA", ["nvidia", "jensen huang", "gtc taipei", "rtx spark", "vera", "rubin", "blackwell", "nvlink", "dgx", "cuda"]),
            ("Whoop", ["whoop"]),
            ("Samsung", ["samsung", "galaxy"]),
            ("Apple", ["apple", "apple intelligence", "ios", "macos", "watchos", "iphone", "ipad", "apple watch"]),
            ("Smartwatches", ["smartwatch", "smart watch", "watch", "wear os", "galaxy watch", "apple watch"]),
            ("Wearables", ["wearable", "wearables", "ring", "oura", "fitness tracker"]),
            ("Health tech", ["health", "fitness", "sleep", "recovery", "heart rate", "glucose", "medical", "wellness"]),
            ("Consumer devices", ["phone", "smartphone", "device", "hardware", "tablet", "laptop", "camera", "headphones", "earbuds"]),
            ("Chips", ["chip", "gpu", "semiconductor", "snapdragon", "exynos", "tsmc"]),
            ("AR/VR", ["vision pro", "vr", "ar", "mixed reality", "headset"]),
            ("Gaming", ["gaming", "xbox", "playstation", "nintendo", "steam"]),
            ("Claude", ["claude", "anthropic"]),
            ("Codex", ["codex"]),
            ("OpenAI", ["openai", "chatgpt", "gpt"]),
            ("AI", ["ai", "artificial intelligence", "llm", "model"]),
            ("AI agents", ["agent", "agents"]),
            ("AI infrastructure", ["chip", "gpu", "data center", "infrastructure", "power"]),
            ("Developer tools", ["developer", "coding", "dev tool", "github"]),
            ("Layoffs", ["layoff", "layoffs", "laid off", "job cuts", "restructuring", "downsizing"]),
            ("Hiring", ["hiring", "jobs", "job market", "recruiting", "internship", "internships"]),
            ("Careers", ["career", "resume", "portfolio", "open source", "ship in public", "network"]),
            ("Startups", ["startup", "funding", "founder"]),
        ]
        for category, needles in categories:
            if any(needle in text for needle in needles):
                return category
        return "General Tech"
