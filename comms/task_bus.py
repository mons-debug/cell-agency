"""
Cell Agency — Agent Communication Protocol
==========================================
File-based async task bus for inter-agent work handoff.

Agents post tasks to each other's virtual inboxes.
Tasks flow autonomously through the pipeline without Moncef's manual intervention.

Storage layout:
  memory/tasks/
    pending/   ← new tasks, unclaimed
    active/    ← claimed, being worked on
    done/      ← completed with outputs
    failed/    ← failed with reason

Task filename: task_YYYYMMDD_HHMMSS_<6hex>.json

Usage:
    from comms import load_task_bus

    bus = load_task_bus()

    # Content Creator hands off to QA Gate after finishing a draft
    task_id = bus.send(
        from_agent="content_creator",
        to_agent="qa_gate",
        title="QA Review: Ramadan Instagram Post",
        description="Caption written for refine-clinic Ramadan campaign.",
        inputs={"content": "...", "platform": "instagram", "client_id": "refine-clinic"},
        skill="content-forge",
        priority=4,
    )

    # QA Gate checks its inbox and claims the task
    tasks = bus.list_inbox("qa_gate", "pending")
    task  = bus.claim("qa_gate", tasks[0].task_id)

    # QA Gate completes review and passes to Social Media Manager
    bus.complete(task_id, outputs={"approved": True, "final_content": "..."})
    bus.send("qa_gate", "social_media_manager", "Publish: Ramadan Post", ...)
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

AGENCY_DIR = Path.home() / "agency"
TASKS_DIR  = AGENCY_DIR / "memory" / "tasks"

VALID_STATUSES = {"pending", "active", "done", "failed"}
STATUS_DIRS: dict[str, Path] = {
    "pending": TASKS_DIR / "pending",
    "active":  TASKS_DIR / "active",
    "done":    TASKS_DIR / "done",
    "failed":  TASKS_DIR / "failed",
}

logger = logging.getLogger(__name__)


# ── Task ───────────────────────────────────────────────────────────────────────

@dataclass
class Task:
    """A single unit of work passed between agents."""

    task_id:    str
    title:      str
    from_agent: str
    to_agent:   str
    status:     str          # pending | active | done | failed
    created_at: str          # ISO 8601
    updated_at: str

    description: str = ""
    skill:       str = ""    # which skill/crew this relates to
    priority:    int = 3     # 1 (low) – 5 (urgent)

    inputs:   dict = field(default_factory=dict)   # task input payload
    outputs:  dict = field(default_factory=dict)   # filled on complete/fail
    thread:   list = field(default_factory=list)   # [{from, message, timestamp}]
    metadata: dict = field(default_factory=dict)   # flexible extra data

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        return cls(
            task_id=d["task_id"],
            title=d["title"],
            from_agent=d["from_agent"],
            to_agent=d["to_agent"],
            status=d["status"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            description=d.get("description", ""),
            skill=d.get("skill", ""),
            priority=d.get("priority", 3),
            inputs=d.get("inputs", {}),
            outputs=d.get("outputs", {}),
            thread=d.get("thread", []),
            metadata=d.get("metadata", {}),
        )

    def summary(self) -> str:
        thread_count = len(self.thread)
        replies = f" | {thread_count} repl{'y' if thread_count == 1 else 'ies'}" if thread_count else ""
        return (
            f"[{self.task_id}] {self.title}\n"
            f"  from={self.from_agent} → to={self.to_agent} | "
            f"status={self.status} | priority={self.priority}/5 | "
            f"skill={self.skill or '—'}{replies}\n"
            f"  created={self.created_at[:16]}"
        )


# ── TaskBus ────────────────────────────────────────────────────────────────────

class TaskBus:
    """
    File-based inter-agent task bus.

    Agents post tasks to each other's virtual inboxes.
    Tasks move through lifecycle: pending → active → done | failed

    Thread-safety note:
        Uses atomic file writes (write-then-rename) for concurrent safety.
        Suitable for single-machine deployments. For distributed agents,
        replace with a proper message queue (Redis, etc.).
    """

    def __init__(self) -> None:
        self._ensure_dirs()

    # ── Public API ─────────────────────────────────────────────────────────────

    def send(
        self,
        from_agent:  str,
        to_agent:    str,
        title:       str,
        description: str = "",
        inputs:      Optional[dict] = None,
        skill:       str = "",
        priority:    int = 3,
        metadata:    Optional[dict] = None,
    ) -> str:
        """
        Post a new task to to_agent's inbox.

        Args:
            from_agent:  Sender agent id (e.g. 'content_creator')
            to_agent:    Recipient agent id (e.g. 'qa_gate')
            title:       Short descriptive title
            description: Full task description
            inputs:      Dict with task payload (content, client_id, etc.)
            skill:       Which agency skill this task relates to
            priority:    1 (low) to 5 (urgent), default 3
            metadata:    Any extra tracking data

        Returns:
            task_id — pass to claim(), complete(), reply(), etc.
        """
        ts = datetime.now()
        short_id = uuid.uuid4().hex[:6]
        task_id  = f"task_{ts.strftime('%Y%m%d_%H%M%S')}_{short_id}"
        now      = ts.isoformat()

        task = Task(
            task_id=task_id,
            title=title,
            from_agent=from_agent,
            to_agent=to_agent,
            status="pending",
            created_at=now,
            updated_at=now,
            description=description,
            skill=skill,
            priority=min(max(priority, 1), 5),
            inputs=inputs or {},
            metadata=metadata or {},
        )
        self._write(task, "pending")
        logger.info(f"[TASK SENT] {from_agent} → {to_agent}: {task_id} — {title}")
        return task_id

    def list_inbox(self, agent_id: str, status: str = "pending") -> list[Task]:
        """
        Return tasks addressed to agent_id in the given status folder.

        Args:
            agent_id: Agent whose inbox to check
            status:   'pending' | 'active' | 'done' | 'failed' | 'all'

        Returns:
            List of Task objects sorted by priority (desc) then created_at (asc)
        """
        statuses = list(VALID_STATUSES) if status == "all" else [status]
        tasks: list[Task] = []
        for s in statuses:
            folder = STATUS_DIRS.get(s)
            if not folder or not folder.exists():
                continue
            for path in sorted(folder.glob("task_*.json")):
                try:
                    task = self._load_file(path)
                    if task.to_agent == agent_id:
                        tasks.append(task)
                except Exception:
                    pass
        return sorted(tasks, key=lambda t: (-t.priority, t.created_at))

    def claim(self, agent_id: str, task_id: str) -> Task:
        """
        Claim a pending task — moves it pending → active.

        Args:
            agent_id: Must match task.to_agent
            task_id:  Task to claim

        Raises:
            FileNotFoundError: task not found
            PermissionError:   task belongs to different agent
            ValueError:        task is not in 'pending' status
        """
        task = self._find(task_id)
        if task.to_agent != agent_id:
            raise PermissionError(
                f"Task {task_id} belongs to '{task.to_agent}', not '{agent_id}'"
            )
        if task.status != "pending":
            raise ValueError(
                f"Task {task_id} is '{task.status}' — can only claim 'pending' tasks"
            )
        old_status   = task.status
        task.status   = "active"
        task.updated_at = datetime.now().isoformat()
        self._move(task, old_status, "active")
        logger.info(f"[TASK CLAIMED] {agent_id} claimed {task_id}")
        return task

    def complete(
        self,
        task_id: str,
        outputs: Optional[dict] = None,
        note:    str = "",
    ) -> Task:
        """
        Mark task as done — moves active → done.

        Args:
            task_id: Task to complete
            outputs: Result data (approved_content, score, report_path, etc.)
            note:    Optional completion note added to thread
        """
        task = self._find(task_id)
        old_status      = task.status
        task.status      = "done"
        task.updated_at  = datetime.now().isoformat()
        task.outputs     = outputs or {}
        if note:
            task.thread.append({
                "from":      task.to_agent,
                "message":   f"[COMPLETED] {note}",
                "timestamp": task.updated_at,
            })
        self._move(task, old_status, "done")
        logger.info(f"[TASK DONE] {task_id} — {task.title}")
        return task

    def fail(self, task_id: str, reason: str = "") -> Task:
        """
        Mark task as failed — moves active → failed.

        Args:
            task_id: Task to fail
            reason:  Explanation of the failure
        """
        task = self._find(task_id)
        old_status          = task.status
        task.status          = "failed"
        task.updated_at      = datetime.now().isoformat()
        task.outputs["failure_reason"] = reason
        if reason:
            task.thread.append({
                "from":      task.to_agent,
                "message":   f"[FAILED] {reason}",
                "timestamp": task.updated_at,
            })
        self._move(task, old_status, "failed")
        logger.warning(f"[TASK FAILED] {task_id}: {reason}")
        return task

    def reply(self, task_id: str, from_agent: str, message: str) -> Task:
        """
        Add a message to a task's thread.
        Task stays in its current status — this is for questions / feedback / updates.

        Args:
            task_id:    Task to reply to
            from_agent: Agent posting the reply
            message:    Reply content
        """
        task = self._find(task_id)
        task.thread.append({
            "from":      from_agent,
            "message":   message,
            "timestamp": datetime.now().isoformat(),
        })
        task.updated_at = datetime.now().isoformat()
        # Write back in same status folder
        self._write(task, task.status)
        return task

    def get(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID regardless of status.
        Returns None if not found.
        """
        try:
            return self._find(task_id)
        except FileNotFoundError:
            return None

    def list_all_pending(self) -> list[Task]:
        """
        Return all pending tasks across all agents.
        Nadia uses this for agency-wide oversight.
        """
        tasks: list[Task] = []
        folder = STATUS_DIRS["pending"]
        if not folder.exists():
            return []
        for path in sorted(folder.glob("task_*.json")):
            try:
                tasks.append(self._load_file(path))
            except Exception:
                pass
        return sorted(tasks, key=lambda t: (-t.priority, t.created_at))

    # ── Internals ──────────────────────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        for d in STATUS_DIRS.values():
            d.mkdir(parents=True, exist_ok=True)

    def _task_path(self, task_id: str, status: str) -> Path:
        return STATUS_DIRS[status] / f"{task_id}.json"

    def _write(self, task: Task, status: str) -> None:
        """Write task JSON to the correct status folder."""
        path = self._task_path(task.task_id, status)
        # Atomic write: write to temp then rename
        tmp = path.with_suffix(".tmp")
        tmp.write_text(task.to_json(), encoding="utf-8")
        tmp.rename(path)

    def _load_file(self, path: Path) -> Task:
        return Task.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _find(self, task_id: str) -> Task:
        """Search all status folders for task_id. Raises FileNotFoundError if missing."""
        for status, folder in STATUS_DIRS.items():
            path = folder / f"{task_id}.json"
            if path.exists():
                return self._load_file(path)
        raise FileNotFoundError(f"Task '{task_id}' not found in any status folder")

    def _move(self, task: Task, from_status: str, to_status: str) -> None:
        """Move task file from one status folder to another."""
        old_path = self._task_path(task.task_id, from_status)
        if old_path.exists():
            old_path.unlink()
        self._write(task, to_status)


# ── Singleton ──────────────────────────────────────────────────────────────────

_task_bus_instance: Optional[TaskBus] = None


def load_task_bus() -> TaskBus:
    """Return singleton TaskBus (lazy-loaded, creates task dirs on first call)."""
    global _task_bus_instance
    if _task_bus_instance is None:
        _task_bus_instance = TaskBus()
    return _task_bus_instance
