"""
Cell Agency — Agent Capability Registry
=========================================
Query the registry to answer:
  - "Which agent handles X task?"
  - "What tools does agent X have?"
  - "Which agents are in department Y?"
  - "Which agents need approval before acting?"
  - "What inputs does agent X need?"
  - "Which agents can handle this tool namespace?"

Usage:
    from registry import load_registry

    reg = load_registry()
    agent = reg.get("content_creator")
    print(agent.capabilities)

    handlers = reg.find_by_task("write_instagram_caption")
    ready = reg.find_ready(missing_env=["SERPER_API_KEY"])
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

REGISTRY_PATH = Path(__file__).parent / "agent_registry.yaml"


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class AgentProfile:
    """Full profile for a single agent."""
    id: str
    role: str
    department: str
    crew_file: str
    llm: str
    allow_delegation: bool
    approval_required: bool
    description: str
    capabilities: list[str]
    handles_tasks: list[str]
    tools: list[str]
    input_needs: dict          # {"required": [...], "optional": [...]}
    output_formats: list[str]
    languages: list[str]
    approval_triggers: list[str] = field(default_factory=list)
    env_required: list[str] = field(default_factory=list)
    env_optional: list[str] = field(default_factory=list)
    quality_rules: list[str] = field(default_factory=list)

    @property
    def resolved_llm(self) -> str:
        """Return the model ID as-is — gpt-4o and gpt-4o-mini are the real model IDs."""
        return self.llm

    @property
    def tool_namespaces(self) -> list[str]:
        """Return unique tool namespaces this agent uses (agency, social, ads, design, deploy, crew)."""
        return list({t.split(".")[0] for t in self.tools})

    def is_env_ready(self, available_env: Optional[list[str]] = None) -> tuple[bool, list[str]]:
        """
        Check if all required env vars are set.

        Args:
            available_env: List of env var names that are set.
                           If None, checks os.environ directly.

        Returns:
            (is_ready, missing_vars)
        """
        env = available_env or list(os.environ.keys())
        missing = [v for v in self.env_required if v not in env]
        return len(missing) == 0, missing

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "department": self.department,
            "crew_file": self.crew_file,
            "llm": self.resolved_llm,
            "allow_delegation": self.allow_delegation,
            "approval_required": self.approval_required,
            "approval_triggers": self.approval_triggers,
            "description": self.description.strip(),
            "capabilities": self.capabilities,
            "handles_tasks": self.handles_tasks,
            "tools": self.tools,
            "tool_namespaces": self.tool_namespaces,
            "input_needs": self.input_needs,
            "output_formats": self.output_formats,
            "languages": self.languages,
            "env_required": self.env_required,
            "env_optional": self.env_optional,
            "quality_rules": self.quality_rules,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def summary(self) -> str:
        """One-line summary for router/nadia context injection."""
        caps = ", ".join(self.capabilities[:4])
        return (
            f"{self.id} ({self.role}, {self.department}): "
            f"handles={self.handles_tasks}, caps=[{caps}...]"
        )


# ── Registry ──────────────────────────────────────────────────────────────────

class AgentRegistry:
    """
    In-memory registry of all 22 agents.
    Supports multiple query patterns for routing and orchestration.
    """

    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self._path = registry_path
        self._agents: dict[str, AgentProfile] = {}
        self._meta: dict = {}
        self._load()

    # ── Public query API ──────────────────────────────────────────────────────

    def get(self, agent_id: str) -> Optional[AgentProfile]:
        """Get agent profile by ID (e.g. 'content_creator')."""
        return self._agents.get(agent_id)

    def all(self) -> list[AgentProfile]:
        """Return all agents."""
        return list(self._agents.values())

    def by_department(self, department: str) -> list[AgentProfile]:
        """
        Return all agents in a department.
        Departments: management, strategy, creative, dev, marketing_ops
        """
        return [a for a in self._agents.values() if a.department == department]

    def find_by_task(self, task_name: str) -> list[AgentProfile]:
        """Return agents that handle a specific task name."""
        return [
            a for a in self._agents.values()
            if task_name in a.handles_tasks
        ]

    def find_by_capability(self, capability: str) -> list[AgentProfile]:
        """Return agents that have a specific capability (partial match)."""
        cap_lower = capability.lower()
        return [
            a for a in self._agents.values()
            if any(cap_lower in c.lower() for c in a.capabilities)
        ]

    def find_by_tool(self, tool_name: str) -> list[AgentProfile]:
        """Return agents that have a specific tool."""
        return [
            a for a in self._agents.values()
            if tool_name in a.tools
        ]

    def find_by_tool_namespace(self, namespace: str) -> list[AgentProfile]:
        """
        Return agents that use a tool namespace (e.g. 'social', 'ads', 'design').
        """
        return [
            a for a in self._agents.values()
            if namespace in a.tool_namespaces
        ]

    def find_ready(self, available_env: Optional[list[str]] = None) -> list[AgentProfile]:
        """Return agents whose required env vars are all set."""
        return [
            a for a in self._agents.values()
            if a.is_env_ready(available_env)[0]
        ]

    def find_blocked(self, available_env: Optional[list[str]] = None) -> list[tuple[AgentProfile, list[str]]]:
        """Return (agent, missing_vars) for agents blocked by missing env vars."""
        result = []
        for a in self._agents.values():
            ready, missing = a.is_env_ready(available_env)
            if not ready:
                result.append((a, missing))
        return result

    def find_requiring_approval(self) -> list[AgentProfile]:
        """Return agents that require Moncef's ✅ approval before acting."""
        return [a for a in self._agents.values() if a.approval_required]

    def department_summary(self) -> dict[str, list[str]]:
        """Return {department: [agent_ids]} summary."""
        summary: dict[str, list[str]] = {}
        for a in self._agents.values():
            summary.setdefault(a.department, []).append(a.id)
        return summary

    def capability_map(self) -> dict[str, str]:
        """Return {capability: agent_id} for all unique capabilities."""
        result = {}
        for a in self._agents.values():
            for cap in a.capabilities:
                result[cap] = a.id
        return result

    def status_report(self, available_env: Optional[list[str]] = None) -> str:
        """
        Return a human-readable status report of all agents.
        Shows which are ready vs blocked by missing env vars.
        """
        env = available_env or list(os.environ.keys())
        lines = ["## Agency Agent Status\n"]

        for dept in ["management", "strategy", "creative", "dev", "marketing_ops"]:
            agents = self.by_department(dept)
            if not agents:
                continue
            lines.append(f"### {dept.replace('_', ' ').title()}")
            for a in agents:
                ready, missing = a.is_env_ready(env)
                status = "✅ ready" if ready else f"⚠️ missing: {', '.join(missing)}"
                approval = " 🔒 needs-approval" if a.approval_required else ""
                lines.append(f"- **{a.id}** ({a.role}): {status}{approval}")
            lines.append("")

        return "\n".join(lines)

    def reload(self) -> None:
        """Hot-reload the registry from disk."""
        self._agents.clear()
        self._load()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._meta = data.get("meta", {})

        for raw in data.get("agents", []):
            profile = AgentProfile(
                id=raw["id"],
                role=raw["role"],
                department=raw["department"],
                crew_file=raw["crew_file"],
                llm=raw.get("llm", "gpt-4o-mini"),
                allow_delegation=raw.get("allow_delegation", False),
                approval_required=raw.get("approval_required", False),
                approval_triggers=raw.get("approval_triggers", []),
                description=raw.get("description", ""),
                capabilities=raw.get("capabilities", []),
                handles_tasks=raw.get("handles_tasks", []),
                tools=raw.get("tools", []),
                input_needs=raw.get("input_needs", {"required": [], "optional": []}),
                output_formats=raw.get("output_formats", []),
                languages=raw.get("languages", ["en"]),
                env_required=raw.get("env_required", []),
                env_optional=raw.get("env_optional", []),
                quality_rules=raw.get("quality_rules", []),
            )
            self._agents[profile.id] = profile


# ── Singleton loader ──────────────────────────────────────────────────────────

_registry_instance: Optional[AgentRegistry] = None


def load_registry(registry_path: Path = REGISTRY_PATH) -> AgentRegistry:
    """
    Return a singleton AgentRegistry instance (lazy-loaded).
    Call registry.reload() to hot-reload without restarting.
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentRegistry(registry_path)
    return _registry_instance
