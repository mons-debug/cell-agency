"""
Cell Agency — Autonomy Engine
================================
The system becomes proactive — prepares work without being asked.

Governance rules:
    - manual > autonomous: manual commands always override
    - Confidence ≥ 0.75: auto-submit to approval queue
    - Confidence < 0.75: save draft to memory/outputs/ for manual review
    - ALL autonomous outputs enter approval queue — never auto-execute

Schedules (run via HEARTBEAT or cron):
    Daily    08:00 Morocco — daily_analysis() for each active client
    Weekly   Mon 09:00    — weekly_strategy_update(), content_gap_detection()
    Monthly  1st 09:00    — campaign_opportunity_detection()

Usage:
    from core.autonomy_engine import load_autonomy_engine

    engine = load_autonomy_engine()
    result = engine.daily_analysis("refine")
    result = engine.weekly_strategy_update("refine")
    result = engine.content_gap_detection("refine")
    result = engine.campaign_opportunity_detection("refine")
    engine.run_scheduled("daily")    # runs all daily tasks for all active clients
"""

from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from core.paths import get_agency_dir

AGENCY_DIR   = get_agency_dir()
CLIENTS_DIR  = AGENCY_DIR / "clients"
OUTPUTS_DIR  = AGENCY_DIR / "memory" / "outputs"
CONFIDENCE_THRESHOLD = 0.75


