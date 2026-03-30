"""
Cell Agency — CrewAI Tool Wrappers
All tools available to CrewAI agents, implemented as Python functions.
These wrap the same underlying logic as the MCP servers.
"""
import os
import json
from pathlib import Path
from datetime import date, datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from crewai.tools import tool

AGENCY_DIR = Path.home() / "agency"
CLIENTS_DIR = AGENCY_DIR / "clients"
MEMORY_DIR = AGENCY_DIR / "memory"

# ─── FILE TOOLS ───────────────────────────────────────────────────────────────

@tool("Read File")
def read_file_tool(path: str) -> str:
    """Read any file from the agency workspace. Path relative to ~/agency/ or absolute."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = AGENCY_DIR / path
    if not p.exists():
        return f"File not found: {path}"
    return p.read_text(encoding="utf-8")


@tool("Write File")
def write_file_tool(path: str, content: str) -> str:
    """Write content to a file in the agency workspace."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = AGENCY_DIR / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Written: {p}"


@tool("Append to File")
def append_file_tool(path: str, content: str) -> str:
    """Append content to a file in the agency workspace."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = AGENCY_DIR / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(f"\n{content}\n")
    return f"Appended to: {p}"


@tool("List Directory")
def list_dir_tool(path: str) -> str:
    """List files in a directory within the agency workspace."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = AGENCY_DIR / path
    if not p.exists():
        return f"Directory not found: {path}"
    files = [str(f.relative_to(p)) for f in sorted(p.iterdir())]
    return "\n".join(files) if files else "(empty)"


# ─── CLIENT REGISTRY ──────────────────────────────────────────────────────────

CLIENT_ALIASES = {
    "refine-clinic": "refine",
    "refine": "refine",
    "lubina-blanca": "lubina_blanca",
    "lubina_blanca": "lubina_blanca",
}


def _resolve_client(client_id: str) -> str:
    """Resolve client ID through aliases for backward compat."""
    return CLIENT_ALIASES.get(client_id, client_id)


@tool("Read Brand Vault")
def read_brand_vault_tool(client_id: str) -> str:
    """Read a client's brand identity, colors, tone, services, and guidelines."""
    resolved = _resolve_client(client_id)
    vault = CLIENTS_DIR / resolved / "brand_vault.md"
    if not vault.exists():
        # Try original ID as fallback
        vault = CLIENTS_DIR / client_id / "brand_vault.md"
    if not vault.exists():
        return f"No brand vault found for '{client_id}'. Available: {[d.name for d in CLIENTS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]}"
    return vault.read_text(encoding="utf-8")


@tool("Read Brand Kit")
def read_brandkit_tool(client_id: str) -> str:
    """
    Read a client's structured brand kit (JSON).
    Contains colors, fonts, tone, audience, services, posting guidelines.
    Use this instead of Read Brand Vault for machine-readable brand data.
    """
    resolved = _resolve_client(client_id)
    kit = CLIENTS_DIR / resolved / "brandkit.json"
    if not kit.exists():
        return f"No brandkit.json found for '{client_id}'. Available: {[d.name for d in CLIENTS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]}"
    return kit.read_text(encoding="utf-8")


@tool("Update Brand Vault")
def update_brand_vault_tool(client_id: str, content: str) -> str:
    """Overwrite a client's brand vault with updated content."""
    vault = CLIENTS_DIR / client_id / "brand_vault.md"
    vault.parent.mkdir(parents=True, exist_ok=True)
    vault.write_text(content, encoding="utf-8")
    return f"Brand vault updated for '{client_id}'"


@tool("List Clients")
def list_clients_tool() -> str:
    """List all registered clients with their basic info."""
    if not CLIENTS_DIR.exists():
        return "No clients directory found."
    clients = []
    for d in CLIENTS_DIR.iterdir():
        if d.is_dir():
            clients.append(f"- {d.name} (brand vault: {'✅' if (d/'brand_vault.md').exists() else '❌'})")
    return "\n".join(clients) if clients else "No clients registered yet."


# ─── CONTENT CALENDAR ─────────────────────────────────────────────────────────

@tool("Read Content Calendar")
def read_calendar_tool(client_id: str) -> str:
    """Read a client's content calendar — all planned and scheduled posts."""
    cal = CLIENTS_DIR / client_id / "calendar.md"
    if not cal.exists():
        return f"No calendar found for '{client_id}'"
    return cal.read_text(encoding="utf-8")


