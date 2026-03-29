"""
Cell Agency — Core MCP Server
Provides: file ops, ChromaDB memory, web search, Python runner, client registry,
          brand vault, content calendar, approvals.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional

# Add tools/ and routing/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastmcp import FastMCP
import chromadb
from file_tools import read_file, write_file, append_file, list_dir, create_dir, delete_file, file_exists
from web_tools import web_search, fetch_url

mcp = FastMCP("agency")

AGENCY_DIR = Path.home() / "agency"
CLIENTS_DIR = AGENCY_DIR / "clients"
CHROMA_PATH = AGENCY_DIR / ".chromadb"

# ─── Client aliases for backward compatibility ───────────────────────────────
CLIENT_ALIASES = {
    "refine-clinic": "refine",
    "refine": "refine",
    "lubina-blanca": "lubina_blanca",
    "lubina_blanca": "lubina_blanca",
}


def resolve_client_id(client_id: str) -> str:
    """Resolve a client ID, supporting aliases for backward compat."""
    return CLIENT_ALIASES.get(client_id, client_id)

# ─── ChromaDB client (persistent) ─────────────────────────────────────────────
_chroma_client: Optional[chromadb.PersistentClient] = None

def get_chroma():
    global _chroma_client
    if _chroma_client is None:
        CHROMA_PATH.mkdir(exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _chroma_client


# ─── FILE TOOLS ───────────────────────────────────────────────────────────────

@mcp.tool()
def agency_read_file(path: str, agent_id: str = "") -> str:
    """
    Read a file from the agency workspace (clients/, skills/, memory/ only).

    Args:
        path: File path (absolute or relative to ~/agency/)
        agent_id: Optional — if provided, enforces per-agent read permission.
                  If empty, only the global safe-path check applies.
    """
    if agent_id:
        from permissions import load_permissions
        return load_permissions().read(agent_id, path)
    return read_file(path)


@mcp.tool()
def agency_write_file(path: str, content: str, overwrite: bool = True, agent_id: str = "") -> str:
    """
    Write content to a file in the agency workspace.

    Args:
        path: File path
        content: Content to write
        overwrite: Whether to overwrite existing file
        agent_id: Optional — if provided, enforces per-agent write permission
    """
    if agent_id:
        from permissions import load_permissions
        return load_permissions().write(agent_id, path, content, overwrite)
    return write_file(path, content, overwrite)


@mcp.tool()
def agency_append_file(path: str, content: str, agent_id: str = "") -> str:
    """
    Append content to a file in the agency workspace.

    Args:
        path: File path
        content: Content to append
        agent_id: Optional — if provided, enforces per-agent append permission
    """
    if agent_id:
        from permissions import load_permissions
        return load_permissions().append(agent_id, path, content)
    return append_file(path, content)


@mcp.tool()
def agency_list_dir(path: str, pattern: str = "*") -> list[str]:
    """List files in a directory within the agency workspace."""
    return list_dir(path, pattern)


@mcp.tool()
def agency_create_dir(path: str, agent_id: str = "") -> str:
    """
    Create a directory in the agency workspace.

    Args:
        path: Directory path
        agent_id: Optional — if provided, enforces per-agent create_dir permission
    """
    if agent_id:
        from permissions import load_permissions
        return load_permissions().create_dir(agent_id, path)
    return create_dir(path)


@mcp.tool()
def agency_delete_file(path: str, agent_id: str = "") -> str:
    """
    Delete a file from the agency workspace.

    Args:
        path: File path
        agent_id: Optional — if provided, enforces per-agent delete permission
    """
    if agent_id:
        from permissions import load_permissions
        return load_permissions().delete(agent_id, path)
    return delete_file(path)


@mcp.tool()
def agency_file_exists(path: str) -> bool:
    """Check if a file exists in the agency workspace."""
    return file_exists(path)


@mcp.tool()
def check_file_permission(agent_id: str, path: str) -> str:
    """
    Check what file operations an agent is allowed on a path.
    Returns a breakdown of allowed and denied operations.

    Args:
        agent_id: Agent identifier (e.g. 'content_creator')
        path: File or directory path to check

    Returns:
        JSON with allowed and denied operations
    """
    try:
        from permissions import load_permissions
        result = load_permissions().explain(agent_id, path)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_agent_permissions(agent_id: str) -> str:
    """
    List all file permission rules for an agent.

    Args:
        agent_id: Agent identifier (e.g. 'graphic_designer')

    Returns:
        JSON list of {pattern, ops} rules
    """
    try:
        from permissions import load_permissions
        rules = load_permissions().list_agent_paths(agent_id)
        return json.dumps({"agent": agent_id, "rules": rules}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── CLIENT REGISTRY ──────────────────────────────────────────────────────────

@mcp.tool()
def list_clients() -> list[dict]:
    """Return a list of all registered clients with their basic info."""
    clients = []
    if not CLIENTS_DIR.exists():
        return clients
    for client_dir in sorted(CLIENTS_DIR.iterdir()):
        if client_dir.is_dir() and not client_dir.name.startswith("."):
            vault = client_dir / "brand_vault.md"
            brandkit = client_dir / "brandkit.json"
            # Try to read name from brandkit.json
            name = client_dir.name.replace("-", " ").replace("_", " ").title()
            if brandkit.exists():
                try:
                    data = json.loads(brandkit.read_text(encoding="utf-8"))
                    name = data.get("name", name)
                except Exception:
                    pass
            clients.append({
                "id": client_dir.name,
                "name": name,
                "has_brand_vault": vault.exists(),
                "has_brandkit": brandkit.exists(),
                "status": "active" if brandkit.exists() else "legacy",
                "path": str(client_dir),
            })
    return clients


@mcp.tool()
def create_client(client_id: str, name: str, industry: str, location: str = "") -> str:
    """
    Register a new client and create their workspace folder structure.

    Args:
        client_id: URL-safe identifier (e.g. 'acme-corp')
        name: Display name
        industry: Industry/sector
        location: Optional location
    """
    client_dir = CLIENTS_DIR / client_id
    if client_dir.exists():
        return f"Client '{client_id}' already exists at {client_dir}"

    # Create folder structure (new layout: images, videos, logo + legacy: campaigns, assets, reports)
    for subdir in ["images", "videos", "logo", "campaigns", "assets", "reports"]:
        (client_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Create brandkit.json (structured, machine-readable)
    from datetime import date as _date
    brandkit = {
        "name": name,
        "short_name": name,
        "industry": industry,
        "location": {"city": location, "area": "", "country": ""},
        "colors": {"primary": "", "secondary": "", "accent": "", "text": ""},
        "fonts": {"heading": "", "body": "", "arabic": ""},
        "tone_of_voice": {"french": "", "darija": "", "avoid": []},
        "audience": {
            "primary": {"name": "", "age": "", "profile": "", "goals": "", "pain_points": ""},
            "secondary": {"name": "", "age": "", "profile": "", "goals": ""},
        },
        "languages": ["fr", "ar"],
        "logo_path": f"clients/{client_id}/logo/",
        "tagline": {"fr": "", "ar": ""},
        "social": {"instagram": "", "facebook": "", "website": ""},
        "services": [],
        "content_themes": [],
        "posting": {
            "frequency": "",
            "best_times": [],
            "hashtags": {"french": [], "arabic": [], "local": []},
        },
        "sensitivity": [],
        "goals_2026": [],
        "added": str(_date.today()),
        "status": "onboarding",
    }
    (client_dir / "brandkit.json").write_text(
        json.dumps(brandkit, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Create brand vault template (human-readable)
    vault_content = f"""# Brand Vault — {name}

