"""
Cell Agency — MCP Server Process Manager
==========================================
Start, stop, restart, and monitor the 4 FastMCP servers.
PIDs are stored in memory/pids/ so health checks can verify aliveness.

Usage:
    from infra.process_manager import load_process_manager

    pm = load_process_manager()
    pm.start("agency")          # Start agency_server.py
    pm.status_all()             # Dict of {server: "running|stopped|crashed"}
    pm.restart("social")        # Restart social_server.py
    pm.stop_all()               # Graceful shutdown of all servers
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.paths import get_agency_dir

AGENCY_DIR = get_agency_dir()
PID_DIR    = AGENCY_DIR / "memory" / "pids"
LOG_DIR    = AGENCY_DIR / "memory" / "logs"

# ── Server definitions ─────────────────────────────────────────────────────────
MCP_SERVERS: dict[str, dict] = {
    # ── Original 4 servers ──────────────────────────────────────────────────────
    "agency": {
        "script": "mcp-servers/agency_server.py",
        "description": "Core agency tools (files, memory, routing, registry, learning bridge)",
        "port": None,  # FastMCP stdio transport
    },
    "social": {
        "script": "mcp-servers/social_server.py",
        "description": "Instagram and Facebook Graph API tools",
        "port": None,
    },
    "ads": {
        "script": "mcp-servers/ads_server.py",
        "description": "Meta Ads and Google Ads management tools",
        "port": None,
    },
    "design": {
        "script": "mcp-servers/design_server.py",
        "description": "Gemini and Firefly image generation tools",
        "port": None,
    },
    # ── New 6 servers (Phase 1) ──────────────────────────────────────────────────
    "content": {
        "script": "mcp-servers/content_server.py",
        "description": "Content strategy, captions, plans, articles, ad copy",
        "port": None,
    },
    "video": {
        "script": "mcp-servers/video_server.py",
        "description": "Reel concept generation, video editing stubs",
        "port": None,
    },
    "asset": {
        "script": "mcp-servers/asset_server.py",
        "description": "Asset search, scoring, tagging, listing (ChromaDB)",
        "port": None,
    },
    "document": {
        "script": "mcp-servers/document_server.py",
        "description": "Document and report generation (proposals, briefs, weekly reports)",
        "port": None,
    },
    "web": {
        "script": "mcp-servers/web_server.py",
        "description": "Next.js website generation and page updates",
        "port": None,
    },
    "learning": {
        "script": "mcp-servers/learning_server.py",
        "description": "Intelligence layer: inspiration, learnings, daily/weekly analysis",
        "port": None,
    },
}

VALID_SERVERS = set(MCP_SERVERS.keys())


# ── ServerStatus ───────────────────────────────────────────────────────────────

@dataclass
class ServerStatus:
    name:        str
    status:      str     # running | stopped | crashed | unknown
    pid:         Optional[int] = None
    started_at:  Optional[str] = None
    script:      str = ""
    description: str = ""

    @property
    def icon(self) -> str:
        return {
            "running":  "✅",
            "stopped":  "⏹",
            "crashed":  "❌",
            "unknown":  "❓",
        }.get(self.status, "?")

    def __str__(self) -> str:
        pid_str = f" (pid {self.pid})" if self.pid else ""
        return f"{self.icon} {self.name}{pid_str} — {self.description}"


# ── ProcessManager ─────────────────────────────────────────────────────────────

class ProcessManager:
    """
    Manages the lifecycle of all 4 Cell Agency MCP servers.

    PID files in memory/pids/<server>.pid enable cross-process status checks.
    Logs go to memory/logs/<server>.log for post-mortem debugging.
    """

    def __init__(self) -> None:
        PID_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self, server: str) -> ServerStatus:
        """
        Start an MCP server in the background.

        Args:
            server: Server name ('agency' | 'social' | 'ads' | 'design')

        Returns:
            ServerStatus after start attempt
        """
        self._validate(server)
        current = self.status(server)
        if current.status == "running":
            return current

        conf   = MCP_SERVERS[server]
        script = AGENCY_DIR / conf["script"]
        if not script.exists():
            raise FileNotFoundError(f"Server script not found: {script}")

        log_file = LOG_DIR / f"{server}.log"
        env      = self._build_env()

        with open(log_file, "a") as log:
            log.write(f"\n{'='*60}\n")
            log.write(f"[{datetime.now().isoformat()}] Starting {server} server\n")
            log.write(f"Script: {script}\n")
            log.write(f"{'='*60}\n")

        proc = subprocess.Popen(
            [sys.executable, str(script)],
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            cwd=str(AGENCY_DIR),
            env=env,
            start_new_session=True,  # detach from parent process group
        )

        # Save PID
        pid_file = PID_DIR / f"{server}.pid"
        pid_file.write_text(str(proc.pid))

        # Brief check that it didn't immediately crash
        import time
        time.sleep(0.5)
        if proc.poll() is not None:
            return ServerStatus(
                name=server,
                status="crashed",
                pid=proc.pid,
                description=conf["description"],
                script=conf["script"],
            )

        return ServerStatus(
            name=server,
            status="running",
            pid=proc.pid,
            started_at=datetime.now().isoformat(),
            description=conf["description"],
            script=conf["script"],
        )

    def stop(self, server: str, signal_type: int = signal.SIGTERM) -> ServerStatus:
        """
        Stop an MCP server gracefully.

        Args:
            server:      Server name
            signal_type: SIGTERM (graceful) or SIGKILL (force)
        """
        self._validate(server)
        current = self.status(server)
        if current.status != "running":
            self._remove_pid(server)
            return ServerStatus(
                name=server,
                status="stopped",
                description=MCP_SERVERS[server]["description"],
                script=MCP_SERVERS[server]["script"],
            )

        try:
            os.kill(current.pid, signal_type)
            import time
            time.sleep(0.3)
            # If still alive after SIGTERM, force kill
            if signal_type == signal.SIGTERM:
                try:
                    os.kill(current.pid, 0)
                    os.kill(current.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        except (ProcessLookupError, PermissionError):
            pass

        self._remove_pid(server)
        return ServerStatus(
            name=server,
            status="stopped",
            description=MCP_SERVERS[server]["description"],
            script=MCP_SERVERS[server]["script"],
        )

    def restart(self, server: str) -> ServerStatus:
        """Stop then start a server."""
        self._validate(server)
        self.stop(server)
        import time
        time.sleep(0.5)
        return self.start(server)

    def start_all(self) -> list[ServerStatus]:
        """Start all 10 MCP servers."""
        results = []
        for server in MCP_SERVERS:
            try:
                results.append(self.start(server))
            except Exception as e:
                results.append(ServerStatus(
                    name=server,
                    status="crashed",
                    description=f"Start error: {e}",
                    script=MCP_SERVERS[server]["script"],
                ))
        return results

    def stop_all(self) -> list[ServerStatus]:
        """Gracefully stop all running servers."""
        return [self.stop(s) for s in MCP_SERVERS]

    def status(self, server: str) -> ServerStatus:
        """Get current status of a single server."""
        self._validate(server)
        conf     = MCP_SERVERS[server]
        pid_file = PID_DIR / f"{server}.pid"

        if not pid_file.exists():
            return ServerStatus(
                name=server,
                status="stopped",
                description=conf["description"],
                script=conf["script"],
            )

        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)   # raises if process is gone
            return ServerStatus(
                name=server,
                status="running",
                pid=pid,
                description=conf["description"],
                script=conf["script"],
            )
        except (ProcessLookupError, PermissionError):
            return ServerStatus(
                name=server,
                status="crashed",
                pid=None,
                description=conf["description"],
                script=conf["script"],
            )
        except Exception:
            return ServerStatus(
                name=server,
                status="unknown",
                description=conf["description"],
                script=conf["script"],
            )

    def status_all(self) -> list[ServerStatus]:
        """Return status of all 10 servers."""
        return [self.status(s) for s in MCP_SERVERS]

    def tail_log(self, server: str, lines: int = 30) -> str:
        """Return the last N lines from a server's log file."""
        self._validate(server)
        log_file = LOG_DIR / f"{server}.log"
        if not log_file.exists():
            return f"No log file for '{server}' yet."
        content = log_file.read_text(encoding="utf-8", errors="replace")
        log_lines = content.splitlines()
        tail = log_lines[-lines:] if len(log_lines) > lines else log_lines
        return "\n".join(tail)

    def status_report(self) -> str:
        """Return a formatted Markdown status table for all servers."""
        statuses = self.status_all()
        lines = [
            "## MCP Server Status",
            "",
            "| Server | Status | PID | Description |",
            "|--------|--------|-----|-------------|",
        ]
        for s in statuses:
            pid = str(s.pid) if s.pid else "—"
            lines.append(f"| {s.name} | {s.icon} {s.status} | {pid} | {s.description} |")
        lines.append("")
        running = sum(1 for s in statuses if s.status == "running")
        lines.append(f"*{running}/{len(statuses)} servers running*")
        return "\n".join(lines)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _validate(self, server: str) -> None:
        if server not in VALID_SERVERS:
            raise ValueError(f"Unknown server '{server}'. Valid: {sorted(VALID_SERVERS)}")

    def _remove_pid(self, server: str) -> None:
        pid_file = PID_DIR / f"{server}.pid"
        if pid_file.exists():
            pid_file.unlink()

    def _build_env(self) -> dict:
        """Build env dict with .env loaded, suitable for subprocess."""
        env = os.environ.copy()
        env_file = AGENCY_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() not in env:  # don't override already-set vars
                        env[k.strip()] = v.strip()
        return env


# ── Singleton ──────────────────────────────────────────────────────────────────

_pm_instance: Optional[ProcessManager] = None


def load_process_manager() -> ProcessManager:
    """Return singleton ProcessManager."""
    global _pm_instance
    if _pm_instance is None:
        _pm_instance = ProcessManager()
    return _pm_instance