@tool("Add to Content Calendar")
def add_to_calendar_tool(client_id: str, entry: str) -> str:
    """
    Add a new entry to a client's content calendar.
    Entry format: ## YYYY-MM-DD HH:MM\\n**Type:** Post\\n**Caption:** ...\\n**Status:** draft
    """
    cal = CLIENTS_DIR / client_id / "calendar.md"
    cal.parent.mkdir(parents=True, exist_ok=True)
    if not cal.exists():
        cal.write_text(f"# Content Calendar — {client_id}\n\n", encoding="utf-8")
    with cal.open("a", encoding="utf-8") as f:
        f.write(f"\n{entry}\n")
    return f"Added to calendar for '{client_id}'"


# ─── PROJECT WORKSPACE ────────────────────────────────────────────────────────

@tool("Create Project")
def create_project_tool(client_id: str, project_name: str, project_type: str = "campaign") -> str:
    """
    Create a new project workspace for a client.
    project_type: campaign | content_series | website | report
    """
    project_dir = CLIENTS_DIR / client_id / "projects" / project_name
    if project_dir.exists():
        return f"Project '{project_name}' already exists for '{client_id}'"
    for subdir in ["design_assets", "copy", "analytics"]:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)
    status = {
        "name": project_name,
        "client": client_id,
        "type": project_type,
        "status": "planning",
        "created": date.today().isoformat(),
        "phases": {
            "strategy": "pending",
            "creative": "pending",
            "qa": "pending",
            "approval": "pending",
            "launch": "pending",
            "analytics": "pending",
        },
        "agents_involved": [],
        "discussion_log": str(project_dir / "discussion_log.md"),
    }
    (project_dir / "project.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    (project_dir / "discussion_log.md").write_text(f"# Discussion Log — {project_name}\n\n", encoding="utf-8")
    (project_dir / "strategy.md").write_text(f"# Strategy — {project_name}\n\n*Not yet written.*\n", encoding="utf-8")
    return f"Project '{project_name}' created at {project_dir}"


@tool("Get Project Status")
def get_project_status_tool(client_id: str, project_name: str) -> str:
    """Get the current status and phase info for a project."""
    status_file = CLIENTS_DIR / client_id / "projects" / project_name / "project.json"
    if not status_file.exists():
        return f"Project '{project_name}' not found for client '{client_id}'"
    return status_file.read_text(encoding="utf-8")


@tool("Update Project Status")
def update_project_status_tool(client_id: str, project_name: str, phase: str, status: str) -> str:
    """
    Update the status of a project phase.
    phase: strategy | creative | qa | approval | launch | analytics
    status: pending | in_progress | done | approved | rejected
    """
    status_file = CLIENTS_DIR / client_id / "projects" / project_name / "project.json"
    if not status_file.exists():
        return f"Project not found: {project_name}"
    data = json.loads(status_file.read_text(encoding="utf-8"))
    data["phases"][phase] = status
    data["last_updated"] = datetime.now().isoformat()
    status_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return f"Project '{project_name}' phase '{phase}' → {status}"


# ─── DISCUSSION LOG ───────────────────────────────────────────────────────────

@tool("Write to Discussion Log")
def discussion_log_write_tool(client_id: str, project_name: str, agent_name: str, message: str) -> str:
    """
    Add an agent's contribution to a project discussion log.
    Used by all agents to collaborate and share their perspective.
    """
    log_file = CLIENTS_DIR / client_id / "projects" / project_name / "discussion_log.md"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if not log_file.exists():
        log_file.write_text(f"# Discussion Log — {project_name}\n\n", encoding="utf-8")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n**{agent_name}** [{timestamp}]:\n{message}\n"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(entry)
    return f"Logged contribution from {agent_name}"


@tool("Read Discussion Log")
def discussion_log_read_tool(client_id: str, project_name: str) -> str:
    """Read the full discussion log for a project to see all agent contributions."""
    log_file = CLIENTS_DIR / client_id / "projects" / project_name / "discussion_log.md"
    if not log_file.exists():
        return "No discussion log found for this project."
    return log_file.read_text(encoding="utf-8")


# ─── APPROVAL QUEUE ───────────────────────────────────────────────────────────

def _load_queue() -> list:
    queue_file = MEMORY_DIR / "approval_queue.json"
    if not queue_file.exists():
        return []
    return json.loads(queue_file.read_text(encoding="utf-8"))


def _save_queue(queue: list) -> None:
    MEMORY_DIR.mkdir(exist_ok=True)
    (MEMORY_DIR / "approval_queue.json").write_text(json.dumps(queue, indent=2), encoding="utf-8")


@tool("Add to Approval Queue")
def approval_queue_add_tool(item_id: str, item_type: str, description: str, client_id: str, data: str = "") -> str:
    """
    Add an item to the approval queue for Moncef to review.
    item_type: post | campaign | website | budget | client_comms | content_series
    data: JSON string with relevant details (image_path, caption, budget, etc.)
    """
    queue = _load_queue()
    queue.append({
        "id": item_id,
        "type": item_type,
        "description": description,
        "client_id": client_id,
        "data": data,
        "status": "pending",
        "created": datetime.now().isoformat(),
        "resolved_at": None,
        "resolution": None,
    })
    _save_queue(queue)
    return f"Added to approval queue: {item_id} ({item_type}) — Waiting for Moncef ✅"


@tool("List Approval Queue")
def approval_queue_list_tool(status: str = "pending") -> str:
    """
    List items in the approval queue.
    status: pending | approved | rejected | all
    """
    queue = _load_queue()
    if status != "all":
        queue = [q for q in queue if q["status"] == status]
    if not queue:
        return f"No {status} items in approval queue."
    lines = [f"**Approval Queue ({status.upper()})**\n"]
    for item in queue:
        lines.append(f"- [{item['id']}] {item['type'].upper()} | {item['client_id']} — {item['description']}")
        lines.append(f"  Created: {item['created'][:16]} | Status: {item['status']}")
    return "\n".join(lines)


@tool("Resolve Approval")
def approval_queue_resolve_tool(item_id: str, approved: bool, note: str = "") -> str:
    """
    Mark an approval queue item as approved or rejected.
    approved: True = approved, False = rejected
    note: Optional note from Moncef
    """
    queue = _load_queue()
    for item in queue:
        if item["id"] == item_id:
            item["status"] = "approved" if approved else "rejected"
            item["resolved_at"] = datetime.now().isoformat()
            item["resolution"] = note
            _save_queue(queue)
            status = "✅ APPROVED" if approved else "❌ REJECTED"
            return f"{status}: {item_id} — {item['description']}"
    return f"Item '{item_id}' not found in queue."


# ─── MEMORY / CHROMADB ────────────────────────────────────────────────────────

@tool("Store in Memory")
def memory_store_tool(collection: str, doc_id: str, content: str, metadata_json: str = "{}") -> str:
    """Store information in ChromaDB semantic memory for later retrieval."""
    import chromadb
    client = chromadb.PersistentClient(path=str(AGENCY_DIR / ".chromadb"))
    col = client.get_or_create_collection(collection)
    meta = json.loads(metadata_json) if metadata_json else {}
    col.upsert(ids=[doc_id], documents=[content], metadatas=[meta])
    return f"Stored '{doc_id}' in '{collection}'"


@tool("Search Memory")
def memory_search_tool(collection: str, query: str, n_results: int = 5) -> str:
    """Search ChromaDB semantic memory for relevant information."""
    import chromadb
    client = chromadb.PersistentClient(path=str(AGENCY_DIR / ".chromadb"))
    try:
        col = client.get_collection(collection)
        results = col.query(query_texts=[query], n_results=n_results)
        if not results["ids"][0]:
            return f"No results found in '{collection}' for: {query}"
        lines = []
        for i, doc_id in enumerate(results["ids"][0]):
            lines.append(f"**{doc_id}** (relevance: {1 - results['distances'][0][i]:.2f})\n{results['documents'][0][i][:300]}")
        return "\n\n".join(lines)
    except Exception:
        return f"Collection '{collection}' not found or empty."


@tool("Store Agency Learning")
def store_learning_tool(insight: str, source: str, metric: str = "", value: str = "", client_id: str = "") -> str:
    """
    Store a marketing insight or learning in the agency knowledge base.
    Used after campaign analytics to improve future campaigns.
    insight: The learning (e.g., 'Educational reels get 3x engagement vs static posts')
    source: Where this came from (e.g., 'refine-clinic instagram analytics Q1 2026')
    """
    import chromadb
    client = chromadb.PersistentClient(path=str(AGENCY_DIR / ".chromadb"))
    col = client.get_or_create_collection("agency_knowledge")
    doc_id = f"learning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    col.upsert(
        ids=[doc_id],
        documents=[insight],
        metadatas=[{"source": source, "metric": metric, "value": value, "client_id": client_id, "date": date.today().isoformat()}]
    )
    return f"Learning stored: {insight[:80]}..."