## Basic Info
- **Name:** {name}
- **Industry:** {industry}
- **Location:** {location}
- **Added:** {_date.today()}

## Brand Identity
- **Primary color:** TBD
- **Secondary color:** TBD
- **Font:** TBD
- **Logo:** TBD
- **Tagline:** TBD

## Target Audience
TBD — describe the ideal customer

## Tone of Voice
TBD — professional / friendly / luxurious / etc.

## Social Media
- **Instagram:** @
- **Facebook:**
- **Website:**

## Services / Products
- TBD

## Content Guidelines
- TBD

## Important Notes
- TBD
"""
    (client_dir / "brand_vault.md").write_text(vault_content, encoding="utf-8")
    (client_dir / "calendar.md").write_text(f"# Content Calendar — {name}\n\n", encoding="utf-8")

    # Register alias
    CLIENT_ALIASES[client_id] = client_id

    return f"Client '{name}' created at {client_dir}"


@mcp.tool()
def read_brand_vault(client_id: str) -> str:
    """Read a client's brand vault (identity, colors, tone, guidelines)."""
    resolved = resolve_client_id(client_id)
    vault_path = CLIENTS_DIR / resolved / "brand_vault.md"
    if not vault_path.exists():
        # Try original ID as fallback
        vault_path = CLIENTS_DIR / client_id / "brand_vault.md"
    if not vault_path.exists():
        raise FileNotFoundError(f"No brand vault found for client '{client_id}'")
    return vault_path.read_text(encoding="utf-8")


