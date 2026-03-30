"""
Cell Agency — File Permission System
======================================
Per-agent file ACL enforcement on top of the existing _safe_path() layer.

Two-layer security:
  Layer 1 (existing): _safe_path() — blocks anything outside clients/, skills/, memory/
  Layer 2 (this):     FilePermissions — per-agent rules within those directories

Usage:
    from permissions import load_permissions, PermissionDenied

    perms = load_permissions()

    # Check before operating
    perms.check("content_creator", "write", "clients/refine-clinic/content/caption.md")

    # Or use the guarded wrappers
    perms.read("content_creator",  "clients/refine-clinic/brand_vault.md")
    perms.write("content_creator", "clients/refine-clinic/content/post.md", "caption text")
"""

from __future__ import annotations

import fnmatch
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from core.paths import get_agency_dir

PERMISSIONS_PATH = Path(__file__).parent / "permissions.yaml"
AGENCY_DIR = get_agency_dir()
DENIED_LOG = AGENCY_DIR / "memory" / "denied_access.log"

logger = logging.getLogger(__name__)

# Valid operations
VALID_OPS = {"read", "write", "append", "delete", "create_dir"}


# ── Exceptions ────────────────────────────────────────────────────────────────

class PermissionDenied(PermissionError):
    """Raised when an agent tries to access a file it has no permission for."""
    def __init__(self, agent: str, op: str, path: str, reason: str = ""):
        self.agent = agent
        self.op = op
        self.path = path
        self.reason = reason
        msg = f"[PERMISSION DENIED] agent={agent} op={op} path={path}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


# ── Core Permission Engine ────────────────────────────────────────────────────