# ─── WEB SEARCH ───────────────────────────────────────────────────────────────

@tool("Search Web")
def search_web_tool(query: str, n_results: int = 5) -> str:
    """Search the web using Serper. Returns titles, links, and snippets."""
    import httpx
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        return "SERPER_API_KEY not set."
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    with httpx.Client(timeout=15) as http:
        resp = http.post("https://google.serper.dev/search", headers=headers, json={"q": query, "num": n_results})
        resp.raise_for_status()
        data = resp.json()
    results = []
    for item in data.get("organic", [])[:n_results]:
        results.append(f"**{item.get('title')}**\n{item.get('snippet', '')}\n{item.get('link', '')}")
    return "\n\n".join(results) if results else "No results found."


@tool("Search Web News")
def search_web_news_tool(query: str, n_results: int = 5) -> str:
    """Search for recent news articles on a topic."""
    import httpx
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        return "SERPER_API_KEY not set."
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    with httpx.Client(timeout=15) as http:
        resp = http.post("https://google.serper.dev/news", headers=headers, json={"q": query, "num": n_results})
        resp.raise_for_status()
        data = resp.json()
    results = []
    for item in data.get("news", [])[:n_results]:
        results.append(f"**{item.get('title')}** ({item.get('date', '')})\n{item.get('snippet', '')}\n{item.get('link', '')}")
    return "\n\n".join(results) if results else "No news found."


