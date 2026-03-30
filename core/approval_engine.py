"""
Cell Agency — Approval Engine
===============================
Dedicated approval queue for all high-risk agency actions.

Decouples approval logic from the workflow engine and task bus.
Every action that requires human sign-off goes through here.

Approval required for:
    - Publishing content (posts, reels, stories)
    - Launching or modifying ad campaigns
    - Deploying websites
    - Brand identity changes
    - Client-facing communications
    - Any autonomous action with confidence < 0.75

Storage: approval_queue/{task_id}.json

Usage:
    from core.approval_engine import load_approval_engine

    engine = load_approval_engine()
    task_id = engine.submit(
        action="publish_instagram_post",
        client_id="refine",
        draft_output={"caption": "...", "image_path": "..."},
        confidence=0.88,
        workflow_id="wf_...",
    )
    engine.approve(task_id)          # → triggers workflow.approve()
    engine.reject(task_id, feedback) # → triggers workflow.reject()
    engine.edit(task_id, changes)    # → modify draft before re-approval
    engine.list_pending("refine")    # → list open tasks
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

AGENCY_DIR    = Path.home() / "agency"
QUEUE_DIR     = AGENCY_DIR / "approval_queue"
CONFIDENCE_THRESHOLD = 0.75


# ── Approval status ─────────────────────────────────────────────────────────────

class ApprovalStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED   = "edited"   # modified and re-submitted


# ── ApprovalTask ──────────────────────────────────────────────────────────────

@dataclass
class ApprovalTask:
    """
    A single approval task in the queue.
    """
    task_id:       str
    action:        str                   # e.g. "publish_instagram_post"
    client_id:     str
    draft_output:  dict                  # the output to be approved
    status:        ApprovalStatus = ApprovalStatus.PENDING
    confidence:    float = 0.0           # agent confidence 0.0–1.0
    workflow_id:   Optional[str] = None  # linked workflow (if any)
    workflow_step: Optional[int] = None  # step index in workflow
    trigger_source: str = "manual"       # manual | autonomous
    notes:         str = ""             # agent notes / context
    feedback:      Optional[str] = None  # rejection feedback
    created_at:    str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at:    str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at:   Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "ApprovalTask":
        d = dict(d)
        d["status"] = ApprovalStatus(d.get("status", "pending"))
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def summary(self) -> str:
        conf = f"{self.confidence:.0%}" if self.confidence else "—"
        return (
            f"[{self.task_id}] {self.action} | {self.client_id} "
            f"| {self.status.value} | conf: {conf} | {self.created_at[:16]}"
        )


# ── ApprovalEngine ────────────────────────────────────────────────────────────

class ApprovalEngine:
    """
    Manages the approval queue for Cell Agency.

    Integrates with WorkflowEngine: when a task is approved/rejected,
    the linked workflow is transitioned accordingly.
    """

    def __init__(self) -> None:
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def submit(
        self,
        action: str,
        client_id: str,
        draft_output: dict,
        confidence: float = 0.0,
        workflow_id: Optional[str] = None,
        workflow_step: Optional[int] = None,
        trigger_source: str = "manual",
        notes: str = "",
    ) -> str:
        """
        Submit an item for approval.

        Args:
            action:         What action is being requested (e.g. "publish_instagram_post")
            client_id:      Client this is for
            draft_output:   The draft content/config to be approved
            confidence:     Agent confidence score (0.0–1.0)
            workflow_id:    Linked workflow ID (if triggered from workflow)
            workflow_step:  Step index in the workflow
            trigger_source: "manual" | "autonomous"
            notes:          Context or explanation from the agent

        Returns:
            task_id of the submitted approval task
        """
        task_id = f"apr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        task = ApprovalTask(
            task_id=task_id,
            action=action,
            client_id=client_id,
            draft_output=draft_output,
            confidence=confidence,
            workflow_id=workflow_id,
            workflow_step=workflow_step,
            trigger_source=trigger_source,
            notes=notes,
        )
        self._save(task)
        return task_id

    def approve(self, task_id: str) -> ApprovalTask:
        """
        Approve a pending task.

        If linked to a workflow, transitions the workflow from
        WAITING_APPROVAL → APPROVED → continues execution.

        Args:
            task_id: Approval task ID

        Returns:
            Updated ApprovalTask
        """
        task = self._load(task_id)
        if task.status not in (ApprovalStatus.PENDING, ApprovalStatus.EDITED):
            raise ValueError(f"Cannot approve task '{task_id}' in status '{task.status.value}'")

        task.status      = ApprovalStatus.APPROVED
        task.resolved_at = datetime.now().isoformat()
        self._save(task)

        # Propagate to linked workflow
        if task.workflow_id:
            self._advance_workflow(task.workflow_id, approved=True)

        return task

    def reject(self, task_id: str, feedback: str = "") -> ApprovalTask:
        """
        Reject a pending task.

        If linked to a workflow, transitions to FAILED with feedback.

        Args:
            task_id:  Approval task ID
            feedback: Reason for rejection

        Returns:
            Updated ApprovalTask
        """
        task = self._load(task_id)
        if task.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot reject task '{task_id}' in status '{task.status.value}'")

        task.status      = ApprovalStatus.REJECTED
        task.feedback    = feedback
        task.resolved_at = datetime.now().isoformat()
        self._save(task)

        # Propagate to linked workflow
        if task.workflow_id:
            self._advance_workflow(task.workflow_id, approved=False, feedback=feedback)

        return task

    def edit(self, task_id: str, changes: dict) -> ApprovalTask:
        """
        Edit the draft output of a pending task before approval.

        Merges changes into draft_output and marks status as EDITED.
        The task remains in the approval queue for final approve/reject.

        Args:
            task_id: Approval task ID
            changes: Dict of fields to update in draft_output

        Returns:
            Updated ApprovalTask
        """
        task = self._load(task_id)
        if task.status not in (ApprovalStatus.PENDING, ApprovalStatus.EDITED):
            raise ValueError(f"Cannot edit task '{task_id}' in status '{task.status.value}'")

        task.draft_output.update(changes)
        task.status = ApprovalStatus.EDITED
        self._save(task)
        return task

    def get(self, task_id: str) -> ApprovalTask:
        """Get a specific approval task by ID."""
        return self._load(task_id)

    def list_pending(self, client_id: str = "") -> list[ApprovalTask]:
        """List all pending (and edited) approval tasks, optionally filtered by client."""
        return self._list(statuses=[ApprovalStatus.PENDING, ApprovalStatus.EDITED], client_id=client_id)

    def list_all(self, client_id: str = "", status: str = "") -> list[ApprovalTask]:
        """List all approval tasks, optionally filtered by client and/or status."""
        if status:
            statuses = [ApprovalStatus(status)]
        else:
            statuses = list(ApprovalStatus)
        return self._list(statuses=statuses, client_id=client_id)

    def requires_approval(self, action: str, confidence: float, trigger_source: str = "manual") -> bool:
        """
        Check whether an action requires approval.

        Rules:
          - confidence < CONFIDENCE_THRESHOLD → always requires approval
          - autonomous actions → always requires approval
          - certain high-risk actions → always requires approval
        """
        HIGH_RISK_ACTIONS = {
            "publish_instagram_post",
            "publish_reel",
            "publish_story",
            "publish_carousel",
            "launch_ad_campaign",
            "modify_ad_campaign",
            "pause_ad_campaign",
            "deploy_website",
            "update_website",
            "update_brandkit",
            "update_brand_vault",
            "send_client_communication",
            "send_client_email",
            "send_client_whatsapp",
        }
        if confidence < CONFIDENCE_THRESHOLD:
            return True
        if trigger_source == "autonomous":
            return True
        if action in HIGH_RISK_ACTIONS:
            return True
        return False

    def pending_count(self, client_id: str = "") -> int:
        """Return number of pending approval tasks."""
        return len(self.list_pending(client_id))

    def queue_summary(self) -> str:
        """Return a Markdown summary of the approval queue."""
        pending = self._list(statuses=[ApprovalStatus.PENDING, ApprovalStatus.EDITED])
        if not pending:
            return "**Approval Queue** — empty, nothing awaiting review."

        lines = [
            f"**Approval Queue** — {len(pending)} item(s) awaiting review\n",
            "| ID | Action | Client | Confidence | Source | Age |",
            "|----|--------|--------|------------|--------|-----|",
        ]
        for task in pending:
            conf = f"{task.confidence:.0%}" if task.confidence else "—"
            age  = self._age(task.created_at)
            lines.append(
                f"| `{task.task_id}` | {task.action} | {task.client_id} "
                f"| {conf} | {task.trigger_source} | {age} |"
            )
        return "\n".join(lines)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _load(self, task_id: str) -> ApprovalTask:
        path = QUEUE_DIR / f"{task_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Approval task not found: {task_id}")
        return ApprovalTask.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _save(self, task: ApprovalTask) -> None:
        task.updated_at = datetime.now().isoformat()
        path = QUEUE_DIR / f"{task.task_id}.json"
        path.write_text(task.to_json(), encoding="utf-8")

    def _list(self, statuses: list[ApprovalStatus], client_id: str = "") -> list[ApprovalTask]:
        results = []
        for path in sorted(QUEUE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                task = ApprovalTask.from_dict(json.loads(path.read_text(encoding="utf-8")))
                if task.status not in statuses:
                    continue
                if client_id and task.client_id != client_id:
                    continue
                results.append(task)
            except Exception:
                continue
        return results

    def _advance_workflow(self, workflow_id: str, approved: bool, feedback: str = "") -> None:
        """Propagate approval/rejection decision to the linked workflow."""
        try:
            from core.workflow_engine import load_workflow_engine
            engine = load_workflow_engine()
            if approved:
                engine.approve(workflow_id)
            else:
                engine.reject(workflow_id, feedback)
        except Exception:
            pass  # Workflow may have already transitioned; don't crash the approval

    @staticmethod
    def _age(created_at: str) -> str:
        """Human-readable age string (e.g. '2h ago', '3d ago')."""
        try:
            created = datetime.fromisoformat(created_at)
            delta   = datetime.now() - created
            secs    = int(delta.total_seconds())
            if secs < 60:
                return f"{secs}s"
            if secs < 3600:
                return f"{secs // 60}m"
            if secs < 86400:
                return f"{secs // 3600}h"
            return f"{secs // 86400}d"
        except Exception:
            return "?"


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine: ApprovalEngine | None = None


def load_approval_engine() -> ApprovalEngine:
    """Return singleton ApprovalEngine."""
    global _engine
    if _engine is None:
        _engine = ApprovalEngine()
    return _engine