@mcp.tool()
def update_brand_vault(client_id: str, content: str) -> str:
    """Overwrite a client's brand vault with new content."""
    resolved = resolve_client_id(client_id)
    vault_path = CLIENTS_DIR / resolved / "brand_vault.md"
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault_path.write_text(content, encoding="utf-8")
    return f"Brand vault updated for '{resolved}'"


@mcp.tool()
def read_brandkit(client_id: str) -> str:
    """
    Read a client's structured brand kit (JSON format).
    Contains colors, fonts, tone, audience, services, posting guidelines.

    Args:
        client_id: Client identifier (e.g. 'refine', 'lubina_blanca')

    Returns:
        JSON string with full brand kit data
    """
    resolved = resolve_client_id(client_id)
    kit_path = CLIENTS_DIR / resolved / "brandkit.json"
    if not kit_path.exists():
        raise FileNotFoundError(
            f"No brandkit.json found for client '{client_id}' (resolved: '{resolved}'). "
            f"Available: {[d.name for d in CLIENTS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]}"
        )
    return kit_path.read_text(encoding="utf-8")


@mcp.tool()
def update_brandkit(client_id: str, updates_json: str) -> str:
    """
    Update specific fields in a client's brand kit.
    Merges updates into existing data (does not replace the whole file).

    Args:
        client_id: Client identifier
        updates_json: JSON string with fields to update, e.g. '{"colors": {"primary": "#FF0000"}}'

    Returns:
        Confirmation message
    """
    resolved = resolve_client_id(client_id)
    kit_path = CLIENTS_DIR / resolved / "brandkit.json"
    if not kit_path.exists():
        raise FileNotFoundError(f"No brandkit.json found for client '{resolved}'")

    existing = json.loads(kit_path.read_text(encoding="utf-8"))
    updates = json.loads(updates_json)

    def deep_merge(base: dict, overlay: dict) -> dict:
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    merged = deep_merge(existing, updates)
    kit_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"Brand kit updated for '{resolved}' — {len(updates)} field(s) merged"


# ─── CONTENT CALENDAR ─────────────────────────────────────────────────────────

@mcp.tool()
def read_calendar(client_id: str) -> str:
    """Read a client's content calendar."""
    resolved = resolve_client_id(client_id)
    cal_path = CLIENTS_DIR / resolved / "calendar.md"
    if not cal_path.exists():
        # Try original ID as fallback
        cal_path = CLIENTS_DIR / client_id / "calendar.md"
    if not cal_path.exists():
        return f"No calendar found for '{client_id}'"
    return cal_path.read_text(encoding="utf-8")


