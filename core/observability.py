"""
Cell Agency — Observability
============================
Full visibility into all system operations.

Provides structured logging for:
    - Workflow state transitions
    - Agent actions (tool calls, decisions)
    - Tool call performance and success rates
    - System health dashboard

Log storage:
    logs/workflow_logs/{workflow_id}.jsonl   — per-workflow event stream
    logs/agent_logs/{agent_id}.jsonl         — per-agent activity stream
    logs/tool_usage/{date}.jsonl             — tool call log (daily rotation)

Usage:
    from core.observability import get_observer

    obs = get_observer()
    obs.log_workflow_event(workflow_id, "state_changed", {"from": "running", "to": "completed"})
    obs.log_agent_action("content_agent", "generate_caption", inputs={}, outputs={}, duration_ms=1200)
    obs.log_tool_call("generate_caption", inputs={}, output="...", duration_ms=1200, success=True)
    report = obs.agency_dashboard()
"""

from __future__ import annotations

import json
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Optional

from core.paths import get_agency_dir

AGENCY_DIR   = get_agency_dir()
LOGS_DIR     = AGENCY_DIR / "logs"
WF_LOGS_DIR  = LOGS_DIR / "workflow_logs"
AG_LOGS_DIR  = LOGS_DIR / "agent_logs"
TL_LOGS_DIR  = LOGS_DIR / "tool_usage"


