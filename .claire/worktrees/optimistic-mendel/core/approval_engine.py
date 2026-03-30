"""
Cell Agency — Approval Engine (Phase 5)

Manages a queue of items that require Moncef's explicit sign-off before
the agency takes action (publish, spend budget, send client comms).

Approval tasks are stored as JSON in ~/agency/approval_queue/.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# ─── STATUS ───────────────────────────────────────────────────────────────────

class ApprovalStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED   = "edited"   # Moncef approved with edits


# ─── DATA MODEL ───────────────────────────────────────────────────────────────

class ApprovalTask:
    """An item waiting for Moncef's approval."""

    def __init__(
        self,
        title: str,
        content: Any,
        task_type: str = "content",
        client_id: str = "",
        workflow_id: str = "",
        submitted_by: str = "nadia",
        priority: str = "normal",
        context: str = "",
    ):
        self.id           = f"appr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
        self.title        = title
        self.content      = content    # The actual thing to approve (text, dict, etc.)
        self.task_type    = task_type  # 'content' | 'ad_campaign' | 'budget' | 'client_comms' | 'publish'
        self.client_id    = client_id
        self.workflow_id  = workflow_id
        self.submitted_by = submitted_by
        self.priority     = priority   # 'low' | 'normal' | 'high' | 'urgent'
        self.context      = context    # Extra context for Moncef

        self.status        = ApprovalStatus.PENDING
        self.submitted_at  = datetime.now().isoformat()
        self.reviewed_at: Optional[str]  = None
        self.reviewed_by: str            = ""
        self.rejection_reason: str       = ""
        self.edited_content: Any         = None
        self.edit_notes: str             = ""

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "title":            self.title,
            "content":          self.content,
            "task_type":        self.task_type,
            "client_id":        self.client_id,
            "workflow_id":      self.workflow_id,
            "submitted_by":     self.submitted_by,
            "priority":         self.priority,
            "context":          self.context,
            "status":           self.status.value,
            "submitted_at":     self.submitted_at,
            "reviewed_at":      self.reviewed_at,
            "reviewed_by":      self.reviewed_by,
            "rejection_reason": self.rejection_reason,
            "edited_content":   self.edited_content,
            "edit_notes":       self.edit_notes,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "ApprovalTask":
        task = cls(
            title=d["title"],
            content=d.get("content"),
            task_type=d.get("task_type", "content"),
            client_id=d.get("client_id", ""),
            workflow_id=d.get("workflow_id", ""),
            submitted_by=d.get("submitted_by", "nadia"),
            priority=d.get("priority", "normal"),
            context=d.get("context", ""),
        )
        task.id               = d["id"]
        task.status           = ApprovalStatus(d.get("status", "pending"))
        task.submitted_at     = d.get("submitted_at", task.submitted_at)
        task.reviewed_at      = d.get("reviewed_at")
        task.reviewed_by      = d.get("reviewed_by", "")
        task.rejection_reason = d.get("rejection_reason", "")
        task.edited_content   = d.get("edited_content")
        task.edit_notes       = d.get("edit_notes", "")
        return task

    def summary(self) -> str:
        """One-line summary for Telegram notification."""
        icon = {"pending": "⏳", "approved": "✅", "rejected": "❌", "edited": "✏️"}.get(
            self.status.value, "📋"
        )
        age = ""
        try:
            submitted = datetime.fromisoformat(self.submitted_at)
            mins = int((datetime.now() - submitted).total_seconds() / 60)
            age = f" ({mins}m ago)" if mins < 60 else f" ({mins // 60}h ago)"
        except Exception:
            pass
        return f"{icon} [{self.priority.upper()}] {self.title} — {self.client_id}{age}"


# ─── ENGINE ───────────────────────────────────────────────────────────────────