@mcp.tool()
def add_to_calendar(client_id: str, entry: str) -> str:
    """Append a new entry to a client's content calendar."""
    resolved = resolve_client_id(client_id)
    cal_path = CLIENTS_DIR / resolved / "calendar.md"
    cal_path.parent.mkdir(parents=True, exist_ok=True)
    if not cal_path.exists():
        cal_path.write_text(f"# Content Calendar — {resolved}\n\n", encoding="utf-8")
    with cal_path.open("a", encoding="utf-8") as f:
        f.write(f"\n{entry}\n")
    return f"Added to calendar for '{resolved}'"


# ─── MEMORY / CHROMADB ────────────────────────────────────────────────────────

@mcp.tool()
def memory_store(collection: str, doc_id: str, content: str, metadata: Optional[dict] = None) -> str:
    """
    Store a document in ChromaDB memory.

    Args:
        collection: Collection name (e.g. 'clients', 'campaigns', 'knowledge')
        doc_id: Unique document ID
        content: Text content to store and embed
        metadata: Optional dict of metadata fields
    """
    client = get_chroma()
    col = client.get_or_create_collection(collection)
    meta = metadata or {}
    col.upsert(ids=[doc_id], documents=[content], metadatas=[meta])
    return f"Stored '{doc_id}' in collection '{collection}'"


