"""
Cell Agency — Deliverable Manager
====================================
Structured output storage for all completed workflows.

Every completed workflow auto-creates a deliverable folder:
    deliverables/{client_id}/{workflow_name}_{deliverable_id}/
        metadata.json     — attribution, timeline, performance
        outputs.json      — full step outputs from the workflow
        {content files}   — caption.txt, brief.md, plan.md, etc.

Usage:
    from core.deliverable_manager import load_deliverable_manager

    dm = load_deliverable_manager()
    d_id = dm.create_from_workflow(workflow)
    dm.get(d_id)
    dm.list("refine")
    dm.update_performance(d_id, {"views": 15400, "engagement_rate": 0.092})
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.paths import get_agency_dir

AGENCY_DIR        = get_agency_dir()
DELIVERABLES_DIR  = AGENCY_DIR / "deliverables"
ANALYTICS_DIR     = AGENCY_DIR / "analytics"


# ── DeliverableMetadata ────────────────────────────────────────────────────────

@dataclass
class DeliverableMetadata:
    deliverable_id:  str
    client_id:       str
    workflow_name:   str
    workflow_id:     str
    agents_used:     list[str]       = field(default_factory=list)
    tools_used:      list[str]       = field(default_factory=list)
    files:           list[str]       = field(default_factory=list)   # relative paths
    created_at:      str             = field(default_factory=lambda: datetime.now().isoformat())
    approved_by:     Optional[str]   = None
    approved_at:     Optional[str]   = None
    trigger_source:  str             = "manual"
    performance:     dict            = field(default_factory=dict)
    tags:            list[str]       = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "DeliverableMetadata":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def summary(self) -> str:
        perf = ""
        if self.performance:
            parts = [f"{k}: {v}" for k, v in list(self.performance.items())[:3]]
            perf = " | " + ", ".join(parts)
        return (
            f"[{self.deliverable_id}] {self.workflow_name} | {self.client_id} "
            f"| {self.created_at[:10]}{perf}"
        )


# ── DeliverableManager ────────────────────────────────────────────────────────

class DeliverableManager:
    """
    Creates and manages deliverable folders for completed workflows.

    Each deliverable gets:
        - metadata.json   — attribution and performance
        - outputs.json    — full workflow step outputs
        - content files   — extracted from outputs (caption.txt, brief.md, etc.)
    """

    def __init__(self) -> None:
        DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)
        ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def create_from_workflow(self, workflow) -> str:
        """
        Create a deliverable from a completed Workflow object.
        Called automatically by WorkflowEngine on COMPLETED transition.

        Args:
            workflow: Completed Workflow instance

        Returns:
            deliverable_id
        """
        d_id   = f"del_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        folder = self._folder(workflow.client_id, workflow.name, d_id)
        folder.mkdir(parents=True, exist_ok=True)

        # Collect agents and tools used from step history
        agents_used = list(dict.fromkeys(s.agent for s in workflow.steps))
        tools_used  = list(dict.fromkeys(
            s.tool for s in workflow.steps if not s.tool.startswith("builtin.")
        ))

        # Save outputs.json (full step outputs)
        outputs_path = folder / "outputs.json"
        outputs_path.write_text(
            json.dumps(workflow.outputs, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Extract and save content files from outputs
        saved_files = ["outputs.json"]
        saved_files.extend(self._extract_content_files(folder, workflow.name, workflow.outputs))

        # Build and save metadata
        meta = DeliverableMetadata(
            deliverable_id=d_id,
            client_id=workflow.client_id,
            workflow_name=workflow.name,
            workflow_id=workflow.id,
            agents_used=agents_used,
            tools_used=tools_used,
            files=saved_files,
            trigger_source=workflow.trigger_source,
        )
        (folder / "metadata.json").write_text(meta.to_json(), encoding="utf-8")

        return d_id

    def create(
        self,
        client_id: str,
        workflow_id: str,
        workflow_name: str,
        outputs: dict,
        agents_used: list[str] = None,
        tools_used: list[str] = None,
        trigger_source: str = "manual",
    ) -> str:
        """
        Create a deliverable manually (without a Workflow object).

        Returns:
            deliverable_id
        """
        d_id   = f"del_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        folder = self._folder(client_id, workflow_name, d_id)
        folder.mkdir(parents=True, exist_ok=True)

        outputs_path = folder / "outputs.json"
        outputs_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False), encoding="utf-8")

        saved_files = ["outputs.json"]
        saved_files.extend(self._extract_content_files(folder, workflow_name, outputs))

        meta = DeliverableMetadata(
            deliverable_id=d_id,
            client_id=client_id,
            workflow_name=workflow_name,
            workflow_id=workflow_id,
            agents_used=agents_used or [],
            tools_used=tools_used or [],
            files=saved_files,
            trigger_source=trigger_source,
        )
        (folder / "metadata.json").write_text(meta.to_json(), encoding="utf-8")
        return d_id

    def get(self, deliverable_id: str) -> dict:
        """
        Get a deliverable by ID.

        Returns:
            Dict with metadata + outputs
        """
        meta   = self._load_meta(deliverable_id)
        folder = self._folder(meta.client_id, meta.workflow_name, deliverable_id)

        outputs = {}
        outputs_path = folder / "outputs.json"
        if outputs_path.exists():
            try:
                outputs = json.loads(outputs_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "metadata": meta.to_dict(),
            "outputs":  outputs,
            "folder":   str(folder),
        }

    def list(self, client_id: str = "", workflow_type: str = "", limit: int = 50) -> list[dict]:
        """
        List deliverables, optionally filtered by client or workflow type.
        Returns sorted by most recent first.
        """
        results = []
        search_root = DELIVERABLES_DIR

        for meta_path in sorted(
            search_root.rglob("metadata.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                meta = DeliverableMetadata.from_dict(
                    json.loads(meta_path.read_text(encoding="utf-8"))
                )
                if client_id and meta.client_id != client_id:
                    continue
                if workflow_type and meta.workflow_name != workflow_type:
                    continue
                results.append(meta.to_dict())
                if len(results) >= limit:
                    break
            except Exception:
                continue

        return results

    def update_performance(self, deliverable_id: str, metrics: dict) -> DeliverableMetadata:
        """
        Update performance metrics for a deliverable after publishing.

        Args:
            deliverable_id: Deliverable ID
            metrics:        Dict of metric_name → value (e.g. {"views": 15400, "engagement_rate": 0.092})

        Returns:
            Updated DeliverableMetadata
        """
        meta = self._load_meta(deliverable_id)
        meta.performance.update(metrics)
        folder = self._folder(meta.client_id, meta.workflow_name, deliverable_id)
        (folder / "metadata.json").write_text(meta.to_json(), encoding="utf-8")

        # Also write to analytics log for weekly optimization
        self._log_analytics(meta)
        return meta

    def mark_approved(self, deliverable_id: str, approved_by: str = "moncef") -> DeliverableMetadata:
        """Record who approved this deliverable and when."""
        meta = self._load_meta(deliverable_id)
        meta.approved_by = approved_by
        meta.approved_at = datetime.now().isoformat()
        folder = self._folder(meta.client_id, meta.workflow_name, deliverable_id)
        (folder / "metadata.json").write_text(meta.to_json(), encoding="utf-8")
        return meta

    def get_folder(self, deliverable_id: str) -> Path:
        """Return the filesystem path to a deliverable's folder."""
        meta = self._load_meta(deliverable_id)
        return self._folder(meta.client_id, meta.workflow_name, deliverable_id)

    # ── Content file extraction ────────────────────────────────────────────────

    def _extract_content_files(self, folder: Path, workflow_name: str, outputs: dict) -> list[str]:
        """
        Extract human-readable content files from workflow outputs.
        Workflow-specific extraction logic.
        """
        saved = []

        # Caption → caption.txt
        caption_output = outputs.get("generate_caption", {})
        if isinstance(caption_output, dict):
            caption_text = (
                caption_output.get("caption")
                or caption_output.get("output")
                or caption_output.get("text")
            )
            if not caption_text and "output" in caption_output:
                caption_text = str(caption_output["output"])
        elif isinstance(caption_output, str):
            caption_text = caption_output
        else:
            caption_text = None

        if caption_text:
            (folder / "caption.txt").write_text(str(caption_text), encoding="utf-8")
            saved.append("caption.txt")

        # Reel concept → brief.md
        concept_output = outputs.get("generate_reel_concept", {})
        if concept_output:
            brief_text = json.dumps(concept_output, indent=2, ensure_ascii=False)
            (folder / "reel_concept.json").write_text(brief_text, encoding="utf-8")
            saved.append("reel_concept.json")

        # Content plan → plan.md
        plan_output = outputs.get("create_plan", {})
        if not plan_output:
            plan_output = outputs.get("content_plan", {})
        if plan_output:
            plan_text = (
                plan_output.get("output")
                or plan_output.get("plan")
                or json.dumps(plan_output, indent=2, ensure_ascii=False)
            )
            (folder / "content_plan.md").write_text(str(plan_text), encoding="utf-8")
            saved.append("content_plan.md")

        # Report → report.md
        report_output = outputs.get("generate_report", {})
        if report_output:
            report_text = (
                report_output.get("output")
                or report_output.get("report")
                or json.dumps(report_output, indent=2, ensure_ascii=False)
            )
            (folder / "report.md").write_text(str(report_text), encoding="utf-8")
            saved.append("report.md")

        # Analysis → analysis.json
        analysis_output = outputs.get("run_analysis", {})
        if analysis_output:
            (folder / "analysis.json").write_text(
                json.dumps(analysis_output, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            saved.append("analysis.json")

        # QA review → qa_review.json
        qa_output = outputs.get("qa_review", {})
        if qa_output:
            (folder / "qa_review.json").write_text(
                json.dumps(qa_output, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            saved.append("qa_review.json")

        return saved

    # ── Internals ──────────────────────────────────────────────────────────────

    def _folder(self, client_id: str, workflow_name: str, deliverable_id: str) -> Path:
        """Return the path for a deliverable folder."""
        return DELIVERABLES_DIR / client_id / f"{workflow_name}_{deliverable_id}"

    def _load_meta(self, deliverable_id: str) -> DeliverableMetadata:
        """Find and load metadata.json for a deliverable ID."""
        for meta_path in DELIVERABLES_DIR.rglob("metadata.json"):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                if data.get("deliverable_id") == deliverable_id:
                    return DeliverableMetadata.from_dict(data)
            except Exception:
                continue
        raise FileNotFoundError(f"Deliverable not found: {deliverable_id}")

    def _log_analytics(self, meta: DeliverableMetadata) -> None:
        """Append performance data to the analytics log."""
        ANALYTICS_DIR.mkdir(exist_ok=True)
        log_file = ANALYTICS_DIR / f"{meta.client_id}_performance.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "deliverable_id": meta.deliverable_id,
                "workflow":       meta.workflow_name,
                "client_id":      meta.client_id,
                "performance":    meta.performance,
                "recorded_at":    datetime.now().isoformat(),
            }, ensure_ascii=False) + "\n")


# ── Singleton ──────────────────────────────────────────────────────────────────

_dm: DeliverableManager | None = None


def load_deliverable_manager() -> DeliverableManager:
    """Return singleton DeliverableManager."""
    global _dm
    if _dm is None:
        _dm = DeliverableManager()
    return _dm