class ApprovalEngine:
    """
    Manages the approval queue stored in ~/agency/approval_queue/.
    Each approval task is a JSON file named {approval_id}.json.
    """

    QUEUE_DIR = Path.home() / "agency" / "approval_queue"

    def __init__(self):
        self.QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    # ── CRUD ───────────────────────────────────────────────────────────────

    def save(self, task: ApprovalTask) -> None:
        path = self.QUEUE_DIR / f"{task.id}.json"
        path.write_text(task.to_json(), encoding="utf-8")

    def load(self, approval_id: str) -> Optional[ApprovalTask]:
        path = self.QUEUE_DIR / f"{approval_id}.json"
        if not path.exists():
            return None
        return ApprovalTask.from_dict(json.loads(path.read_text(encoding="utf-8")))

    # ── OPERATIONS ─────────────────────────────────────────────────────────

    def submit(
        self,
        title: str,
        content: Any,
        task_type: str = "content",
        client_id: str = "",
        workflow_id: str = "",
        submitted_by: str = "nadia",
        priority: str = "normal",
        context: str = "",
    ) -> ApprovalTask:
        """Create and store a new approval task. Returns the task."""
        task = ApprovalTask(
            title=title,
            content=content,
            task_type=task_type,
            client_id=client_id,
            workflow_id=workflow_id,
            submitted_by=submitted_by,
            priority=priority,
            context=context,
        )
        self.save(task)
        return task

    def approve(self, approval_id: str, reviewed_by: str = "moncef") -> ApprovalTask:
        """Approve a pending task. Resumes workflow if linked."""
        task = self._require(approval_id)
        if task.status != ApprovalStatus.PENDING:
            raise ValueError(f"Task '{approval_id}' is not pending (status={task.status})")
        task.status      = ApprovalStatus.APPROVED
        task.reviewed_at = datetime.now().isoformat()
        task.reviewed_by = reviewed_by
        self.save(task)

        # Resume linked workflow
        if task.workflow_id:
            self._resume_workflow(task.workflow_id)

        return task

    def reject(
        self,
        approval_id: str,
        reason: str = "",
        reviewed_by: str = "moncef",
    ) -> ApprovalTask:
        """Reject a pending task."""
        task = self._require(approval_id)
        if task.status != ApprovalStatus.PENDING:
            raise ValueError(f"Task '{approval_id}' is not pending (status={task.status})")
        task.status           = ApprovalStatus.REJECTED
        task.reviewed_at      = datetime.now().isoformat()
        task.reviewed_by      = reviewed_by
        task.rejection_reason = reason
        self.save(task)

        # Mark workflow as rejected
        if task.workflow_id:
            self._reject_workflow(task.workflow_id, reason)

        return task

    def edit_and_approve(
        self,
        approval_id: str,
        edited_content: Any,
        edit_notes: str = "",
        reviewed_by: str = "moncef",
    ) -> ApprovalTask:
        """Approve with edits — stores the corrected content."""
        task = self._require(approval_id)
        task.status         = ApprovalStatus.EDITED
        task.edited_content = edited_content
        task.edit_notes     = edit_notes
        task.reviewed_at    = datetime.now().isoformat()
        task.reviewed_by    = reviewed_by
        self.save(task)

        if task.workflow_id:
            self._resume_workflow(task.workflow_id)

        return task

    # ── QUERIES ────────────────────────────────────────────────────────────

    def list_pending(self) -> list[ApprovalTask]:
        """Return all pending tasks, sorted by priority then submission time."""
        tasks = self._load_all(status="pending")
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        return sorted(tasks, key=lambda t: (priority_order.get(t.priority, 2), t.submitted_at))

    def list_all(self, status: str = "", limit: int = 50) -> list[ApprovalTask]:
        return self._load_all(status=status, limit=limit)

    def pending_count(self) -> int:
        return len([
            p for p in self.QUEUE_DIR.glob("appr_*.json")
            if '"status": "pending"' in p.read_text(encoding="utf-8")
        ])

    def format_pending_summary(self) -> str:
        """Markdown summary of pending approvals — for Telegram heartbeat."""
        tasks = self.list_pending()
        if not tasks:
            return "✅ No pending approvals."
        lines = [f"📋 **{len(tasks)} pending approval(s):**"]
        for t in tasks[:10]:
            lines.append(f"  • {t.summary()}")
            lines.append(f"    ID: `{t.id}`")
        return "\n".join(lines)

    # ── INTERNALS ──────────────────────────────────────────────────────────

    def _require(self, approval_id: str) -> ApprovalTask:
        task = self.load(approval_id)
        if task is None:
            raise FileNotFoundError(f"Approval task '{approval_id}' not found")
        return task

    def _load_all(self, status: str = "", limit: int = 100) -> list[ApprovalTask]:
        results = []
        for p in sorted(self.QUEUE_DIR.glob("appr_*.json"), reverse=True):
            try:
                text = p.read_text(encoding="utf-8")
                if status and f'"status": "{status}"' not in text:
                    continue
                results.append(ApprovalTask.from_dict(json.loads(text)))
                if len(results) >= limit:
                    break
            except Exception:
                continue
        return results

    def _resume_workflow(self, workflow_id: str) -> None:
        try:
            from .workflow_engine import get_engine
            engine = get_engine()
            engine.approve(workflow_id)
        except Exception:
            pass

    def _reject_workflow(self, workflow_id: str, reason: str) -> None:
        try:
            from .workflow_engine import get_engine
            engine = get_engine()
            engine.reject(workflow_id, reason)
        except Exception:
            pass


# ─── SINGLETON ────────────────────────────────────────────────────────────────

_approval_engine: Optional[ApprovalEngine] = None


def get_approval_engine() -> ApprovalEngine:
    global _approval_engine
    if _approval_engine is None:
        _approval_engine = ApprovalEngine()
    return _approval_engine