@tool("Fetch Webpage")
def fetch_webpage_tool(url: str) -> str:
    """Fetch and return the text content of a webpage."""
    import httpx
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as http:
            resp = http.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; CellAgencyBot/1.0)"})
            resp.raise_for_status()
            return resp.text[:5000]
    except Exception as e:
        return f"Error fetching {url}: {e}"


# ─── DAILY LOG ────────────────────────────────────────────────────────────────

@tool("Log Daily Activity")
def log_daily_tool(entry: str) -> str:
    """Append an entry to today's activity log. Use to record what you've done."""
    MEMORY_DIR.mkdir(exist_ok=True)
    log_file = MEMORY_DIR / f"{date.today().isoformat()}.md"
    timestamp = datetime.now().strftime("%H:%M")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"\n### {timestamp}\n{entry}\n")
    return f"Logged to {log_file.name}"


# ─── SKILL EVOLUTION SYSTEM ──────────────────────────────────────────────────

@tool("Log Skill Run")
def skill_log_run_tool(
    skill: str,
    agent: str,
    status: str = "success",
    client_id: str = "",
    triggered_by: str = "",
    qa_score: float = 0.0,
    duration_s: float = 0.0,
    notes: str = "",
) -> str:
    """
    Log a completed skill execution for performance tracking.
    Call this after finishing any skill task to build the evolution database.

    Args:
        skill:        Skill slug (e.g. 'content-forge', 'social-pilot', 'seo-radar')
        agent:        Your agent id (e.g. 'content_creator')
        status:       'success' | 'failed' | 'partial'
        client_id:    Client this ran for (e.g. 'refine-clinic')
        triggered_by: Original trigger phrase or task description
        qa_score:     QA score 1-10 (0.0 = not yet scored)
        duration_s:   How many seconds the task took (0.0 = not tracked)
        notes:        Any extra notes about this run
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from skills.skill_tracker import load_tracker
    tracker = load_tracker()
    run_id = tracker.log_run(
        skill=skill,
        agent=agent,
        client_id=client_id,
        triggered_by=triggered_by,
        status=status,
        qa_score=qa_score if qa_score > 0 else None,
        duration_s=duration_s if duration_s > 0 else None,
        notes=notes,
    )
    return f"✅ Run logged: {run_id}\n  skill={skill} | agent={agent} | status={status}"


@tool("Log Skill Feedback")
def skill_log_feedback_tool(run_id: str, feedback: str, approved: bool = True) -> str:
    """
    Record Moncef's feedback on a skill output.
    Call after receiving approval or rejection from Moncef.

    Args:
        run_id:   Run ID from skill_log_run_tool
        feedback: Text feedback ('approved', 'needs revision — tone too formal', etc.)
        approved: True if Moncef approved, False if rejected
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from skills.skill_tracker import load_tracker
    tracker = load_tracker()
    found = tracker.log_feedback(run_id, feedback, approved)
    if found:
        status = "✅ approved" if approved else "❌ rejected"
        return f"Feedback recorded for {run_id}: {status} — {feedback}"
    return f"Run ID '{run_id}' not found."