class AutonomyEngine:
    """
    Runs periodic intelligence tasks and submits results to the approval queue.

    All autonomous outputs are tagged with trigger_source="autonomous" and
    go through the approval engine before any content is executed.
    """

    def __init__(self) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def daily_analysis(self, client_id: str) -> dict:
        """
        Run daily performance analysis for a client.

        Steps:
          1. Call learning_server.daily_analysis() for performance insights
          2. Call learning_server.detect_content_gaps() for missing content
          3. Estimate confidence from data availability
          4. If conf ≥ 0.75: submit to approval queue as content recommendations
          5. If conf < 0.75: save draft to memory/outputs/

        Returns:
            Dict with analysis, gaps, confidence, approval_task_id (if submitted)
        """
        sys_path_insert()

        # Step 1: performance analysis
        analysis  = self._run_daily_analysis(client_id)
        # Step 2: content gaps
        gaps      = self._run_gap_detection(client_id)
        # Step 3: estimate confidence
        confidence = self._estimate_confidence(analysis, "daily_analysis")

        result = {
            "type":        "daily_analysis",
            "client_id":   client_id,
            "date":        date.today().isoformat(),
            "analysis":    analysis,
            "content_gaps": gaps,
            "confidence":  confidence,
            "trigger_source": "autonomous",
        }

        # Step 4/5: route based on confidence
        if confidence >= CONFIDENCE_THRESHOLD:
            task_id = self._submit_to_approval(
                action="daily_analysis_recommendations",
                client_id=client_id,
                draft_output=result,
                confidence=confidence,
            )
            result["approval_task_id"] = task_id
            result["routed_to"] = "approval_queue"
        else:
            path = self._save_draft(client_id, "daily_analysis", result)
            result["draft_path"] = str(path)
            result["routed_to"] = "drafts"

        return result

    def weekly_strategy_update(self, client_id: str) -> dict:
        """
        Run weekly strategy optimization and generate recommendations.

        Steps:
          1. Call learning_server.weekly_optimization()
          2. Generate content plan recommendation for next week
          3. Submit high-confidence items to approval queue

        Returns:
            Dict with weekly report, recommendations, confidence, routing info
        """
        sys_path_insert()

        weekly   = self._run_weekly_optimization(client_id)
        confidence = self._estimate_confidence(weekly, "weekly_optimization")

        result = {
            "type":        "weekly_strategy_update",
            "client_id":   client_id,
            "week":        date.today().isoformat(),
            "weekly_report": weekly,
            "confidence":  confidence,
            "trigger_source": "autonomous",
        }

        if confidence >= CONFIDENCE_THRESHOLD:
            task_id = self._submit_to_approval(
                action="weekly_strategy_recommendations",
                client_id=client_id,
                draft_output=result,
                confidence=confidence,
            )
            result["approval_task_id"] = task_id
            result["routed_to"] = "approval_queue"
        else:
            path = self._save_draft(client_id, "weekly_strategy", result)
            result["draft_path"] = str(path)
            result["routed_to"] = "drafts"

        return result

    def content_gap_detection(self, client_id: str) -> dict:
        """
        Detect content gaps and generate recommended post ideas.

        Steps:
          1. Detect gaps in calendar + service coverage
          2. Generate specific post recommendations per gap
          3. Submit to approval if confidence ≥ 0.75

        Returns:
            Dict with gaps, recommended posts, confidence, routing info
        """
        sys_path_insert()

        gaps       = self._run_gap_detection(client_id)
        confidence = self._estimate_confidence(gaps, "gap_detection")

        result = {
            "type":        "content_gap_detection",
            "client_id":   client_id,
            "date":        date.today().isoformat(),
            "gaps":        gaps,
            "confidence":  confidence,
            "trigger_source": "autonomous",
        }

        if confidence >= CONFIDENCE_THRESHOLD:
            task_id = self._submit_to_approval(
                action="content_gap_recommendations",
                client_id=client_id,
                draft_output=result,
                confidence=confidence,
            )
            result["approval_task_id"] = task_id
            result["routed_to"] = "approval_queue"
        else:
            path = self._save_draft(client_id, "content_gaps", result)
            result["draft_path"] = str(path)
            result["routed_to"] = "drafts"

        return result

    def campaign_opportunity_detection(self, client_id: str) -> dict:
        """
        Detect upcoming campaign opportunities (holidays, seasons, local events).

        Returns:
            Dict with opportunities, confidence, routing info
        """
        sys_path_insert()

        brand    = self._load_brandkit(client_id)
        industry = brand.get("industry", "beauty")
        location = brand.get("location", "Tanger, Morocco")

        opportunities = self._detect_opportunities(client_id, industry, location)
        confidence    = 0.70  # Campaign detection is always reviewed

        result = {
            "type":          "campaign_opportunity_detection",
            "client_id":     client_id,
            "date":          date.today().isoformat(),
            "opportunities": opportunities,
            "confidence":    confidence,
            "trigger_source": "autonomous",
        }

        # Campaign opportunities always below threshold → saved as draft for manual review
        path = self._save_draft(client_id, "campaign_opportunities", result)
        result["draft_path"] = str(path)
        result["routed_to"]  = "drafts"

        return result

    def run_scheduled(self, schedule_name: str, client_ids: list[str] = None) -> dict:
        """
        Run a named schedule batch for all (or specified) active clients.

        schedule_name:
            "daily"   → daily_analysis() for each client
            "weekly"  → weekly_strategy_update() + content_gap_detection()
            "monthly" → campaign_opportunity_detection()

        Args:
            schedule_name: "daily" | "weekly" | "monthly"
            client_ids:    Override clients (default = all active clients)

        Returns:
            Dict with results per client
        """
        clients = client_ids or self._get_active_clients()
        results = {}

        for cid in clients:
            try:
                if schedule_name == "daily":
                    results[cid] = self.daily_analysis(cid)
                elif schedule_name == "weekly":
                    results[cid] = {
                        "strategy": self.weekly_strategy_update(cid),
                        "gaps":     self.content_gap_detection(cid),
                    }
                elif schedule_name == "monthly":
                    results[cid] = self.campaign_opportunity_detection(cid)
                else:
                    results[cid] = {"error": f"Unknown schedule: {schedule_name}"}
            except Exception as e:
                results[cid] = {"error": str(e)}

        return {
            "schedule":    schedule_name,
            "ran_at":      datetime.now().isoformat(),
            "clients":     clients,
            "results":     results,
        }

    def list_drafts(self, client_id: str = "") -> list[dict]:
        """
        List autonomous drafts saved to memory/outputs/ (below confidence threshold).

        Args:
            client_id: Filter by client (empty = all)

        Returns:
            List of draft metadata dicts sorted by most recent first
        """
        drafts = []
        pattern = f"{client_id}_*.json" if client_id else "*.json"

        for path in sorted(OUTPUTS_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                drafts.append({
                    "file":       path.name,
                    "type":       data.get("type", "unknown"),
                    "client_id":  data.get("client_id", ""),
                    "date":       data.get("date", ""),
                    "confidence": data.get("confidence", 0),
                    "routed_to":  data.get("routed_to", ""),
                    "path":       str(path),
                })
            except Exception:
                continue

        return drafts

    # ── Private: tool calls ───────────────────────────────────────────────────

    def _run_daily_analysis(self, client_id: str) -> dict:
        try:
            from learning_server import daily_analysis
            raw = daily_analysis(client_id)
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception as e:
            return {"error": str(e), "client_id": client_id}

    def _run_weekly_optimization(self, client_id: str) -> dict:
        try:
            from learning_server import weekly_optimization
            raw = weekly_optimization(client_id)
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception as e:
            return {"error": str(e), "client_id": client_id}

    def _run_gap_detection(self, client_id: str) -> dict:
        try:
            from learning_server import detect_content_gaps
            raw = detect_content_gaps(client_id)
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception as e:
            return {"error": str(e), "client_id": client_id}

    def _detect_opportunities(self, client_id: str, industry: str, location: str) -> list:
        """Stub: detect seasonal/local campaign opportunities."""
        today = date.today()
        month = today.month

        # Basic seasonal opportunities for Morocco beauty clinic
        seasonal = {
            1:  ["New Year glow-up promotion", "January reset skincare campaign"],
            2:  ["Valentine's Day couples packages", "February skin care event"],
            3:  ["Spring renewal skincare launch", "Ramadan preparation"],
            4:  ["Ramadan special offers", "Spring beauty event"],
            5:  ["Eid Al-Fitr beauty packages", "Mother's Day promotions"],
            6:  ["Summer body prep campaign", "Beach-ready laser packages"],
            7:  ["Midsummer skin treatments", "Holiday glow campaign"],
            8:  ["Back-to-school confidence boost", "Late summer renewal"],
            9:  ["September fresh start packages", "Autumn skin transition"],
            10: ["Autumn skin restoration", "Pre-wedding season packages"],
            11: ["Year-end transformation", "Black Friday beauty offers"],
            12: ["Holiday party glow packages", "Year-end review + new year prep"],
        }

        base = seasonal.get(month, [])
        return [{"opportunity": opp, "month": month, "priority": "medium"} for opp in base]

    # ── Private: routing ──────────────────────────────────────────────────────

    def _submit_to_approval(
        self,
        action: str,
        client_id: str,
        draft_output: dict,
        confidence: float,
    ) -> str:
        """Submit autonomous output to the approval engine."""
        try:
            from core.approval_engine import load_approval_engine
            engine  = load_approval_engine()
            task_id = engine.submit(
                action=action,
                client_id=client_id,
                draft_output=draft_output,
                confidence=confidence,
                trigger_source="autonomous",
                notes=f"Autonomous {action} — generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )
            return task_id
        except Exception as e:
            return f"submit_error: {e}"

    def _save_draft(self, client_id: str, task_type: str, data: dict) -> Path:
        """Save low-confidence autonomous output to memory/outputs/."""
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{client_id}_{task_type}_{date.today().isoformat()}.json"
        path = OUTPUTS_DIR / filename
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    # ── Private: helpers ──────────────────────────────────────────────────────

    def _estimate_confidence(self, data: dict, task_type: str) -> float:
        """
        Estimate confidence based on data availability and quality.
        """
        if "error" in data:
            return 0.30

        # Check for key signals in the data
        has_insights = bool(
            data.get("insights") or
            data.get("content_opportunities") or
            data.get("recommended_next_5_posts") or
            data.get("next_week_priorities") or
            data.get("summary")
        )
        has_data = bool(
            data.get("top_wins") or
            data.get("content_strategy_updates") or
            data.get("underrepresented_themes") or
            data.get("action_items")
        )

        if has_insights and has_data:
            return 0.82
        elif has_insights or has_data:
            return 0.70
        else:
            return 0.55

    def _load_brandkit(self, client_id: str) -> dict:
        kit = CLIENTS_DIR / client_id / "brandkit.json"
        if kit.exists():
            try:
                return json.loads(kit.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _get_active_clients(self) -> list[str]:
        """Return list of clients with brandkit.json (active clients)."""
        if not CLIENTS_DIR.exists():
            return []
        return [
            d.name for d in CLIENTS_DIR.iterdir()
            if d.is_dir() and (d / "brandkit.json").exists()
        ]


# ── Helpers ────────────────────────────────────────────────────────────────────

def sys_path_insert() -> None:
    import sys
    for p in [str(AGENCY_DIR), str(AGENCY_DIR / "mcp-servers"), str(AGENCY_DIR / "tools")]:
        if p not in sys.path:
            sys.path.insert(0, p)


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine: AutonomyEngine | None = None


def load_autonomy_engine() -> AutonomyEngine:
    """Return singleton AutonomyEngine."""
    global _engine
    if _engine is None:
        _engine = AutonomyEngine()
    return _engine