class FilePermissions:
    """
    Enforces per-agent file ACLs defined in permissions.yaml.

    Rules:
    - Evaluated top-to-bottom per agent
    - First matching pattern wins
    - Default: DENY if nothing matches (when default_policy: deny)
    - Paths are always normalised relative to ~/agency/
    """

    def __init__(self, permissions_path: Path = PERMISSIONS_PATH):
        self._path = permissions_path
        self._rules: dict[str, list[dict]] = {}
        self._default_policy: str = "deny"
        self._log_denied: bool = True
        self._log_granted: bool = False
        self._load()

    # ── Public check API ─────────────────────────────────────────────────────

    def check(self, agent_id: str, op: str, path: str) -> bool:
        """
        Check if agent_id is allowed to perform op on path.

        Args:
            agent_id: Agent identifier (e.g. 'content_creator')
            op: Operation — 'read', 'write', 'append', 'delete', 'create_dir'
            path: File path (absolute or relative to ~/agency/)

        Returns:
            True if allowed

        Raises:
            PermissionDenied if not allowed
        """
        if op not in VALID_OPS:
            raise ValueError(f"Invalid op '{op}'. Must be one of {VALID_OPS}")

        rel = self._normalise(path)
        allowed = self._evaluate(agent_id, op, rel)

        if allowed:
            if self._log_granted:
                logger.debug(f"[GRANTED] {agent_id} {op} {rel}")
            return True

        # Denied
        reason = f"no rule grants {op} on {rel}"
        if agent_id not in self._rules:
            reason = f"agent '{agent_id}' has no rules defined"

        if self._log_denied:
            self._write_denied_log(agent_id, op, rel, reason)

        raise PermissionDenied(agent=agent_id, op=op, path=rel, reason=reason)

    def is_allowed(self, agent_id: str, op: str, path: str) -> bool:
        """
        Check permission without raising. Returns True/False.
        """
        try:
            return self.check(agent_id, op, path)
        except PermissionDenied:
            return False

    def explain(self, agent_id: str, path: str) -> dict:
        """
        Return which operations agent_id is allowed on path.
        Useful for debugging.

        Returns:
            {"path": "...", "agent": "...", "allowed": ["read", "write"], "denied": [...]}
        """
        rel = self._normalise(path)
        allowed = []
        denied = []
        for op in sorted(VALID_OPS):
            if self._evaluate(agent_id, op, rel):
                allowed.append(op)
            else:
                denied.append(op)
        return {
            "path": rel,
            "agent": agent_id,
            "allowed": allowed,
            "denied": denied,
        }

    def list_agent_paths(self, agent_id: str) -> list[dict]:
        """
        Return all path patterns and ops defined for an agent.
        """
        rules = self._rules.get(agent_id, [])
        return [{"pattern": r["path"], "ops": r["ops"]} for r in rules]

    def reload(self) -> None:
        """Hot-reload permissions.yaml from disk."""
        self._rules.clear()
        self._load()
        logger.info("File permissions reloaded.")

    # ── Guarded file operation wrappers ──────────────────────────────────────
    # These wrap tools/file_tools.py with agent-aware permission checks.

    def read(self, agent_id: str, path: str) -> str:
        """Read a file as agent_id (checks read permission first)."""
        import sys
        sys.path.insert(0, str(AGENCY_DIR / "tools"))
        from file_tools import read_file
        self.check(agent_id, "read", path)
        return read_file(path)

    def write(self, agent_id: str, path: str, content: str, overwrite: bool = True) -> str:
        """Write a file as agent_id (checks write permission first)."""
        import sys
        sys.path.insert(0, str(AGENCY_DIR / "tools"))
        from file_tools import write_file
        self.check(agent_id, "write", path)
        return write_file(path, content, overwrite)

    def append(self, agent_id: str, path: str, content: str) -> str:
        """Append to a file as agent_id (checks append permission first)."""
        import sys
        sys.path.insert(0, str(AGENCY_DIR / "tools"))
        from file_tools import append_file
        self.check(agent_id, "append", path)
        return append_file(path, content)

    def delete(self, agent_id: str, path: str) -> str:
        """Delete a file as agent_id (checks delete permission first)."""
        import sys
        sys.path.insert(0, str(AGENCY_DIR / "tools"))
        from file_tools import delete_file
        self.check(agent_id, "delete", path)
        return delete_file(path)

    def create_dir(self, agent_id: str, path: str) -> str:
        """Create a directory as agent_id (checks create_dir permission first)."""
        import sys
        sys.path.insert(0, str(AGENCY_DIR / "tools"))
        from file_tools import create_dir
        self.check(agent_id, "create_dir", path)
        return create_dir(path)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._default_policy = data.get("default_policy", "deny")
        self._log_denied = data.get("log_denied", True)
        self._log_granted = data.get("log_granted", False)

        for agent_id, agent_data in data.get("agents", {}).items():
            self._rules[agent_id] = agent_data.get("rules", [])

    def _normalise(self, path: str) -> str:
        """
        Normalise path to be relative to ~/agency/.
        Strips the absolute prefix if given.
        """
        p = Path(path).expanduser()
        try:
            return str(p.relative_to(AGENCY_DIR))
        except ValueError:
            pass
        # Already relative — return as-is
        return str(Path(path))

    def _evaluate(self, agent_id: str, op: str, rel_path: str) -> bool:
        """
        Evaluate rules top-to-bottom. First match wins.
        Returns True (allow) or False (deny).
        """
        rules = self._rules.get(agent_id)
        if rules is None:
            # Agent not in registry → fall back to default policy
            return self._default_policy == "allow"

        for rule in rules:
            pattern = rule.get("path", "")
            ops = rule.get("ops", [])

            # Expand implicit ops: "write" covers "append" and "create_dir"
            expanded_ops = set(ops)
            if "write" in ops:
                expanded_ops.add("append")
                expanded_ops.add("create_dir")

            if op not in expanded_ops:
                continue

            # Match path pattern (fnmatch glob)
            if fnmatch.fnmatch(rel_path, pattern):
                return True

            # Also match if the path starts with a directory pattern
            # e.g. pattern "clients/**" should match "clients/refine-clinic/content/post.md"
            if "**" in pattern:
                # Convert ** to fnmatch-compatible
                fn_pattern = pattern.replace("**", "*")
                if fnmatch.fnmatch(rel_path, fn_pattern):
                    return True
                # Also try prefix match for directories
                prefix = pattern.split("**")[0].rstrip("/")
                if rel_path.startswith(prefix + "/") or rel_path == prefix:
                    return True

        return self._default_policy == "allow"

    def _write_denied_log(self, agent: str, op: str, path: str, reason: str) -> None:
        """Append a denied access entry to memory/denied_access.log."""
        try:
            DENIED_LOG.parent.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{ts}] DENIED agent={agent} op={op} path={path} reason={reason}\n"
            with DENIED_LOG.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass  # Never crash the system over a log write failure


# ── Singleton ─────────────────────────────────────────────────────────────────

_permissions_instance: Optional[FilePermissions] = None


def load_permissions(permissions_path: Path = PERMISSIONS_PATH) -> FilePermissions:
    """Return a singleton FilePermissions instance (lazy-loaded)."""
    global _permissions_instance
    if _permissions_instance is None:
        _permissions_instance = FilePermissions(permissions_path)
    return _permissions_instance
