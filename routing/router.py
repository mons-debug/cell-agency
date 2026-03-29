"""
Cell Agency — Smart Routing Engine
===================================
Classifies incoming Telegram messages into the correct skill → crew → task → agent.

Priority order:
  1. Deterministic keyword/regex matching against routing_table.yaml
  2. LLM fallback (Claude Haiku) for ambiguous or unmatched messages
  3. Hard fallback to Nadia if everything fails

Usage:
    from routing import load_router

    router = load_router()
    decision = router.classify("write a caption for refine clinic about spring offer")
    print(decision.skill, decision.crew, decision.task, decision.confidence)
"""

from __future__ import annotations

import os
import re
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

ROUTING_TABLE_PATH = Path(__file__).parent / "routing_table.yaml"
KEYWORD_MATCH_WEIGHT = 1.0       # score per exact keyword match
REGEX_MATCH_WEIGHT = 0.8         # score per regex match
MIN_KEYWORD_SCORE = 0.2          # minimum normalised score to consider a route
LLM_FALLBACK_MODEL = "claude-haiku-4-5-20251001"


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RouteDecision:
    """Result of routing a message to a crew/task/agent."""
    skill: str
    crew: str
    task: str
    agent: str
    confidence: float                       # 0.0 – 1.0
    matched_triggers: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    approval_required: bool = False
    method: str = "keyword"                 # "keyword" | "llm" | "fallback"
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "crew": self.crew,
            "task": self.task,
            "agent": self.agent,
            "confidence": round(self.confidence, 3),
            "matched_triggers": self.matched_triggers,
            "missing_inputs": self.missing_inputs,
            "approval_required": self.approval_required,
            "method": self.method,
            "context": self.context,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ── Router ────────────────────────────────────────────────────────────────────

