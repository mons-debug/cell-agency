"""
Cell Agency — Skill Evolution System
=====================================
Tracks every skill execution, aggregates performance stats, and surfaces
improvement opportunities so skills get smarter over time.

Storage:
  memory/skill_performance.db    ← SQLite log of all runs
  skills/<skill>/performance.json ← auto-updated per-skill stats summary

Usage:
    from skills.skill_tracker import load_tracker

    tracker = load_tracker()

    # Agent logs a completed run
    run_id = tracker.log_run(
        skill="content-forge",
        agent="content_creator",
        client_id="refine-clinic",
        triggered_by="write instagram caption for Ramadan",
        status="success",
        qa_score=9.0,
        duration_s=14.2,
    )

    # Nadia records Moncef's reaction
    tracker.log_feedback(run_id, feedback="approved", approved=True)

    # Check how a skill is performing
    stats = tracker.get_performance("content-forge")
    print(stats["success_rate"], stats["avg_qa_score"])

    # Full agency evolution report
    print(tracker.evolution_report())
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, date
from pathlib import Path
from typing import Optional

AGENCY_DIR = Path.home() / "agency"
SKILLS_DIR = AGENCY_DIR / "skills"
DB_PATH    = AGENCY_DIR / "memory" / "skill_performance.db"

# Thresholds for flagging underperforming skills
THRESHOLD_SUCCESS_RATE    = 0.80   # below 80% runs succeed → flag
THRESHOLD_QA_SCORE        = 7.0    # below 7/10 average QA score → flag
THRESHOLD_APPROVAL_RATE   = 0.70   # Moncef approves < 70% → flag
MIN_RUNS_FOR_EVAL         = 3      # need at least 3 runs before evaluating

# Known skill slugs (matches skills/ directory names)
KNOWN_SKILLS = [
    "ads-cockpit", "brand-vault", "calendar-brain", "client-pulse",
    "client-registry", "content-forge", "design-brief", "email-engine",
    "lead-hunter", "report-builder", "seo-radar", "social-pilot",
]

STOPWORDS = {"for", "the", "a", "an", "to", "and", "or", "of", "in", "on",
             "with", "write", "create", "make", "generate", "get", "do", "me"}


# ── SkillTracker ───────────────────────────────────────────────────────────────

class SkillTracker:
    """
    Logs skill executions to SQLite and maintains per-skill performance.json summaries.

    Lifecycle:
        log_run()       → records execution, updates performance.json
        log_feedback()  → adds Moncef's approval/rejection to a run
        get_performance() → aggregated stats for one skill
        get_all_performance() → stats for every skill with ≥1 run
        evolution_report() → markdown report with highlights + underperformers
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Public API ─────────────────────────────────────────────────────────────

    def log_run(
        self,
        skill:        str,
        agent:        str,
        client_id:    str = "",
        triggered_by: str = "",
        status:       str = "success",   # success | failed | partial
        qa_score:     Optional[float] = None,
        duration_s:   Optional[float] = None,
        notes:        str = "",
    ) -> str:
        """
        Record one skill execution.

        Args:
            skill:        Skill slug (e.g. 'content-forge')
            agent:        Agent that ran it (e.g. 'content_creator')
            client_id:    Client context (e.g. 'refine-clinic')
            triggered_by: Raw trigger phrase / task description
            status:       'success' | 'failed' | 'partial'
            qa_score:     QA Gate score 1-10 (optional, filled after QA review)
            duration_s:   Wall-clock seconds the task took (optional)
            notes:        Any extra notes

        Returns:
            run_id — pass to log_feedback() to record Moncef's reaction
        """
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now    = datetime.now().isoformat()

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO runs
                  (run_id, skill, agent, client_id, triggered_by, status,
                   qa_score, duration_s, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, skill, agent, client_id, triggered_by, status,
                 qa_score, duration_s, notes, now),
            )

        # Refresh the per-skill performance.json
        self._update_performance_file(skill)
        return run_id

    def log_feedback(
        self,
        run_id:   str,
        feedback: str = "",
        approved: Optional[bool] = None,
    ) -> bool:
        """
        Record Moncef's reaction to a skill output.

        Args:
            run_id:   From log_run()
            feedback: Text feedback ('approved', 'needs revision', etc.)
            approved: True = approved, False = rejected, None = no decision yet

        Returns:
            True if run_id found and updated, False otherwise
        """
        approved_int = None if approved is None else (1 if approved else 0)
        with self._conn() as conn:
            cursor = conn.execute(
                "UPDATE runs SET moncef_feedback=?, moncef_approved=? WHERE run_id=?",
                (feedback, approved_int, run_id),
            )
            updated = cursor.rowcount > 0

        if updated:
            # Get skill for this run and refresh its performance.json
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT skill FROM runs WHERE run_id=?", (run_id,)
                ).fetchone()
            if row:
                self._update_performance_file(row[0])
        return updated

    def get_performance(self, skill: str) -> dict:
        """
        Return aggregated performance stats for a single skill.

        Returns dict with:
            skill, total_runs, success_rate, avg_qa_score, avg_duration_s,
            moncef_approval_rate, last_run, top_triggers, health, issues
        """
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                                                         AS total_runs,
                    SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) * 1.0
                        / NULLIF(COUNT(*), 0)                                        AS success_rate,
                    AVG(CASE WHEN qa_score IS NOT NULL THEN qa_score END)            AS avg_qa_score,
                    AVG(CASE WHEN duration_s IS NOT NULL THEN duration_s END)        AS avg_duration_s,
                    SUM(CASE WHEN moncef_approved=1 THEN 1 ELSE 0 END) * 1.0
                        / NULLIF(SUM(CASE WHEN moncef_approved IS NOT NULL
                                         THEN 1 ELSE 0 END), 0)                     AS moncef_approval_rate,
                    MAX(timestamp)                                                   AS last_run
                FROM runs
                WHERE skill = ?
                """,
                (skill,),
            ).fetchone()

            # Get all trigger phrases for word frequency
            triggers = conn.execute(
                "SELECT triggered_by FROM runs WHERE skill=? AND triggered_by != ''",
                (skill,),
            ).fetchall()

        total_runs = row[0] or 0
        if total_runs == 0:
            return {
                "skill": skill, "total_runs": 0,
                "success_rate": None, "avg_qa_score": None,
                "avg_duration_s": None, "moncef_approval_rate": None,
                "last_run": None, "top_triggers": [], "health": "no_data", "issues": [],
            }

        # Calculate top trigger words
        words = []
        for (text,) in triggers:
            words.extend([
                w.lower() for w in re.findall(r'\b\w{4,}\b', text)
                if w.lower() not in STOPWORDS
            ])
        top_triggers = [w for w, _ in Counter(words).most_common(5)]

        # Determine health status
        success_rate      = row[1]
        avg_qa_score      = row[2]
        moncef_rate       = row[4]
        issues            = []

        if total_runs >= MIN_RUNS_FOR_EVAL:
            if success_rate is not None and success_rate < THRESHOLD_SUCCESS_RATE:
                issues.append(f"low success rate ({success_rate:.0%})")
            if avg_qa_score is not None and avg_qa_score < THRESHOLD_QA_SCORE:
                issues.append(f"low QA score ({avg_qa_score:.1f}/10)")
            if moncef_rate is not None and moncef_rate < THRESHOLD_APPROVAL_RATE:
                issues.append(f"low Moncef approval rate ({moncef_rate:.0%})")

        health = "underperforming" if issues else ("healthy" if total_runs >= MIN_RUNS_FOR_EVAL else "new")

        return {
            "skill":               skill,
            "total_runs":          total_runs,
            "success_rate":        round(success_rate, 3) if success_rate is not None else None,
            "avg_qa_score":        round(avg_qa_score, 1) if avg_qa_score is not None else None,
            "avg_duration_s":      round(row[3], 1) if row[3] is not None else None,
            "moncef_approval_rate": round(moncef_rate, 3) if moncef_rate is not None else None,
            "last_run":            row[5][:10] if row[5] else None,
            "top_triggers":        top_triggers,
            "health":              health,
            "issues":              issues,
        }

    def get_all_performance(self) -> list[dict]:
        """Return performance stats for every skill that has ≥1 logged run."""
        with self._conn() as conn:
            skills = [r[0] for r in conn.execute(
                "SELECT DISTINCT skill FROM runs ORDER BY skill"
            ).fetchall()]
        return [self.get_performance(s) for s in skills]

    def recent_runs(self, skill: str = "", n: int = 10) -> list[dict]:
        """Return the n most recent runs, optionally filtered by skill."""
        query  = "SELECT * FROM runs"
        params: list = []
        if skill:
            query  += " WHERE skill=?"
            params  = [skill]
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(n)
        with self._conn() as conn:
            cols = ["run_id", "skill", "agent", "client_id", "triggered_by",
                    "status", "qa_score", "duration_s", "moncef_feedback",
                    "moncef_approved", "notes", "timestamp"]
            rows = conn.execute(query, params).fetchall()
        return [dict(zip(cols, row)) for row in rows]

    def evolution_report(self) -> str:
        """
        Generate a full Markdown evolution report for all skills.
        Highlights top performers and flags underperformers with improvement notes.
        """
        all_stats = self.get_all_performance()
        # Also include skills with no runs
        tracked   = {s["skill"] for s in all_stats}
        no_data   = [s for s in KNOWN_SKILLS if s not in tracked]

        lines = [
            "# Skill Evolution Report",
            f"*Generated: {date.today().isoformat()}*",
            f"*Skills tracked: {len(all_stats)} | No data yet: {len(no_data)}*",
            "",
        ]

        # Summary table
        lines += [
            "## Performance Summary",
            "",
            "| Skill | Runs | Success% | QA Score | Approval% | Health |",
            "|-------|------|---------|---------|----------|--------|",
        ]
        for s in sorted(all_stats, key=lambda x: x["total_runs"], reverse=True):
            sr  = f"{s['success_rate']:.0%}"      if s["success_rate"]       is not None else "—"
            qa  = f"{s['avg_qa_score']:.1f}/10"   if s["avg_qa_score"]       is not None else "—"
            ar  = f"{s['moncef_approval_rate']:.0%}" if s["moncef_approval_rate"] is not None else "—"
            icon = "🔴" if s["health"] == "underperforming" else ("✅" if s["health"] == "healthy" else "🆕")
            lines.append(
                f"| {s['skill']} | {s['total_runs']} | {sr} | {qa} | {ar} | {icon} {s['health']} |"
            )
        lines.append("")

        # Underperformers section
        bad = [s for s in all_stats if s["health"] == "underperforming"]
        if bad:
            lines += ["## ⚠️ Underperforming Skills — Needs Attention", ""]
            for s in bad:
                lines.append(f"### {s['skill']}")
                for issue in s["issues"]:
                    lines.append(f"- 🔴 {issue}")
                if s["top_triggers"]:
                    lines.append(f"- Top trigger words: {', '.join(s['top_triggers'])}")
                lines.append("")
        else:
            lines += ["## ✅ All Tracked Skills Healthy", ""]

        # No-data skills
        if no_data:
            lines += [
                "## 🆕 Skills Not Yet Used",
                "",
                "The following skills have no execution records yet:",
                "",
            ]
            for s in no_data:
                lines.append(f"- `{s}`")
            lines.append("")

        # Top performers
        top = [s for s in all_stats if s["health"] == "healthy" and s["total_runs"] >= 5]
        top.sort(key=lambda x: (x["avg_qa_score"] or 0), reverse=True)
        if top:
            lines += ["## 🏆 Top Performers", ""]
            for s in top[:3]:
                lines.append(
                    f"- **{s['skill']}** — {s['total_runs']} runs, "
                    f"QA {s['avg_qa_score']}/10, "
                    f"{s['moncef_approval_rate']:.0%} Moncef approval"
                )
            lines.append("")

        return "\n".join(lines)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id            TEXT PRIMARY KEY,
                    skill             TEXT NOT NULL,
                    agent             TEXT NOT NULL,
                    client_id         TEXT DEFAULT '',
                    triggered_by      TEXT DEFAULT '',
                    status            TEXT DEFAULT 'success',
                    qa_score          REAL,
                    duration_s        REAL,
                    moncef_feedback   TEXT,
                    moncef_approved   INTEGER,
                    notes             TEXT DEFAULT '',
                    timestamp         TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skill ON runs(skill)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON runs(timestamp)")
            conn.commit()

    def _update_performance_file(self, skill: str) -> None:
        """Write/update skills/<skill>/performance.json with latest aggregated stats."""
        skill_dir = SKILLS_DIR / skill
        if not skill_dir.exists():
            return  # unknown skill slug — skip file update
        stats = self.get_performance(skill)
        perf_path = skill_dir / "performance.json"
        perf_path.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_tracker_instance: Optional[SkillTracker] = None


def load_tracker(db_path: Path = DB_PATH) -> SkillTracker:
    """Return singleton SkillTracker instance (lazy-loaded)."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = SkillTracker(db_path)
    return _tracker_instance
