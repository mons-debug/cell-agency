"""
Cell Agency — Infrastructure Health Check
==========================================
Checks every agency component and returns a structured health report.

Checks:
  1. Environment variables     — all required keys present + non-empty
  2. MCP server processes      — all 4 servers alive (via PID files)
  3. ChromaDB                  — accessible and writable
  4. Task bus directories      — memory/tasks/{pending,active,done,failed}/ exist
  5. Memory directory          — memory/ writable, skill_performance.db accessible
  6. Client workspace          — clients/ directory and active clients
  7. Disk space                — ≥ 500 MB free on agency drive

Usage:
    from infra.health_check import load_health_checker

    hc = load_health_checker()
    report = hc.full_check()
    print(report.summary())
    print(report.to_markdown())
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.paths import get_agency_dir

AGENCY_DIR = get_agency_dir()

# ── Required env vars by phase ─────────────────────────────────────────────────
ENV_REQUIRED = {
    "phase1_core": [
        "OPENAI_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_OWNER_ID",
    ],
    "phase2_content": [
        "GEMINI_API_KEY",
        "SERPER_API_KEY",
    ],
    "phase3_social": [
        "INSTAGRAM_ACCESS_TOKEN",
        "INSTAGRAM_BUSINESS_ACCOUNT_ID",
        "FACEBOOK_ACCESS_TOKEN",
        "FACEBOOK_PAGE_ID",
    ],
    "phase4_ads": [
        "META_ACCESS_TOKEN",
        "META_AD_ACCOUNT_ID",
    ],
    "phase5_deploy": [
        "VERCEL_TOKEN",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
    ],
}

# ── MCP server definitions ─────────────────────────────────────────────────────
MCP_SERVERS = {
    # Original 4
    "agency":   "mcp-servers/agency_server.py",
    "social":   "mcp-servers/social_server.py",
    "ads":      "mcp-servers/ads_server.py",
    "design":   "mcp-servers/design_server.py",
    # New 6 (Phase 1)
    "content":  "mcp-servers/content_server.py",
    "video":    "mcp-servers/video_server.py",
    "asset":    "mcp-servers/asset_server.py",
    "document": "mcp-servers/document_server.py",
    "web":      "mcp-servers/web_server.py",
    "learning": "mcp-servers/learning_server.py",
}

DISK_MIN_MB = 500  # minimum free disk space in MB


# ── Result dataclasses ─────────────────────────────────────────────────────────

@dataclass
class ComponentStatus:
    name:    str
    status:  str          # ok | warn | error | skip
    message: str = ""
    details: dict = field(default_factory=dict)

    @property
    def icon(self) -> str:
        return {"ok": "✅", "warn": "⚠️", "error": "❌", "skip": "⏭"}.get(self.status, "?")


@dataclass
class HealthReport:
    timestamp:  str
    components: list[ComponentStatus] = field(default_factory=list)

    @property
    def overall(self) -> str:
        statuses = {c.status for c in self.components}
        if "error" in statuses:
            return "degraded"
        if "warn" in statuses:
            return "warning"
        return "healthy"

    @property
    def overall_icon(self) -> str:
        return {"healthy": "✅", "warning": "⚠️", "degraded": "❌"}.get(self.overall, "?")

    def summary(self) -> str:
        ok    = sum(1 for c in self.components if c.status == "ok")
        warn  = sum(1 for c in self.components if c.status == "warn")
        error = sum(1 for c in self.components if c.status == "error")
        return (
            f"{self.overall_icon} Agency status: {self.overall.upper()} "
            f"[✅ {ok} ok | ⚠️ {warn} warn | ❌ {error} error] "
            f"— {self.timestamp[:16]}"
        )

    def to_markdown(self) -> str:
        lines = [
            "# Agency Health Report",
            f"*{self.timestamp[:19]}*",
            f"**Overall: {self.overall_icon} {self.overall.upper()}**",
            "",
        ]
        for comp in self.components:
            lines.append(f"### {comp.icon} {comp.name}")
            if comp.message:
                lines.append(comp.message)
            if comp.details:
                for k, v in comp.details.items():
                    lines.append(f"- **{k}:** {v}")
            lines.append("")
        return "\n".join(lines)


# ── HealthChecker ──────────────────────────────────────────────────────────────

class HealthChecker:
    """Run all health checks and return a HealthReport."""

    def full_check(self) -> HealthReport:
        """Run all checks and return a complete HealthReport."""
        report = HealthReport(timestamp=datetime.now().isoformat())
        report.components = [
            self.check_env_vars(),
            self.check_mcp_servers(),
            self.check_chromadb(),
            self.check_task_bus(),
            self.check_memory_dir(),
            self.check_clients(),
            self.check_disk(),
            self.check_observability(),
        ]
        return report

    # ── Individual checks ─────────────────────────────────────────────────────

    def check_env_vars(self) -> ComponentStatus:
        """Check all required env vars are set and non-empty."""
        missing_by_phase: dict[str, list[str]] = {}
        set_by_phase:     dict[str, list[str]] = {}
        total_missing = 0
        total_set     = 0

        for phase, keys in ENV_REQUIRED.items():
            missing = [k for k in keys if not os.getenv(k, "").strip()]
            present = [k for k in keys if os.getenv(k, "").strip()]
            if missing:
                missing_by_phase[phase] = missing
            if present:
                set_by_phase[phase] = present
            total_missing += len(missing)
            total_set     += len(present)

        if total_missing == 0:
            return ComponentStatus(
                name="Environment Variables",
                status="ok",
                message=f"All {total_set} required env vars are set.",
                details={phase: f"✅ {len(keys)} set" for phase, keys in ENV_REQUIRED.items()},
            )

        # Some missing
        details = {}
        for phase, keys in ENV_REQUIRED.items():
            missing = missing_by_phase.get(phase, [])
            present_count = len(keys) - len(missing)
            if missing:
                details[phase] = f"⚠️ {present_count}/{len(keys)} set — missing: {', '.join(missing)}"
            else:
                details[phase] = f"✅ {len(keys)}/{len(keys)} set"

        return ComponentStatus(
            name="Environment Variables",
            status="warn",
            message=f"{total_missing} env var(s) missing — some agency features may be unavailable.",
            details=details,
        )

    def check_mcp_servers(self) -> ComponentStatus:
        """Check MCP server PID files and whether processes are alive."""
        pid_dir = AGENCY_DIR / "memory" / "pids"
        statuses: dict[str, str] = {}
        alive_count = 0
        missing_pid = 0

        for server, script in MCP_SERVERS.items():
            pid_file = pid_dir / f"{server}.pid"
            script_path = AGENCY_DIR / script

            if not script_path.exists():
                statuses[server] = "❌ script missing"
                continue

            if not pid_file.exists():
                statuses[server] = "⏭ not started (no PID file)"
                missing_pid += 1
                continue

            try:
                pid = int(pid_file.read_text().strip())
                # Check if process is alive using /proc or kill -0
                import signal
                try:
                    os.kill(pid, 0)  # signal 0 = just check existence
                    statuses[server] = f"✅ running (pid {pid})"
                    alive_count += 1
                except (ProcessLookupError, PermissionError):
                    statuses[server] = f"❌ crashed (pid {pid} gone)"
            except Exception as e:
                statuses[server] = f"⚠️ pid file error: {e}"

        if missing_pid == len(MCP_SERVERS):
            # Never started — this is normal if agency hasn't been launched yet
            return ComponentStatus(
                name="MCP Servers",
                status="warn",
                message="No PID files found — agency may not be running. Run start_agency.sh to start.",
                details=statuses,
            )

        if alive_count == len(MCP_SERVERS):
            return ComponentStatus(
                name="MCP Servers",
                status="ok",
                message=f"All {alive_count} MCP servers running.",
                details=statuses,
            )

        return ComponentStatus(
            name="MCP Servers",
            status="error" if alive_count == 0 else "warn",
            message=f"{alive_count}/{len(MCP_SERVERS)} MCP servers alive.",
            details=statuses,
        )

    def check_chromadb(self) -> ComponentStatus:
        """Check ChromaDB is accessible and the agency_knowledge collection exists."""
        chroma_path = AGENCY_DIR / ".chromadb"
        if not chroma_path.exists():
            return ComponentStatus(
                name="ChromaDB",
                status="warn",
                message="ChromaDB directory does not exist yet — will be created on first use.",
            )
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(chroma_path))
            collections = client.list_collections()
            col_names   = [c.name for c in collections]
            return ComponentStatus(
                name="ChromaDB",
                status="ok",
                message=f"ChromaDB accessible. {len(col_names)} collection(s).",
                details={"collections": ", ".join(col_names) if col_names else "(none yet)"},
            )
        except ImportError:
            return ComponentStatus(
                name="ChromaDB",
                status="warn",
                message="chromadb package not importable in this context (normal outside uv env).",
            )
        except Exception as e:
            return ComponentStatus(
                name="ChromaDB",
                status="error",
                message=f"ChromaDB error: {e}",
            )

    def check_task_bus(self) -> ComponentStatus:
        """Check task bus directories exist."""
        tasks_dir = AGENCY_DIR / "memory" / "tasks"
        required  = ["pending", "active", "done", "failed"]
        missing   = [d for d in required if not (tasks_dir / d).exists()]

        if missing:
            return ComponentStatus(
                name="Task Bus",
                status="warn",
                message=f"Missing task dirs: {missing}. Run: from comms import load_task_bus; load_task_bus()",
            )

        # Count files in each
        counts = {d: len(list((tasks_dir / d).glob("*.json"))) for d in required}
        total  = sum(counts.values())
        return ComponentStatus(
            name="Task Bus",
            status="ok",
            message=f"All 4 task directories present. {total} total task(s).",
            details={f"{d}/": f"{counts[d]} tasks" for d in required},
        )

    def check_memory_dir(self) -> ComponentStatus:
        """Check memory directory and skill performance DB."""
        memory_dir = AGENCY_DIR / "memory"
        if not memory_dir.exists():
            return ComponentStatus(
                name="Memory",
                status="error",
                message="memory/ directory does not exist.",
            )

        details: dict[str, str] = {}
        status = "ok"

        # Skill performance DB
        db_path = memory_dir / "skill_performance.db"
        if db_path.exists():
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
                details["skill_performance.db"] = f"✅ {count} run(s) logged"
            except Exception as e:
                details["skill_performance.db"] = f"❌ error: {e}"
                status = "warn"
        else:
            details["skill_performance.db"] = "⏭ not created yet (no runs logged)"

        # Approval queue
        aq = memory_dir / "approval_queue.json"
        if aq.exists():
            import json
            try:
                q    = json.loads(aq.read_text())
                pending = sum(1 for i in q if i.get("status") == "pending")
                details["approval_queue.json"] = f"✅ {len(q)} items, {pending} pending"
            except Exception:
                details["approval_queue.json"] = "⚠️ parse error"
        else:
            details["approval_queue.json"] = "⏭ empty"

        # Denied access log
        dal = memory_dir / "denied_access.log"
        if dal.exists():
            lines = dal.read_text().splitlines()
            details["denied_access.log"] = f"⚠️ {len(lines)} denied access attempt(s)" if lines else "✅ empty"
            if lines:
                status = "warn"

        return ComponentStatus(
            name="Memory",
            status=status,
            message=f"memory/ directory accessible.",
            details=details,
        )

    def check_clients(self) -> ComponentStatus:
        """Check clients directory and brand vaults."""
        clients_dir = AGENCY_DIR / "clients"
        if not clients_dir.exists():
            return ComponentStatus(
                name="Client Workspace",
                status="warn",
                message="clients/ directory does not exist.",
            )

        clients = [d.name for d in clients_dir.iterdir() if d.is_dir()]
        if not clients:
            return ComponentStatus(
                name="Client Workspace",
                status="warn",
                message="No clients registered yet.",
            )

        details: dict[str, str] = {}
        for client in clients:
            vault = clients_dir / client / "brand_vault.md"
            cal   = clients_dir / client / "calendar.md"
            v_ok  = "✅" if vault.exists() else "❌"
            c_ok  = "✅" if cal.exists() else "❌"
            details[client] = f"brand_vault {v_ok} | calendar {c_ok}"

        return ComponentStatus(
            name="Client Workspace",
            status="ok",
            message=f"{len(clients)} client(s) registered.",
            details=details,
        )

    def check_observability(self) -> ComponentStatus:
        """Check observability logs directory and recent activity."""
        logs_dir = AGENCY_DIR / "logs"
        wf_logs  = logs_dir / "workflow_logs"
        ag_logs  = logs_dir / "agent_logs"
        tl_logs  = logs_dir / "tool_usage"

        missing = [
            d.name for d in [logs_dir, wf_logs, ag_logs, tl_logs] if not d.exists()
        ]
        if missing:
            return ComponentStatus(
                name="Observability",
                status="warn",
                message=f"Log directories missing: {missing}. Run start_agency.sh to create.",
            )

        import json as _json

        wf_count = len(list(wf_logs.glob("*.jsonl")))
        ag_count = len(list(ag_logs.glob("*.jsonl")))
        tl_count = len(list(tl_logs.glob("*.jsonl")))

        # Count pending approvals
        approval_dir = AGENCY_DIR / "approval_queue"
        pending_approvals = 0
        if approval_dir.exists():
            for f in approval_dir.glob("*.json"):
                try:
                    d = _json.loads(f.read_text(encoding="utf-8"))
                    if d.get("status") in ("pending", "edited"):
                        pending_approvals += 1
                except Exception:
                    pass

        # Count autonomous drafts
        outputs_dir = AGENCY_DIR / "memory" / "outputs"
        draft_count = len(list(outputs_dir.glob("*.json"))) if outputs_dir.exists() else 0

        return ComponentStatus(
            name="Observability",
            status="ok",
            message="Observability system online.",
            details={
                "workflow_logs": f"{wf_count} workflow(s) tracked",
                "agent_logs":    f"{ag_count} agent(s) tracked",
                "tool_logs":     f"{tl_count} daily log(s)",
                "pending_approvals": str(pending_approvals),
                "autonomous_drafts": str(draft_count),
            },
        )

    def check_disk(self) -> ComponentStatus:
        """Check available disk space on the agency drive."""
        usage = shutil.disk_usage(str(AGENCY_DIR))
        free_mb  = usage.free // (1024 * 1024)
        total_mb = usage.total // (1024 * 1024)
        used_pct = (usage.used / usage.total) * 100

        if free_mb < DISK_MIN_MB:
            return ComponentStatus(
                name="Disk Space",
                status="error",
                message=f"Low disk space: {free_mb} MB free (need ≥ {DISK_MIN_MB} MB).",
                details={"free": f"{free_mb} MB", "used": f"{used_pct:.0f}%", "total": f"{total_mb} MB"},
            )
        if free_mb < DISK_MIN_MB * 4:
            return ComponentStatus(
                name="Disk Space",
                status="warn",
                message=f"Disk getting low: {free_mb} MB free.",
                details={"free": f"{free_mb} MB", "used": f"{used_pct:.0f}%", "total": f"{total_mb} MB"},
            )

        return ComponentStatus(
            name="Disk Space",
            status="ok",
            message=f"{free_mb:,} MB free ({100-used_pct:.0f}% available).",
            details={"free": f"{free_mb:,} MB", "used": f"{used_pct:.0f}%", "total": f"{total_mb:,} MB"},
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_checker_instance: Optional[HealthChecker] = None


def load_health_checker() -> HealthChecker:
    """Return singleton HealthChecker."""
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = HealthChecker()
    return _checker_instance