def _ensure_dirs() -> None:
    for d in [WF_LOGS_DIR, AG_LOGS_DIR, TL_LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, record: dict) -> None:
    """Append a JSON record to a JSONL file (atomic line append)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    """Read all records from a JSONL file."""
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


class Observer:
    """
    Central observability system for Cell Agency.

    All logging is append-only JSONL — low overhead, easy to grep/parse.
    """

    def __init__(self) -> None:
        _ensure_dirs()

    # ── Workflow logging ───────────────────────────────────────────────────────

    def log_workflow_event(
        self,
        workflow_id: str,
        event: str,
        data: dict | None = None,
    ) -> None:
        """
        Log a workflow lifecycle event.

        Args:
            workflow_id: The workflow UUID
            event:       Event name, e.g. "created", "state_changed", "step_started",
                         "step_completed", "approval_submitted", "completed", "failed"
            data:        Additional event payload
        """
        record = {
            "ts":          datetime.now().isoformat(),
            "workflow_id": workflow_id,
            "event":       event,
            "data":        data or {},
        }
        _append_jsonl(WF_LOGS_DIR / f"{workflow_id}.jsonl", record)

    # ── Agent logging ──────────────────────────────────────────────────────────

    def log_agent_action(
        self,
        agent_id: str,
        action: str,
        inputs:      dict | None = None,
        outputs:     Any         = None,
        duration_ms: int         = 0,
        success:     bool        = True,
        error:       str         = "",
    ) -> None:
        """
        Log an agent action (tool call, decision, delegation).

        Args:
            agent_id:    Agent identifier, e.g. "content_agent", "nadia"
            action:      Action name
            inputs:      Input dict (will be truncated if large)
            outputs:     Output (will be truncated if large)
            duration_ms: Execution time in milliseconds
            success:     Whether the action succeeded
            error:       Error message if failed
        """
        record = {
            "ts":          datetime.now().isoformat(),
            "agent_id":    agent_id,
            "action":      action,
            "inputs":      _truncate(inputs or {}),
            "outputs":     _truncate(outputs),
            "duration_ms": duration_ms,
            "success":     success,
            "error":       error,
        }
        _append_jsonl(AG_LOGS_DIR / f"{agent_id}.jsonl", record)

    # ── Tool logging ───────────────────────────────────────────────────────────

    def log_tool_call(
        self,
        tool_name:   str,
        inputs:      dict | None = None,
        output:      Any         = None,
        duration_ms: int         = 0,
        success:     bool        = True,
        agent_id:    str         = "",
        workflow_id: str         = "",
    ) -> None:
        """
        Log a tool call (MCP tool invocation).

        Args:
            tool_name:   MCP tool name
            inputs:      Tool inputs
            output:      Tool output (truncated)
            duration_ms: Execution time
            success:     Whether the call succeeded
            agent_id:    Agent that triggered the call (optional)
            workflow_id: Workflow context (optional)
        """
        today = date.today().isoformat()
        record = {
            "ts":          datetime.now().isoformat(),
            "tool_name":   tool_name,
            "inputs":      _truncate(inputs or {}),
            "output":      _truncate(output),
            "duration_ms": duration_ms,
            "success":     success,
            "agent_id":    agent_id,
            "workflow_id": workflow_id,
        }
        _append_jsonl(TL_LOGS_DIR / f"{today}.jsonl", record)

    # ── Dashboard ──────────────────────────────────────────────────────────────

    def agency_dashboard(self) -> dict:
        """
        Return comprehensive system status.

        Includes:
          - Active/completed/failed workflow counts
          - Recent agent actions (last 24h)
          - Tool call counts and success rates (last 7 days)
          - Pending approvals count
          - Pending autonomous drafts count
        """
        wf_stats   = self._workflow_stats()
        tool_stats = self.tool_usage_report(days=7)
        agent_stats = self.agent_activity_report(hours=24)
        approval_count  = self._count_pending_approvals()
        draft_count     = self._count_autonomous_drafts()

        return {
            "generated_at":     datetime.now().isoformat(),
            "workflows":        wf_stats,
            "pending_approvals": approval_count,
            "autonomous_drafts": draft_count,
            "tool_usage_7d":    tool_stats.get("summary", {}),
            "agent_activity_24h": agent_stats.get("summary", {}),
        }

    def workflow_logs(self, workflow_id: str, last_n: int = 50) -> dict:
        """
        Return the event log for a specific workflow.

        Args:
            workflow_id: Workflow UUID
            last_n:      Number of most recent events to return (0 = all)

        Returns:
            Dict with workflow_id and list of events
        """
        path    = WF_LOGS_DIR / f"{workflow_id}.jsonl"
        events  = _read_jsonl(path)
        if last_n > 0:
            events = events[-last_n:]
        return {
            "workflow_id": workflow_id,
            "event_count": len(events),
            "events":      events,
        }

    def agent_activity_report(self, agent_id: str = "", hours: int = 24) -> dict:
        """
        Return agent activity for the last N hours.

        Args:
            agent_id: Filter to a specific agent (empty = all agents)
            hours:    Look-back window in hours

        Returns:
            Dict with per-agent action counts, success rates, and recent actions
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        per_agent: dict[str, dict] = {}

        files = (
            [AG_LOGS_DIR / f"{agent_id}.jsonl"]
            if agent_id
            else list(AG_LOGS_DIR.glob("*.jsonl"))
        )

        for f in files:
            aid = f.stem
            records = [
                r for r in _read_jsonl(f)
                if _parse_ts(r.get("ts", "")) >= cutoff
            ]
            if not records:
                continue
            successes = sum(1 for r in records if r.get("success", True))
            per_agent[aid] = {
                "total_actions":  len(records),
                "success_count":  successes,
                "failure_count":  len(records) - successes,
                "success_rate":   round(successes / len(records), 3) if records else 1.0,
                "avg_duration_ms": int(
                    sum(r.get("duration_ms", 0) for r in records) / len(records)
                ) if records else 0,
                "recent_actions": [
                    {"ts": r["ts"], "action": r.get("action"), "success": r.get("success", True)}
                    for r in records[-5:]
                ],
            }

        total_actions = sum(v["total_actions"] for v in per_agent.values())
        return {
            "window_hours": hours,
            "agents_active": len(per_agent),
            "summary": {"total_actions": total_actions, "agents": list(per_agent.keys())},
            "per_agent":    per_agent,
        }

    def tool_usage_report(self, days: int = 7) -> dict:
        """
        Return tool call statistics for the last N days.

        Args:
            days: Look-back window in days

        Returns:
            Dict with per-tool call counts, success rates, avg duration
        """
        cutoff = datetime.now() - timedelta(days=days)
        per_tool: dict[str, dict] = {}

        for f in sorted(TL_LOGS_DIR.glob("*.jsonl")):
            for r in _read_jsonl(f):
                if _parse_ts(r.get("ts", "")) < cutoff:
                    continue
                name = r.get("tool_name", "unknown")
                if name not in per_tool:
                    per_tool[name] = {"calls": 0, "successes": 0, "total_ms": 0}
                per_tool[name]["calls"]     += 1
                per_tool[name]["successes"] += 1 if r.get("success", True) else 0
                per_tool[name]["total_ms"]  += r.get("duration_ms", 0)

        # Compute rates
        ranked = []
        for name, stats in per_tool.items():
            calls = stats["calls"]
            ranked.append({
                "tool":         name,
                "calls":        calls,
                "success_rate": round(stats["successes"] / calls, 3) if calls else 1.0,
                "avg_ms":       int(stats["total_ms"] / calls) if calls else 0,
            })
        ranked.sort(key=lambda x: x["calls"], reverse=True)

        total_calls = sum(x["calls"] for x in ranked)
        return {
            "window_days":  days,
            "unique_tools": len(ranked),
            "summary":      {"total_calls": total_calls, "top_tool": ranked[0]["tool"] if ranked else ""},
            "per_tool":     ranked,
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _workflow_stats(self) -> dict:
        """Count workflows by state from memory/workflows/."""
        wf_dir = AGENCY_DIR / "memory" / "workflows"
        if not wf_dir.exists():
            return {}
        counts: dict[str, int] = {}
        for f in wf_dir.glob("*.json"):
            try:
                data  = json.loads(f.read_text(encoding="utf-8"))
                state = data.get("state", "unknown")
                counts[state] = counts.get(state, 0) + 1
            except Exception:
                continue
        counts["total"] = sum(counts.values())
        return counts

    def _count_pending_approvals(self) -> int:
        queue_dir = AGENCY_DIR / "approval_queue"
        if not queue_dir.exists():
            return 0
        count = 0
        for f in queue_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("status") in ("pending", "edited"):
                    count += 1
            except Exception:
                continue
        return count

    def _count_autonomous_drafts(self) -> int:
        outputs_dir = AGENCY_DIR / "memory" / "outputs"
        if not outputs_dir.exists():
            return 0
        return len(list(outputs_dir.glob("*.json")))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _truncate(value: Any, max_chars: int = 500) -> Any:
    """Truncate large values to keep log files reasonable."""
    if value is None:
        return None
    s = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    if len(s) <= max_chars:
        return value
    return s[:max_chars] + "…[truncated]"


def _parse_ts(ts_str: str) -> datetime:
    """Parse ISO timestamp, returning epoch on failure."""
    try:
        return datetime.fromisoformat(ts_str)
    except Exception:
        return datetime(1970, 1, 1)


# ── Singleton ──────────────────────────────────────────────────────────────────

_observer: Observer | None = None


def get_observer() -> Observer:
    """Return singleton Observer."""
    global _observer
    if _observer is None:
        _observer = Observer()
    return _observer