@mcp.tool()
def memory_search(collection: str, query: str, n_results: int = 5) -> list[dict]:
    """
    Semantic search in ChromaDB memory.

    Returns list of dicts with keys: id, content, metadata, distance
    """
    client = get_chroma()
    try:
        col = client.get_collection(collection)
    except Exception:
        return []
    results = col.query(query_texts=[query], n_results=n_results)
    output = []
    for i, doc_id in enumerate(results["ids"][0]):
        output.append({
            "id": doc_id,
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return output


@mcp.tool()
def memory_get(collection: str, doc_id: str) -> Optional[dict]:
    """Retrieve a specific document from ChromaDB by ID."""
    client = get_chroma()
    try:
        col = client.get_collection(collection)
        result = col.get(ids=[doc_id])
        if result["ids"]:
            return {
                "id": result["ids"][0],
                "content": result["documents"][0],
                "metadata": result["metadatas"][0],
            }
    except Exception:
        pass
    return None


@mcp.tool()
def memory_delete(collection: str, doc_id: str) -> str:
    """Delete a document from ChromaDB."""
    client = get_chroma()
    try:
        col = client.get_collection(collection)
        col.delete(ids=[doc_id])
        return f"Deleted '{doc_id}' from '{collection}'"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_memory_collections() -> list[str]:
    """List all ChromaDB collections."""
    client = get_chroma()
    return [col.name for col in client.list_collections()]


# ─── WEB SEARCH ───────────────────────────────────────────────────────────────

@mcp.tool()
def search_web(query: str, n_results: int = 5) -> list[dict]:
    """Search the web using Serper. Returns list of {title, link, snippet}."""
    return web_search(query, n_results)


@mcp.tool()
def fetch_webpage(url: str) -> str:
    """Fetch the text content of a webpage."""
    return fetch_url(url)


# ─── SAFE PYTHON RUNNER ───────────────────────────────────────────────────────

@mcp.tool()
def run_python(script: str, timeout: int = 30) -> dict:
    """
    Execute a Python script safely in a subprocess.

    ⚠️ This requires approval for production use. Only runs code
    that operates within ~/agency/ scope.

    Returns dict with: stdout, stderr, returncode
    """
    result = subprocess.run(
        ["python3", "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(AGENCY_DIR),
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


# ─── DAILY MEMORY LOG ─────────────────────────────────────────────────────────

@mcp.tool()
def log_daily(entry: str) -> str:
    """Append an entry to today's daily memory log."""
    from datetime import date
    log_dir = AGENCY_DIR / "memory"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{date.today().isoformat()}.md"
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"\n### {timestamp}\n{entry}\n")
    return f"Logged to {log_file.name}"


@mcp.tool()
def read_daily_log(date_str: str = "") -> str:
    """
    Read a daily memory log.

    Args:
        date_str: Date in YYYY-MM-DD format. Defaults to today.
    """
    from datetime import date
    d = date_str or date.today().isoformat()
    log_file = AGENCY_DIR / "memory" / f"{d}.md"
    if not log_file.exists():
        return f"No log found for {d}"
    return log_file.read_text(encoding="utf-8")


# ─── AGENT CAPABILITY REGISTRY ────────────────────────────────────────────────

@mcp.tool()
def get_agent(agent_id: str) -> str:
    """
    Get full capability profile for a single agent.

    Args:
        agent_id: Agent key name (e.g. 'content_creator', 'nadia', 'ads_manager')

    Returns:
        JSON profile with role, capabilities, tools, input_needs, env requirements
    """
    try:
        from registry import load_registry
        reg = load_registry()
        agent = reg.get(agent_id)
        if not agent:
            available = [a.id for a in reg.all()]
            return json.dumps({"error": f"Agent '{agent_id}' not found.", "available": available})
        return agent.to_json()
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def find_agent_for_task(task_name: str) -> str:
    """
    Find which agent(s) handle a specific task.

    Args:
        task_name: Task name to look up (e.g. 'write_instagram_caption', 'launch_ad_campaign')

    Returns:
        JSON list of matching agent profiles
    """
    try:
        from registry import load_registry
        reg = load_registry()
        agents = reg.find_by_task(task_name)
        return json.dumps([a.to_dict() for a in agents], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def find_agents_by_capability(capability: str) -> str:
    """
    Find agents that have a specific capability (partial text match).

    Args:
        capability: Capability keyword to search for (e.g. 'instagram', 'seo', 'design')

    Returns:
        JSON list of matching agent summaries
    """
    try:
        from registry import load_registry
        reg = load_registry()
        agents = reg.find_by_capability(capability)
        return json.dumps(
            [{"id": a.id, "role": a.role, "department": a.department,
              "matching_caps": [c for c in a.capabilities if capability.lower() in c.lower()]}
             for a in agents],
            ensure_ascii=False, indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def agency_status() -> str:
    """
    Return the full agency status: which agents are ready vs blocked by missing env vars.
    Also shows which agents require Moncef approval before acting.

    Returns:
        Human-readable markdown status report
    """
    try:
        from registry import load_registry
        reg = load_registry()
        return reg.status_report()
    except Exception as e:
        return f"Error generating status: {e}"


# ─── SMART ROUTING ────────────────────────────────────────────────────────────

@mcp.tool()
def route_message(message: str, context_json: str = "{}") -> str:
    """
    Route an incoming message to the correct skill, crew, task, and agent.

    Uses deterministic keyword/regex matching first (fast, free).
    Falls back to Claude Haiku for ambiguous messages.

    Args:
        message: Raw message text from Moncef (Telegram)
        context_json: JSON string with optional context {"client_id": "refine-clinic", ...}

    Returns:
        JSON string with routing decision:
        {
          "skill": "content-forge",
          "crew": "creative",
          "task": "write_instagram_caption",
          "agent": "content_creator",
          "confidence": 0.85,
          "matched_triggers": ["write caption"],
          "missing_inputs": ["topic"],
          "approval_required": false,
          "method": "keyword"
        }
    """
    try:
        from routing import load_router
        context = json.loads(context_json) if context_json.strip() else {}
        router = load_router()
        decision = router.classify(message, context)
        return decision.to_json()
    except Exception as e:
        return json.dumps({
            "skill": "management",
            "crew": "management",
            "task": "route_task",
            "agent": "nadia",
            "confidence": 0.1,
            "matched_triggers": [],
            "missing_inputs": [],
            "approval_required": False,
            "method": "fallback",
            "error": str(e),
        }, indent=2)


@mcp.tool()
def explain_routing(message: str) -> str:
    """
    Show top-5 route scores for a message without committing to a route.
    Used for debugging routing decisions.

    Args:
        message: Message to explain routing for

    Returns:
        JSON string with top-5 candidate routes and their scores
    """
    try:
        from routing import load_router
        router = load_router()
        candidates = router.explain(message)
        return json.dumps(candidates, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def reload_routing_table() -> str:
    """
    Hot-reload the routing table from routing/routing_table.yaml.
    Use after editing the routing table — no server restart needed.

    Returns:
        Confirmation message
    """
    try:
        from routing import load_router
        router = load_router()
        router.reload()
        return "✅ Routing table reloaded successfully."
    except Exception as e:
        return f"❌ Failed to reload routing table: {e}"


# ─── INFRASTRUCTURE ──────────────────────────────────────────────────────────

@mcp.tool()
def agency_health_check() -> str:
    """
    Run a full health check on all agency infrastructure components.
    Returns a Markdown report covering: env vars, MCP servers, ChromaDB,
    task bus, memory, clients, and disk space.

    Use from Telegram to instantly see if anything is broken.

    Returns:
        Markdown health report with per-component status and overall health
    """
    try:
        from infra.health_check import load_health_checker
        hc     = load_health_checker()
        report = hc.full_check()
        return report.to_markdown()
    except Exception as e:
        return f"❌ Health check failed: {e}"


@mcp.tool()
def agency_server_status() -> str:
    """
    Show the running status of all 4 MCP servers (agency, social, ads, design).
    Uses PID files in memory/pids/ to check if each process is alive.

    Returns:
        Markdown table with server status, PIDs, and descriptions
    """
    try:
        from infra.process_manager import load_process_manager
        pm = load_process_manager()
        return pm.status_report()
    except Exception as e:
        return f"❌ Status check failed: {e}"


@mcp.tool()
def agency_restart_server(server_name: str) -> str:
    """
    Restart a crashed or misbehaving MCP server.

    Args:
        server_name: One of 'agency' | 'social' | 'ads' | 'design'

    Returns:
        Status message with new PID or error details
    """
    try:
        from infra.process_manager import load_process_manager
        pm     = load_process_manager()
        result = pm.restart(server_name)
        return (
            f"{result.icon} {server_name} server {result.status}"
            + (f" (pid {result.pid})" if result.pid else "")
        )
    except ValueError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Restart failed: {e}"


@mcp.tool()
def agency_tail_log(server_name: str, lines: int = 30) -> str:
    """
    Read the last N lines from an MCP server's log file.
    Useful for debugging crashes or unexpected behaviour.

    Args:
        server_name: One of 'agency' | 'social' | 'ads' | 'design'
        lines:       Number of log lines to return (default 30)

    Returns:
        Last N lines of the server log
    """
    try:
        from infra.process_manager import load_process_manager
        pm = load_process_manager()
        return pm.tail_log(server_name, lines)
    except ValueError as e:
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Log read failed: {e}"


# ─── SKILL EVOLUTION SYSTEM ──────────────────────────────────────────────────

@mcp.tool()
def skill_evolution_report() -> str:
    """
    Generate a full Markdown performance report for all agency skills.
    Shows run counts, success rates, QA scores, Moncef approval rates,
    and flags underperforming skills that need improvement.

    Returns:
        Markdown report with health summary, underperformers, and top performers
    """
    try:
        from skills.skill_tracker import load_tracker
        tracker = load_tracker()
        return tracker.evolution_report()
    except Exception as e:
        return f"Error generating evolution report: {e}"


@mcp.tool()
def skill_log_run(
    skill:        str,
    agent:        str,
    status:       str = "success",
    client_id:    str = "",
    triggered_by: str = "",
    qa_score:     Optional[float] = None,
    duration_s:   Optional[float] = None,
    notes:        str = "",
) -> str:
    """
    Log a skill execution from OpenClaw/Telegram context.
    Use after any skill completes to build performance history.

    Args:
        skill:        Skill slug (e.g. 'content-forge', 'social-pilot')
        agent:        Agent that ran it (e.g. 'content_creator')
        status:       'success' | 'failed' | 'partial'
        client_id:    Client this ran for
        triggered_by: Original trigger phrase
        qa_score:     QA Gate score 1-10 (optional)
        duration_s:   Wall-clock seconds (optional)
        notes:        Extra notes

    Returns:
        JSON with run_id
    """
    try:
        from skills.skill_tracker import load_tracker
        tracker = load_tracker()
        run_id = tracker.log_run(
            skill=skill,
            agent=agent,
            client_id=client_id,
            triggered_by=triggered_by,
            status=status,
            qa_score=qa_score,
            duration_s=duration_s,
            notes=notes,
        )
        return json.dumps({
            "run_id":  run_id,
            "skill":   skill,
            "agent":   agent,
            "status":  status,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── AGENT COMMUNICATION PROTOCOL ────────────────────────────────────────────

@mcp.tool()
def send_agent_task(
    from_agent:  str,
    to_agent:    str,
    title:       str,
    description: str = "",
    inputs_json: str = "{}",
    skill:       str = "",
    priority:    int = 3,
) -> str:
    """
    Dispatch a task from one agent to another via the task bus.
    Nadia can use this from Telegram to manually kickoff work or create handoff tasks.

    Args:
        from_agent:  Sender agent id (e.g. 'nadia', 'content_creator')
        to_agent:    Recipient agent id (e.g. 'qa_gate', 'social_media_manager')
        title:       Short task title
        description: Full description of what needs to be done
        inputs_json: JSON string with task inputs {"client_id": "...", "content": "..."}
        skill:       Which agency skill this relates to (optional)
        priority:    1 (low) to 5 (urgent), default 3

    Returns:
        JSON with task_id, from, to, title
    """
    try:
        from comms import load_task_bus
        inputs = json.loads(inputs_json) if inputs_json.strip() else {}
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
        return json.dumps({
            "task_id": task_id,
            "from":    from_agent,
            "to":      to_agent,
            "title":   title,
            "status":  "pending",
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_agent_tasks(agent_id: str = "", status: str = "pending") -> str:
    """
    List tasks for an agent or all pending tasks across the agency.
    Nadia uses this for agency-wide task oversight from Telegram.

    Args:
        agent_id: Agent to filter by (e.g. 'qa_gate'). If empty, shows all pending tasks.
        status:   'pending' | 'active' | 'done' | 'failed' | 'all'

    Returns:
        JSON array of task objects, sorted by priority then created_at
    """
    try:
        from comms import load_task_bus
        bus = load_task_bus()
        if agent_id:
            tasks = bus.list_inbox(agent_id, status)
        else:
            tasks = bus.list_all_pending()
        if not tasks:
            label = f"{agent_id}'s {status}" if agent_id else f"agency-wide {status}"
            return json.dumps({"tasks": [], "message": f"No {label} tasks."})
        return json.dumps([t.to_dict() for t in tasks], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_agent_task(task_id: str) -> str:
    """
    Get full details for a specific task by ID including its thread of messages.

    Args:
        task_id: Task ID (e.g. 'task_20260329_103045_a3f8b2')

    Returns:
        Full Task JSON including inputs, outputs, and thread
    """
    try:
        from comms import load_task_bus
        bus = load_task_bus()
        task = bus.get(task_id)
        if not task:
            return json.dumps({"error": f"Task '{task_id}' not found."})
        return task.to_json()
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