@tool("Get Skill Performance")
def skill_get_performance_tool(skill: str) -> str:
    """
    Get aggregated performance stats for a skill.
    Use to check if a skill is performing well before routing important tasks to it.

    Args:
        skill: Skill slug (e.g. 'content-forge', 'ads-cockpit')
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from skills.skill_tracker import load_tracker
    tracker = load_tracker()
    stats = tracker.get_performance(skill)
    if stats["total_runs"] == 0:
        return f"No data yet for '{skill}'. Run it at least {3} times to generate stats."
    lines = [
        f"**{skill}** — {stats['health'].upper()}",
        f"  Runs: {stats['total_runs']} | Last: {stats['last_run'] or '—'}",
        f"  Success rate: {stats['success_rate']:.0%}" if stats["success_rate"] is not None else "  Success rate: —",
        f"  Avg QA score: {stats['avg_qa_score']:.1f}/10" if stats["avg_qa_score"] is not None else "  Avg QA score: —",
        f"  Moncef approval: {stats['moncef_approval_rate']:.0%}" if stats["moncef_approval_rate"] is not None else "  Moncef approval: —",
        f"  Top triggers: {', '.join(stats['top_triggers'])}" if stats["top_triggers"] else "",
    ]
    if stats["issues"]:
        lines.append("  ⚠️ Issues: " + " | ".join(stats["issues"]))
    return "\n".join(l for l in lines if l)


# ─── AGENT COMMUNICATION PROTOCOL ────────────────────────────────────────────

@tool("Send Task to Agent")
def task_send_tool(
    from_agent: str,
    to_agent: str,
    title: str,
    description: str = "",
    inputs_json: str = "{}",
    skill: str = "",
    priority: int = 3,
) -> str:
    """
    Send a task to another agent's inbox for async handoff.

    Args:
        from_agent:  Your agent id (e.g. 'content_creator')
        to_agent:    Recipient agent id (e.g. 'qa_gate', 'social_media_manager', 'nadia')
        title:       Short task title (e.g. 'QA Review: Ramadan Post')
        description: Full description of what needs to be done
        inputs_json: JSON string with task payload (e.g. '{"content": "...", "client_id": "..."}')
        skill:       Which agency skill this relates to (e.g. 'content-forge')
        priority:    1 (low) to 5 (urgent), default 3
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from comms import load_task_bus
    try:
        inputs = json.loads(inputs_json) if inputs_json.strip() else {}
    except json.JSONDecodeError:
        inputs = {"raw": inputs_json}
    bus = load_task_bus()
    task_id = bus.send(
        from_agent=from_agent,
        to_agent=to_agent,
        title=title,
        description=description,
        inputs=inputs,
        skill=skill,
        priority=priority,
    )
    return f"✅ Task sent: {task_id}\n  {from_agent} → {to_agent}: {title}"


