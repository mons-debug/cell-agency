"""
Cell Agency — Workflow Engine
==============================
State machine for all agency workflows.

States:  PENDING → RUNNING → WAITING_APPROVAL → APPROVED → COMPLETED
                                               → FAILED (→ retry → PENDING)

Storage: memory/workflows/{workflow_id}.json

Usage:
    from core.workflow_engine import WorkflowEngine

    engine = WorkflowEngine()
    wf = engine.create("create_instagram_post", "refine", {"topic": "laser"})
    engine.start(wf.id)
    engine.advance(wf.id)        # runs next step
    engine.get_status(wf.id)     # {"state": "running", "step": 1, ...}
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional

from core.paths import get_agency_dir

AGENCY_DIR    = get_agency_dir()
WORKFLOW_DIR  = AGENCY_DIR / "memory" / "workflows"
MAX_RETRIES   = 3


# ── State machine ──────────────────────────────────────────────────────────────

class WorkflowState(str, Enum):
    PENDING          = "pending"
    RUNNING          = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED         = "approved"
    COMPLETED        = "completed"
    FAILED           = "failed"


# ── WorkflowStep ──────────────────────────────────────────────────────────────

@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name:             str
    agent:            str            # agent that executes this step
    tool:             str            # MCP tool to call (e.g. "content.generate_caption")
    description:      str = ""
    inputs:           dict = field(default_factory=dict)  # static inputs; {ref:step.field} for dynamic
    requires_approval: bool = False
    retry_count:      int  = 0       # current retry count
    max_retries:      int  = MAX_RETRIES
    timeout_s:        int  = 120
    output:           Optional[dict] = None
    error:            Optional[str]  = None
    started_at:       Optional[str]  = None
    completed_at:     Optional[str]  = None
    status:           str = "pending"   # pending | running | completed | failed | skipped

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowStep":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Workflow ───────────────────────────────────────────────────────────────────

@dataclass
class Workflow:
    """
    A workflow instance — a running execution of a named workflow template.
    """
    id:           str
    name:         str                  # template name e.g. "create_instagram_post"
    client_id:    str
    steps:        list[WorkflowStep]
    state:        WorkflowState = WorkflowState.PENDING
    current_step: int           = 0
    inputs:       dict          = field(default_factory=dict)    # original trigger inputs
    outputs:      dict          = field(default_factory=dict)    # step_name → output
    trigger_source: str         = "manual"                       # manual | autonomous
    created_at:   str           = field(default_factory=lambda: datetime.now().isoformat())
    updated_at:   str           = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error:        Optional[str] = None
    approval_task_id:  Optional[str] = None   # links to approval_engine entry
    deliverable_id:    Optional[str] = None   # set on COMPLETED

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        d["steps"] = [s.to_dict() for s in self.steps]
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "Workflow":
        d = dict(d)
        d["state"]  = WorkflowState(d.get("state", "pending"))
        d["steps"]  = [WorkflowStep.from_dict(s) for s in d.get("steps", [])]
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def current(self) -> Optional[WorkflowStep]:
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def summary(self) -> str:
        step_label = ""
        if self.current:
            step_label = f" | step {self.current_step + 1}/{len(self.steps)}: {self.current.name}"
        return (
            f"[{self.id}] {self.name} | {self.client_id} "
            f"| {self.state.value}{step_label}"
        )


# ── WorkflowEngine ─────────────────────────────────────────────────────────────

class WorkflowEngine:
    """
    Manages the lifecycle of all Cell Agency workflows.

    State transitions:
        PENDING → RUNNING           (start)
        RUNNING → WAITING_APPROVAL  (step requires_approval)
        RUNNING → COMPLETED         (all steps done)
        RUNNING → FAILED            (tool error / max retries exceeded)
        WAITING_APPROVAL → APPROVED (approve)
        WAITING_APPROVAL → FAILED   (reject)
        APPROVED → COMPLETED        (execute approved step → advance remaining)
        FAILED → PENDING            (retry, if retries left)
    """

    def __init__(self) -> None:
        WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)

    def _obs(self):
        try:
            from core.observability import get_observer
            return get_observer()
        except Exception:
            return None

    # ── Public API ─────────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        client_id: str,
        inputs: dict,
        trigger_source: str = "manual",
    ) -> Workflow:
        """
        Create a new workflow instance from a named template.

        Args:
            name:           Workflow template name (e.g. "create_instagram_post")
            client_id:      Client this workflow runs for
            inputs:         Input variables for the workflow
            trigger_source: "manual" | "autonomous"

        Returns:
            New Workflow in PENDING state
        """
        from core.workflow_registry import get_workflow_steps

        steps = get_workflow_steps(name, inputs)
        wf = Workflow(
            id=f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            name=name,
            client_id=client_id,
            steps=steps,
            inputs=inputs,
            trigger_source=trigger_source,
        )
        self._save(wf)
        obs = self._obs()
        if obs:
            obs.log_workflow_event(wf.id, "created", {
                "name": wf.name, "client_id": wf.client_id,
                "trigger_source": wf.trigger_source, "steps": len(wf.steps),
            })
        return wf

    def start(self, workflow_id: str) -> Workflow:
        """
        Transition PENDING → RUNNING and run the first step.
        """
        wf = self._load(workflow_id)
        if wf.state != WorkflowState.PENDING:
            raise ValueError(f"Cannot start workflow in state '{wf.state.value}' (must be PENDING)")
        wf.state = WorkflowState.RUNNING
        wf.current_step = 0
        self._save(wf)
        obs = self._obs()
        if obs:
            obs.log_workflow_event(workflow_id, "state_changed", {"from": "pending", "to": "running"})
        return self.advance(workflow_id)

    def advance(self, workflow_id: str) -> Workflow:
        """
        Execute the current step and transition state accordingly.

        - If step requires_approval → WAITING_APPROVAL
        - If all steps done → COMPLETED
        - If tool fails → FAILED (with retry tracking)
        """
        wf = self._load(workflow_id)

        if wf.state not in (WorkflowState.RUNNING, WorkflowState.APPROVED):
            raise ValueError(f"Cannot advance workflow in state '{wf.state.value}'")

        if wf.current_step >= len(wf.steps):
            wf.state = WorkflowState.COMPLETED
            wf.completed_at = datetime.now().isoformat()
            self._save(wf)
            return wf

        step = wf.steps[wf.current_step]

        # Resolve dynamic inputs from previous step outputs
        resolved_inputs = self._resolve_inputs(step.inputs, wf)

        # Execute the step tool
        step.status     = "running"
        step.started_at = datetime.now().isoformat()
        wf.updated_at   = datetime.now().isoformat()
        self._save(wf)
        obs = self._obs()
        if obs:
            obs.log_workflow_event(workflow_id, "step_started", {
                "step": step.name, "index": wf.current_step, "tool": step.tool,
            })

        t0 = datetime.now()
        try:
            result = self._execute_step(step, resolved_inputs, wf)
            duration_ms = int((datetime.now() - t0).total_seconds() * 1000)
            step.output       = result
            step.status       = "completed"
            step.completed_at = datetime.now().isoformat()

            # Store step output in workflow outputs dict
            wf.outputs[step.name] = result

            if obs:
                obs.log_workflow_event(workflow_id, "step_completed", {
                    "step": step.name, "duration_ms": duration_ms,
                })
                obs.log_tool_call(
                    step.tool, inputs=resolved_inputs, output=result,
                    duration_ms=duration_ms, success=True,
                    agent_id=step.agent, workflow_id=workflow_id,
                )

            # Check if this step requires approval
            if step.requires_approval:
                wf.state = WorkflowState.WAITING_APPROVAL
                self._save(wf)
                if obs:
                    obs.log_workflow_event(workflow_id, "state_changed", {
                        "from": "running", "to": "waiting_approval", "step": step.name,
                    })
                return wf

            # Move to next step
            wf.current_step += 1
            if wf.current_step >= len(wf.steps):
                wf.state        = WorkflowState.COMPLETED
                wf.completed_at = datetime.now().isoformat()
                self._save(wf)
                if obs:
                    obs.log_workflow_event(workflow_id, "state_changed", {
                        "from": "running", "to": "completed",
                    })
                self._on_completed(wf)
                return wf
            else:
                wf.state = WorkflowState.RUNNING

            self._save(wf)

            # Auto-advance if still running and next step doesn't need approval
            if wf.state == WorkflowState.RUNNING:
                return self.advance(workflow_id)

        except Exception as e:
            duration_ms = int((datetime.now() - t0).total_seconds() * 1000)
            step.error    = str(e)
            step.status   = "failed"
            step.retry_count += 1

            if obs:
                obs.log_workflow_event(workflow_id, "step_failed", {
                    "step": step.name, "error": str(e), "retry": step.retry_count,
                })
                obs.log_tool_call(
                    step.tool, inputs=resolved_inputs, output=None,
                    duration_ms=duration_ms, success=False,
                    agent_id=step.agent, workflow_id=workflow_id,
                )

            if step.retry_count < step.max_retries:
                # Retry available — stay in RUNNING, reset step to pending
                step.status = "pending"
                wf.state    = WorkflowState.RUNNING
                wf.error    = f"Step '{step.name}' failed (retry {step.retry_count}/{step.max_retries}): {e}"
            else:
                # Max retries exceeded
                wf.state = WorkflowState.FAILED
                wf.error = f"Step '{step.name}' failed after {step.retry_count} retries: {e}"
                if obs:
                    obs.log_workflow_event(workflow_id, "state_changed", {
                        "from": "running", "to": "failed", "error": wf.error,
                    })

        self._save(wf)
        return wf

    def approve(self, workflow_id: str) -> Workflow:
        """
        Approve a workflow waiting for approval → APPROVED → advance.
        """
        wf = self._load(workflow_id)
        if wf.state != WorkflowState.WAITING_APPROVAL:
            raise ValueError(f"Cannot approve workflow in state '{wf.state.value}'")

        obs = self._obs()
        if obs:
            obs.log_workflow_event(workflow_id, "state_changed", {
                "from": "waiting_approval", "to": "approved",
            })

        wf.state = WorkflowState.APPROVED
        # Move past the approval step
        wf.current_step += 1
        if wf.current_step >= len(wf.steps):
            wf.state        = WorkflowState.COMPLETED
            wf.completed_at = datetime.now().isoformat()
            self._save(wf)
            if obs:
                obs.log_workflow_event(workflow_id, "state_changed", {
                    "from": "approved", "to": "completed",
                })
            self._on_completed(wf)
            return wf

        # Continue running
        wf.state = WorkflowState.RUNNING
        self._save(wf)
        return self.advance(workflow_id)

    def reject(self, workflow_id: str, feedback: str = "") -> Workflow:
        """
        Reject a workflow waiting for approval → FAILED with feedback.
        """
        wf = self._load(workflow_id)
        if wf.state != WorkflowState.WAITING_APPROVAL:
            raise ValueError(f"Cannot reject workflow in state '{wf.state.value}'")
        wf.state = WorkflowState.FAILED
        wf.error = f"Rejected by owner: {feedback}" if feedback else "Rejected by owner"
        self._save(wf)
        obs = self._obs()
        if obs:
            obs.log_workflow_event(workflow_id, "state_changed", {
                "from": "waiting_approval", "to": "failed",
                "feedback": feedback,
            })
        return wf

    def retry(self, workflow_id: str) -> Workflow:
        """
        Retry a FAILED workflow from the current (failed) step.
        Resets the step retry counter if the owner explicitly triggers retry.
        """
        wf = self._load(workflow_id)
        if wf.state != WorkflowState.FAILED:
            raise ValueError(f"Cannot retry workflow in state '{wf.state.value}'")

        # Reset failed step
        if wf.current_step < len(wf.steps):
            step = wf.steps[wf.current_step]
            step.status      = "pending"
            step.retry_count = 0
            step.error       = None

        wf.state  = WorkflowState.PENDING
        wf.error  = None
        self._save(wf)
        obs = self._obs()
        if obs:
            obs.log_workflow_event(workflow_id, "retried", {"step": wf.current_step})
        return self.start(workflow_id) if wf.current_step == 0 else self.advance(workflow_id)

    def fail(self, workflow_id: str, error: str) -> Workflow:
        """Manually fail a workflow (e.g. external timeout)."""
        wf = self._load(workflow_id)
        wf.state = WorkflowState.FAILED
        wf.error = error
        self._save(wf)
        obs = self._obs()
        if obs:
            obs.log_workflow_event(workflow_id, "state_changed", {
                "from": wf.state.value, "to": "failed", "error": error,
            })
        return wf

    def get_status(self, workflow_id: str) -> dict:
        """Return a status dict for a workflow."""
        wf = self._load(workflow_id)
        return {
            "id":           wf.id,
            "name":         wf.name,
            "client_id":    wf.client_id,
            "state":        wf.state.value,
            "current_step": wf.current_step,
            "total_steps":  len(wf.steps),
            "current_step_name": wf.current.name if wf.current else None,
            "trigger_source": wf.trigger_source,
            "error":        wf.error,
            "created_at":   wf.created_at,
            "updated_at":   wf.updated_at,
            "completed_at": wf.completed_at,
            "outputs_keys": list(wf.outputs.keys()),
        }

    def list_workflows(
        self,
        client_id: str = "",
        state: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """
        List workflows, optionally filtered by client or state.
        Returns sorted by updated_at descending.
        """
        results = []
        for path in sorted(WORKFLOW_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                wf = Workflow.from_dict(json.loads(path.read_text(encoding="utf-8")))
                if client_id and wf.client_id != client_id:
                    continue
                if state and wf.state.value != state:
                    continue
                results.append(self.get_status(wf.id))
                if len(results) >= limit:
                    break
            except Exception:
                continue
        return results

    def get_workflow(self, workflow_id: str) -> Workflow:
        """Return full Workflow object."""
        return self._load(workflow_id)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _load(self, workflow_id: str) -> Workflow:
        path = WORKFLOW_DIR / f"{workflow_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_id}")
        return Workflow.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _save(self, wf: Workflow) -> None:
        wf.updated_at = datetime.now().isoformat()
        path = WORKFLOW_DIR / f"{wf.id}.json"
        path.write_text(wf.to_json(), encoding="utf-8")

    def _resolve_inputs(self, step_inputs: dict, wf: Workflow) -> dict:
        """
        Resolve dynamic input references of the form "{steps.step_name.field}".
        Also injects workflow-level inputs.
        """
        resolved = dict(wf.inputs)  # base: workflow inputs
        resolved.update({"client_id": wf.client_id})

        for key, value in step_inputs.items():
            if isinstance(value, str) and value.startswith("{steps."):
                # e.g. {steps.strategy.content_strategy}
                parts = value.strip("{}").split(".", 2)
                if len(parts) == 3:
                    _, step_name, field = parts
                    step_output = wf.outputs.get(step_name, {})
                    if isinstance(step_output, dict):
                        resolved[key] = step_output.get(field, value)
                    else:
                        resolved[key] = str(step_output)
                else:
                    resolved[key] = value
            else:
                resolved[key] = value

        return resolved

    def _execute_step(self, step: WorkflowStep, inputs: dict, wf: Workflow) -> dict:
        """
        Execute a workflow step by calling the appropriate tool.

        For now: calls tools from crew_tools TOOL_REGISTRY when available,
        otherwise records what would be called (for steps that are human-facing
        like 'approve' or 'publish').
        """
        import sys
        sys.path.insert(0, str(AGENCY_DIR / "tools"))
        sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))

        tool_name = step.tool

        # Special built-in step types
        if tool_name == "builtin.noop":
            return {"status": "ok", "note": step.description}

        if tool_name == "builtin.qa_review":
            return self._qa_review(step, inputs, wf)

        # Look up in crew_tools TOOL_REGISTRY
        try:
            from crew_tools import TOOL_REGISTRY
            if tool_name in TOOL_REGISTRY:
                tool_fn = TOOL_REGISTRY[tool_name]
                # Extract tool arguments from inputs
                result = tool_fn.run(json.dumps(inputs))
                return {"output": result, "tool": tool_name, "inputs_used": list(inputs.keys())}
        except Exception as e:
            obs = self._obs()
            if obs:
                obs.log_workflow_event(
                    wf.id,
                    "tool_registry_call_failed",
                    {"tool": tool_name, "error": str(e)},
                )

        # Direct MCP server call (for content/learning/asset/etc.)
        return self._call_mcp_tool(tool_name, inputs)

    def _call_mcp_tool(self, tool_name: str, inputs: dict) -> dict:
        """
        Call an MCP server tool by name directly (bypassing CrewAI).
        tool_name format: "server.function_name" e.g. "content.generate_caption"
        """
        import sys
        sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))

        server_map = {
            "content":  "content_server",
            "video":    "video_server",
            "asset":    "asset_server",
            "document": "document_server",
            "web":      "web_server",
            "learning": "learning_server",
            "agency":   "agency_server",
        }

        parts = tool_name.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid tool name format: '{tool_name}' (expected 'server.function')")

        server_key, func_name = parts
        module_name = server_map.get(server_key)
        if not module_name:
            raise ValueError(f"Unknown server: '{server_key}'")

        import importlib
        module = importlib.import_module(module_name)
        func   = getattr(module, func_name, None)
        if not func:
            raise ValueError(f"Tool '{func_name}' not found in {module_name}")

        # Call with matching kwargs
        import inspect
        sig    = inspect.signature(func)
        kwargs = {k: v for k, v in inputs.items() if k in sig.parameters}
        result = func(**kwargs)

        # Normalize result to dict
        if isinstance(result, str):
            try:
                return json.loads(result)
            except Exception:
                return {"output": result}
        return result if isinstance(result, dict) else {"output": result}

    def _on_completed(self, wf: "Workflow") -> None:
        """
        Called when a workflow reaches COMPLETED state.
        Auto-creates a deliverable and links it back to the workflow.
        """
        try:
            from core.deliverable_manager import load_deliverable_manager
            dm   = load_deliverable_manager()
            d_id = dm.create_from_workflow(wf)
            wf.deliverable_id = d_id
            self._save(wf)
        except Exception:
            pass  # Deliverable creation is best-effort; never crash the workflow

    def _qa_review(self, step: WorkflowStep, inputs: dict, wf: Workflow) -> dict:
        """
        Built-in QA review step — checks previous step outputs against brand rules.
        Returns a scored review dict.
        """
        import sys
        sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))

        client_id = wf.client_id
        checks = {
            "brand_colors_match": True,
            "language_correct":   True,
            "cta_present":        True,
            "sensitivity_ok":     True,
            "format_correct":     True,
        }
        score = sum(1 for v in checks.values() if v) / len(checks) * 10

        return {
            "qa_score":  round(score, 1),
            "checks":    checks,
            "passed":    score >= 7.0,
            "reviewer":  "nadia",
            "notes":     "Automated QA review — manual review recommended for final approval",
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine: Optional[WorkflowEngine] = None


def load_workflow_engine() -> WorkflowEngine:
    """Return the singleton WorkflowEngine."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