class SmartRouter:
    """
    Hybrid router: deterministic keyword/regex first, LLM fallback second.

    Steps:
      1. Normalise the message (lowercase, strip punctuation)
      2. Score every route in routing_table.yaml
      3. If top score ≥ route's confidence_floor → return deterministic decision
      4. Else → call LLM with structured prompt to pick the best route
      5. Fallback → Nadia (management crew)
    """

    def __init__(self, routing_table_path: Path = ROUTING_TABLE_PATH):
        self._table_path = routing_table_path
        self._routes: list[dict] = []
        self._fallback: dict = {}
        self._reload_table()

    # ── Public API ────────────────────────────────────────────────────────────

    def classify(
        self,
        message: str,
        context: Optional[dict] = None,
        use_llm_fallback: bool = True,
    ) -> RouteDecision:
        """
        Route a message to the best skill/crew/task/agent.

        Args:
            message: Raw text message from Moncef (Telegram)
            context: Optional additional context (client_id, etc.)
            use_llm_fallback: Whether to call LLM when keywords don't match

        Returns:
            RouteDecision with full routing info
        """
        ctx = context or {}
        normalised = self._normalise(message)

        # Step 1: Score all routes by keyword/regex
        scored = self._score_routes(normalised)

        if scored:
            top_route, top_score, matched = scored[0]
            confidence_floor = top_route.get("confidence_floor", 0.3)

            if top_score >= confidence_floor:
                return self._make_decision(
                    route=top_route,
                    confidence=min(top_score, 1.0),
                    matched=matched,
                    ctx=ctx,
                    method="keyword",
                )

        # Step 2: LLM fallback
        if use_llm_fallback:
            try:
                return self._llm_classify(message, ctx)
            except Exception as e:
                logger.warning(f"LLM routing fallback failed: {e}")

        # Step 3: Hard fallback
        return self._hard_fallback(ctx)

    def explain(self, message: str) -> list[dict]:
        """
        Return top-5 route scores for a message (debugging / transparency).

        Returns:
            List of dicts: [{skill, crew, task, score, matched_triggers}, ...]
        """
        normalised = self._normalise(message)
        scored = self._score_routes(normalised)
        return [
            {
                "skill": r["skill"],
                "crew": r["crew"],
                "task": r["task"],
                "agent": r["agent"],
                "score": round(s, 3),
                "matched_triggers": m,
            }
            for r, s, m in scored[:5]
        ]

    def reload(self) -> None:
        """Hot-reload the routing table from disk (no restart needed)."""
        self._reload_table()
        logger.info(f"Routing table reloaded: {len(self._routes)} routes")

    # ── Internals ─────────────────────────────────────────────────────────────

    def _reload_table(self) -> None:
        with open(self._table_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Sort by priority descending (checked first)
        self._routes = sorted(
            data.get("routes", []),
            key=lambda r: r.get("priority", 50),
            reverse=True,
        )
        self._fallback = data.get("fallback", {
            "crew": "management",
            "task": "route_task",
            "agent": "nadia",
        })

    def _normalise(self, text: str) -> str:
        """Lowercase, collapse whitespace, remove excess punctuation."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _score_routes(
        self, normalised_message: str
    ) -> list[tuple[dict, float, list[str]]]:
        """
        Score every route and return sorted (highest first).

        Returns:
            List of (route_dict, normalised_score, matched_triggers)
        """
        results = []

        for route in self._routes:
            score = 0.0
            matched: list[str] = []
            triggers = route.get("triggers", {})

            # Keyword matching
            for kw in triggers.get("keywords", []):
                kw_norm = self._normalise(kw)
                if kw_norm in normalised_message:
                    score += KEYWORD_MATCH_WEIGHT
                    matched.append(kw)
                elif any(word in normalised_message for word in kw_norm.split()
                         if len(word) > 4):          # ignore short words like "a", "for"
                    # Partial single-word match — very low weight
                    score += KEYWORD_MATCH_WEIGHT * 0.12
                    matched.append(f"~{kw}")

            # Regex matching
            for pattern in triggers.get("regex", []):
                try:
                    if re.search(pattern, normalised_message):
                        score += REGEX_MATCH_WEIGHT
                        matched.append(f"/{pattern}/")
                except re.error as e:
                    logger.warning(f"Bad regex in routing table '{pattern}': {e}")

            if score > 0:
                # Confidence = tanh-like curve on raw score:
                #   1 exact keyword match  → ~0.5
                #   2 exact keyword matches → ~0.75
                #   3+ matches             → ~0.9+
                # This avoids penalising routes with many trigger phrases.
                normalised_score = min(score * 0.45, 1.0)
                results.append((route, normalised_score, matched))

        # Sort descending by score, then by priority as tiebreaker
        results.sort(key=lambda x: (x[1], x[0].get("priority", 50)), reverse=True)
        return results

    def _make_decision(
        self,
        route: dict,
        confidence: float,
        matched: list[str],
        ctx: dict,
        method: str,
    ) -> RouteDecision:
        """Build a RouteDecision from a matched route."""
        required = route.get("required_inputs", [])
        missing = [inp for inp in required if inp not in ctx]

        return RouteDecision(
            skill=route["skill"],
            crew=route["crew"],
            task=route["task"],
            agent=route["agent"],
            confidence=confidence,
            matched_triggers=matched,
            missing_inputs=missing,
            approval_required=route.get("approval_required", False),
            method=method,
            context=ctx,
        )

    def _llm_classify(self, message: str, ctx: dict) -> RouteDecision:
        """
        Use Claude Haiku to classify the message when keyword matching fails.
        Returns a RouteDecision with method="llm".
        """
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed — cannot use LLM fallback")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set — cannot use LLM fallback")

        # Build a compact route menu for the LLM to choose from
        route_menu = []
        for r in self._routes:
            route_menu.append({
                "skill": r["skill"],
                "crew": r["crew"],
                "task": r["task"],
                "agent": r["agent"],
                "keywords": r.get("triggers", {}).get("keywords", [])[:5],
            })

        # Deduplicate (same skill/task can appear multiple times for different triggers)
        seen = set()
        unique_routes = []
        for r in route_menu:
            key = f"{r['skill']}:{r['task']}"
            if key not in seen:
                seen.add(key)
                unique_routes.append(r)

        system_prompt = (
            "You are the routing engine for Cell Agency, an AI digital marketing agency. "
            "Your job is to classify incoming messages from the owner (Moncef) and route them "
            "to the correct skill, crew, task, and agent.\n\n"
            "Respond ONLY with valid JSON matching this schema:\n"
            '{"skill": "...", "crew": "...", "task": "...", "agent": "...", "confidence": 0.0}'
        )

        user_prompt = (
            f"Message: {message}\n\n"
            f"Available routes (skill → crew → task → agent):\n"
            f"{json.dumps(unique_routes, ensure_ascii=False, indent=2)}\n\n"
            "Pick the BEST matching route. If nothing fits well, use:\n"
            '{"skill": "management", "crew": "management", '
            '"task": "route_task", "agent": "nadia", "confidence": 0.3}'
        )

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=LLM_FALLBACK_MODEL,
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()

        # Strip markdown code blocks if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        parsed = json.loads(raw)

        # Find the matching route for full details
        matched_route = next(
            (r for r in self._routes
             if r["skill"] == parsed.get("skill") and r["task"] == parsed.get("task")),
            None,
        )

        if matched_route:
            return self._make_decision(
                route=matched_route,
                confidence=float(parsed.get("confidence", 0.5)),
                matched=["[llm]"],
                ctx=ctx,
                method="llm",
            )

        # LLM returned something not in our table — use parsed values directly
        required = []
        missing = [inp for inp in required if inp not in ctx]
        return RouteDecision(
            skill=parsed.get("skill", "management"),
            crew=parsed.get("crew", "management"),
            task=parsed.get("task", "route_task"),
            agent=parsed.get("agent", "nadia"),
            confidence=float(parsed.get("confidence", 0.4)),
            matched_triggers=["[llm]"],
            missing_inputs=missing,
            approval_required=False,
            method="llm",
            context=ctx,
        )

    def _hard_fallback(self, ctx: dict) -> RouteDecision:
        """Last-resort fallback — send to Nadia."""
        return RouteDecision(
            skill=self._fallback.get("skill", "management"),
            crew=self._fallback.get("crew", "management"),
            task=self._fallback.get("task", "route_task"),
            agent=self._fallback.get("agent", "nadia"),
            confidence=0.1,
            matched_triggers=[],
            missing_inputs=[],
            approval_required=False,
            method="fallback",
            context=ctx,
        )


# ── Convenience loader ────────────────────────────────────────────────────────

_router_instance: Optional[SmartRouter] = None


def load_router(routing_table_path: Path = ROUTING_TABLE_PATH) -> SmartRouter:
    """
    Return a singleton SmartRouter instance (lazy-loaded).
    Call router.reload() to hot-reload the routing table without restarting.
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = SmartRouter(routing_table_path)
    return _router_instance