@tool("List My Tasks")
def task_list_tool(agent_id: str, status: str = "pending") -> str:
    """
    List tasks in an agent's inbox.

    Args:
        agent_id: Whose inbox to check — use your own agent id
        status:   'pending' | 'active' | 'done' | 'failed' | 'all'
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from comms import load_task_bus
    bus = load_task_bus()
    tasks = bus.list_inbox(agent_id, status)
    if not tasks:
        return f"No {status} tasks for {agent_id}."
    lines = [f"**Tasks for {agent_id} ({status.upper()})**\n"]
    for task in tasks:
        lines.append(task.summary())
    return "\n\n".join(lines)


@tool("Claim Task")
def task_claim_tool(agent_id: str, task_id: str) -> str:
    """
    Claim a pending task to mark it as in-progress before starting work.

    Args:
        agent_id: Your agent id (must match task's to_agent field)
        task_id:  The task_id from your inbox (e.g. 'task_20260329_103045_a3f8b2')
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from comms import load_task_bus
    bus = load_task_bus()
    try:
        task = bus.claim(agent_id, task_id)
        inputs_str = json.dumps(task.inputs, ensure_ascii=False, indent=2)
        return (
            f"✅ Claimed: {task_id}\n{task.summary()}\n\n"
            f"**Description:** {task.description}\n\n"
            f"**Inputs:**\n{inputs_str}"
        )
    except (FileNotFoundError, PermissionError, ValueError) as e:
        return f"❌ Cannot claim task: {e}"


@tool("Complete Task")
def task_complete_tool(task_id: str, outputs_json: str = "{}", note: str = "") -> str:
    """
    Mark a task as complete with output data.

    Args:
        task_id:      Task to complete
        outputs_json: JSON string with results (e.g. '{"approved": true, "content": "..."}')
        note:         Optional completion note added to task thread
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from comms import load_task_bus
    bus = load_task_bus()
    try:
        outputs = json.loads(outputs_json) if outputs_json.strip() else {}
    except json.JSONDecodeError:
        outputs = {"raw": outputs_json}
    try:
        task = bus.complete(task_id, outputs, note)
        return f"✅ Task completed: {task_id} — {task.title}"
    except FileNotFoundError as e:
        return f"❌ Task not found: {e}"


@tool("Fail Task")
def task_fail_tool(task_id: str, reason: str) -> str:
    """
    Mark a task as failed with a clear reason.

    Args:
        task_id: Task to fail
        reason:  Explanation of what went wrong and what's needed to retry
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from comms import load_task_bus
    bus = load_task_bus()
    try:
        task = bus.fail(task_id, reason)
        return f"❌ Task failed: {task_id} — {task.title}\nReason: {reason}"
    except FileNotFoundError as e:
        return f"❌ Task not found: {e}"


@tool("Reply to Task")
def task_reply_tool(task_id: str, from_agent: str, message: str) -> str:
    """
    Add a message to a task's thread for questions, feedback, or status updates.

    Args:
        task_id:    Task to reply to
        from_agent: Your agent id
        message:    Your message (question, feedback, clarification, etc.)
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from comms import load_task_bus
    bus = load_task_bus()
    try:
        task = bus.reply(task_id, from_agent, message)
        return f"💬 Reply added to {task_id}. Thread now has {len(task.thread)} message(s)."
    except FileNotFoundError as e:
        return f"❌ Task not found: {e}"


# ─── APPROVAL ENGINE TOOLS ────────────────────────────────────────────────────

@tool("Submit for Approval")
def submit_approval_tool(
    action: str,
    client_id: str,
    draft_output_json: str,
    confidence: float = 0.0,
    workflow_id: str = "",
    notes: str = "",
) -> str:
    """
    Submit an action for Moncef's approval before executing it.
    Use for publishing, ads, website deploys, or any autonomous action.
    confidence: 0.0–1.0 — below 0.75 always requires approval.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    import json
    from core.approval_engine import load_approval_engine
    draft = json.loads(draft_output_json) if draft_output_json.strip() else {}
    engine  = load_approval_engine()
    task_id = engine.submit(
        action=action,
        client_id=_resolve_client(client_id),
        draft_output=draft,
        confidence=confidence,
        workflow_id=workflow_id or None,
        notes=notes,
    )
    return f"Submitted for approval: {task_id} — action: {action}"


@tool("List Pending Approvals")
def list_approvals_tool(client_id: str = "") -> str:
    """List all items in the approval queue waiting for Moncef's review."""
    import sys
    sys.path.insert(0, str(AGENCY_DIR))
    from core.approval_engine import load_approval_engine
    engine = load_approval_engine()
    return engine.queue_summary()


@tool("Create Workflow")
def create_workflow_tool(workflow_name: str, client_id: str, inputs_json: str = "{}") -> str:
    """
    Create and start a named workflow via the Workflow Engine.
    workflow_name: create_instagram_post | create_reel | content_planning | website_creation | generate_report
    """
    import sys, json
    sys.path.insert(0, str(AGENCY_DIR))
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from core.workflow_engine import load_workflow_engine
    inputs = json.loads(inputs_json) if inputs_json.strip() else {}
    inputs.setdefault("client_id", _resolve_client(client_id))
    engine = load_workflow_engine()
    wf     = engine.create(workflow_name, _resolve_client(client_id), inputs)
    wf     = engine.start(wf.id)
    return f"Workflow {wf.id} started | state: {wf.state.value} | {len(wf.steps)} steps"


@tool("Get Workflow Status")
def workflow_status_tool(workflow_id: str) -> str:
    """Get current status of a running workflow."""
    import sys, json
    sys.path.insert(0, str(AGENCY_DIR))
    from core.workflow_engine import load_workflow_engine
    engine = load_workflow_engine()
    return json.dumps(engine.get_status(workflow_id), ensure_ascii=False, indent=2)


# ─── CONTENT SERVER TOOLS ────────────────────────────────────────────────────

@tool("Generate Content Strategy")
def generate_content_strategy_tool(client_id: str, goal: str, weeks: int = 4, platforms: str = "instagram") -> str:
    """
    Generate a multi-week content strategy for a client.
    Reads brandkit for context, returns strategy JSON with themes, content mix, and key messages.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from content_server import generate_content_strategy
    return generate_content_strategy(client_id, goal, weeks, platforms)


@tool("Generate Caption")
def generate_caption_tool(client_id: str, topic: str, platform: str = "instagram", language: str = "french", tone: str = "") -> str:
    """
    Generate a platform-optimized caption for a social post.
    Reads brandkit for tone of voice, audience, and sensitivity rules.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from content_server import generate_caption
    return generate_caption(client_id, topic, platform, language, tone)


@tool("Create Content Plan")
def create_content_plan_tool(client_id: str, weeks: int = 2, themes: str = "") -> str:
    """
    Create a detailed week-by-week content calendar with post ideas, formats, and timing.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from content_server import create_content_plan
    return create_content_plan(client_id, weeks, themes)


@tool("Generate Ad Copy")
def generate_ad_copy_tool(client_id: str, campaign_goal: str, offer: str, language: str = "french") -> str:
    """Generate ad copy variations for a campaign — headlines, primary text, CTAs."""
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from content_server import generate_ad_copy
    return generate_ad_copy(client_id, campaign_goal, offer, language)


# ─── VIDEO SERVER TOOLS ───────────────────────────────────────────────────────

@tool("Generate Reel Concept")
def generate_reel_concept_tool(client_id: str, topic: str, duration_s: int = 15, style: str = "educational") -> str:
    """
    Generate a structured reel concept JSON with hook, scenes, transitions, CTA, and music mood.
    Use before producing any video content.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from video_server import generate_reel_concept
    return generate_reel_concept(client_id, topic, duration_s, style)


# ─── ASSET SERVER TOOLS ───────────────────────────────────────────────────────

@tool("Search Assets")
def search_assets_tool(client_id: str, query: str, asset_type: str = "all", limit: int = 10) -> str:
    """
    Search client assets by semantic query. Searches ChromaDB tags + filename matching.
    asset_type: 'image' | 'video' | 'logo' | 'all'
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from asset_server import search_assets
    return search_assets(client_id, query, asset_type, limit)


@tool("Choose Best Assets")
def choose_best_assets_tool(client_id: str, brief: str, count: int = 3) -> str:
    """
    Score and rank available assets for a given creative brief.
    Returns top N assets with relevance scores.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from asset_server import choose_best_assets
    return choose_best_assets(client_id, brief, count)


@tool("List Assets")
def list_assets_tool(client_id: str, asset_type: str = "all") -> str:
    """List all assets for a client with file sizes and metadata."""
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from asset_server import list_assets
    return list_assets(client_id, asset_type)


# ─── DOCUMENT SERVER TOOLS ───────────────────────────────────────────────────

@tool("Generate Document")
def generate_document_tool(client_id: str, doc_type: str, title: str, sections: str = "", language: str = "french") -> str:
    """
    Generate a professional document (proposal, brief, report, plan, strategy, onboarding).
    Saves to memory/outputs/{client_id}/ and returns the file path + content.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from document_server import generate_document
    return generate_document(client_id, doc_type, title, sections, language)


@tool("Generate Report")
def generate_report_tool(client_id: str, report_type: str, period: str, data_json: str = "{}") -> str:
    """
    Generate a performance report (weekly, monthly, campaign, social, ads).
    report_type: 'weekly' | 'monthly' | 'campaign' | 'social' | 'ads' | 'annual'
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from document_server import generate_report
    return generate_report(client_id, report_type, period, data_json)


# ─── LEARNING SERVER TOOLS ────────────────────────────────────────────────────

@tool("Find Inspiration")
def find_inspiration_tool(query: str, platform: str = "instagram", industry: str = "beauty", limit: int = 5) -> str:
    """
    Search for marketing inspiration. Checks ChromaDB cache first, then web search.
    Stores results for future reference. Call before creating any new content.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from learning_server import find_inspiration
    return find_inspiration(query, platform, industry, limit)


@tool("Store Learning")
def store_learning_server_tool(insight: str, client_id: str = "", source: str = "", category: str = "general", metric: str = "", value: str = "") -> str:
    """
    Store a marketing learning in the agency knowledge base (ChromaDB + filesystem).
    category: content_performance | audience_insight | campaign_result | best_practice | brand_guideline
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from learning_server import store_learning
    return store_learning(insight, client_id, source, category, metric, value)


@tool("Query Learnings")
def query_learnings_tool(query: str, client_id: str = "", category: str = "", limit: int = 5) -> str:
    """
    Semantic search over stored marketing learnings. Call BEFORE creating content.
    Searches client-specific and agency-wide collections.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from learning_server import query_learnings
    return query_learnings(query, client_id, category, limit)


@tool("Daily Analysis")
def daily_analysis_tool(client_id: str) -> str:
    """
    Run daily performance analysis for a client. Generates insights and auto-stores
    top learnings to ChromaDB for future content decisions.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from learning_server import daily_analysis
    return daily_analysis(client_id)


@tool("Detect Content Gaps")
def detect_content_gaps_tool(client_id: str) -> str:
    """
    Analyze content calendar to find underrepresented themes and missing service coverage.
    Returns recommended next 5 posts.
    """
    import sys
    sys.path.insert(0, str(AGENCY_DIR / "mcp-servers"))
    from learning_server import detect_content_gaps
    return detect_content_gaps(client_id)


# ─── TOOL REGISTRY ────────────────────────────────────────────────────────────
# Maps YAML tool names to actual tool objects

TOOL_REGISTRY = {
    # File tools
    "agency.read_file": read_file_tool,
    "agency.write_file": write_file_tool,
    "agency.append_file": append_file_tool,
    "agency.list_dir": list_dir_tool,
    # Client tools
    "agency.read_brand_vault": read_brand_vault_tool,
    "agency.read_brandkit": read_brandkit_tool,
    "agency.update_brand_vault": update_brand_vault_tool,
    "agency.list_clients": list_clients_tool,
    # Calendar tools
    "agency.read_calendar": read_calendar_tool,
    "agency.add_to_calendar": add_to_calendar_tool,
    # Project tools
    "agency.create_project": create_project_tool,
    "agency.get_project_status": get_project_status_tool,
    "agency.update_project_status": update_project_status_tool,
    # Discussion tools
    "agency.discussion_log_write": discussion_log_write_tool,
    "agency.discussion_log_read": discussion_log_read_tool,
    # Approval queue
    "agency.approval_queue_add": approval_queue_add_tool,
    "agency.approval_queue_list": approval_queue_list_tool,
    "agency.approval_queue_resolve": approval_queue_resolve_tool,
    # Memory tools
    "agency.memory_store": memory_store_tool,
    "agency.memory_search": memory_search_tool,
    "agency.store_learning": store_learning_tool,
    # Web tools
    "agency.search_web": search_web_tool,
    "agency.search_web_news": search_web_news_tool,
    "agency.fetch_webpage": fetch_webpage_tool,
    # Log
    "agency.log_daily": log_daily_tool,
    # Skill evolution tracking
    "skill.log_run":        skill_log_run_tool,
    "skill.log_feedback":   skill_log_feedback_tool,
    "skill.get_performance": skill_get_performance_tool,
    # Agent communication / task bus
    "crew.task_send":     task_send_tool,
    "crew.task_list":     task_list_tool,
    "crew.task_claim":    task_claim_tool,
    "crew.task_complete": task_complete_tool,
    "crew.task_fail":     task_fail_tool,
    "crew.task_reply":    task_reply_tool,
    # Content server
    "content.generate_content_strategy": generate_content_strategy_tool,
    "content.generate_caption":          generate_caption_tool,
    "content.create_content_plan":       create_content_plan_tool,
    "content.generate_ad_copy":          generate_ad_copy_tool,
    # Video server
    "video.generate_reel_concept":       generate_reel_concept_tool,
    # Asset server
    "asset.search_assets":               search_assets_tool,
    "asset.choose_best_assets":          choose_best_assets_tool,
    "asset.list_assets":                 list_assets_tool,
    # Document server
    "document.generate_document":        generate_document_tool,
    "document.generate_report":          generate_report_tool,
    # Learning server
    "learning.find_inspiration":         find_inspiration_tool,
    "learning.store_learning":           store_learning_server_tool,
    "learning.query_learnings":          query_learnings_tool,
    "learning.daily_analysis":           daily_analysis_tool,
    "learning.detect_content_gaps":      detect_content_gaps_tool,
    # Approval engine
    "approval.submit":                   submit_approval_tool,
    "approval.list_pending":             list_approvals_tool,
    # Workflow engine
    "workflow.create":                   create_workflow_tool,
    "workflow.status":                   workflow_status_tool,
}


def get_tools_for_agent(tool_names: list[str]) -> list:
    """Return CrewAI tool objects for a list of YAML tool name strings."""
    tools = []
    for name in tool_names:
        if name in TOOL_REGISTRY:
            tools.append(TOOL_REGISTRY[name])
        # Tools from social/ads/design servers are handled as stubs for now
        # (they require API keys and are called directly via MCP by OpenClaw)
    return tools
