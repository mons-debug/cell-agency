"""
Cell Agency — Asset MCP Server
Provides: asset search, scoring/ranking, tagging, and discovery.

Uses ChromaDB for semantic search over asset metadata/tags.
Uses Pillow for image metadata extraction.
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastmcp import FastMCP
import chromadb

mcp = FastMCP("asset")

AGENCY_DIR = Path.home() / "agency"
CLIENTS_DIR = AGENCY_DIR / "clients"
CHROMA_PATH = AGENCY_DIR / ".chromadb"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

# ─── ChromaDB ─────────────────────────────────────────────────────────────────

_chroma_client = None

def _get_chroma():
    global _chroma_client
    if _chroma_client is None:
        CHROMA_PATH.mkdir(exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _chroma_client


def _get_asset_collection(client_id: str):
    """Get or create a per-client asset tag collection."""
    return _get_chroma().get_or_create_collection(f"assets_{client_id}")


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _scan_assets(client_id: str, asset_type: str = "all") -> list[Path]:
    """Scan client directories for asset files."""
    client_dir = CLIENTS_DIR / client_id
    results = []

    # Search in images/, videos/, logo/, and legacy assets/
    search_dirs = []
    if asset_type in ("all", "image"):
        search_dirs.extend([client_dir / "images", client_dir / "assets"])
        search_dirs.append(client_dir / "logo")
    if asset_type in ("all", "video"):
        search_dirs.append(client_dir / "videos")
        if asset_type == "all":
            search_dirs.append(client_dir / "assets")

    seen = set()
    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.iterdir():
            if f.is_file() and f not in seen:
                ext = f.suffix.lower()
                if asset_type == "all" and ext in IMAGE_EXTS | VIDEO_EXTS:
                    results.append(f)
                    seen.add(f)
                elif asset_type == "image" and ext in IMAGE_EXTS:
                    results.append(f)
                    seen.add(f)
                elif asset_type == "video" and ext in VIDEO_EXTS:
                    results.append(f)
                    seen.add(f)

    return sorted(results, key=lambda p: p.stat().st_mtime, reverse=True)


def _get_image_info(path: Path) -> dict:
    """Extract image metadata using Pillow."""
    info = {
        "path": str(path),
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        "type": "image" if path.suffix.lower() in IMAGE_EXTS else "video",
    }
    if path.suffix.lower() in IMAGE_EXTS:
        try:
            from PIL import Image
            with Image.open(path) as img:
                info["width"] = img.width
                info["height"] = img.height
                info["format"] = img.format
        except Exception:
            pass
    return info


# ─── SEARCH ASSETS ───────────────────────────────────────────────────────────

@mcp.tool()
def search_assets(
    client_id: str,
    query: str,
    asset_type: str = "all",
    limit: int = 10,
) -> str:
    """
    Search a client's assets by semantic query and/or filename pattern.

    Searches both file names and ChromaDB tags for matches.

    Args:
        client_id: Client identifier
        query: Search query (e.g. 'clinic exterior', 'pink tones', 'laser treatment')
        asset_type: Filter by type: 'all' | 'image' | 'video'
        limit: Max results to return

    Returns:
        JSON array of matching assets with metadata
    """
    results = []

    # 1. Search ChromaDB tags
    try:
        col = _get_asset_collection(client_id)
        chroma_results = col.query(query_texts=[query], n_results=limit)
        for i, doc_id in enumerate(chroma_results["ids"][0]):
            meta = chroma_results["metadatas"][0][i]
            path = Path(meta.get("path", ""))
            if path.exists():
                info = _get_image_info(path)
                info["tags"] = meta.get("tags", "").split(",") if meta.get("tags") else []
                info["match_source"] = "semantic"
                info["distance"] = chroma_results["distances"][0][i]
                results.append(info)
    except Exception:
        pass

    # 2. Filename search (fallback/supplement)
    query_lower = query.lower().replace(" ", "")
    for asset_path in _scan_assets(client_id, asset_type):
        name_lower = asset_path.stem.lower().replace("_", "").replace("-", "")
        if query_lower in name_lower or any(w in name_lower for w in query.lower().split()):
            info = _get_image_info(asset_path)
            info["match_source"] = "filename"
            # Avoid duplicates
            if not any(r["path"] == info["path"] for r in results):
                results.append(info)

    return json.dumps(results[:limit], indent=2, ensure_ascii=False)


# ─── CHOOSE BEST ASSETS ─────────────────────────────────────────────────────

@mcp.tool()
def choose_best_assets(
    client_id: str,
    brief: str,
    count: int = 3,
) -> str:
    """
    Score and rank available assets based on a creative brief.

    Args:
        client_id: Client identifier
        brief: Creative brief (e.g. 'spring promotion, pink tones, clinic exterior')
        count: Number of top assets to return

    Returns:
        JSON array of top-ranked assets with relevance scores
    """
    # Get all assets
    all_assets = _scan_assets(client_id)
    if not all_assets:
        return json.dumps({
            "message": f"No assets found for client '{client_id}'",
            "suggestion": "Upload images to clients/{client_id}/images/ first",
        })

    # Try semantic search first
    try:
        col = _get_asset_collection(client_id)
        chroma_results = col.query(query_texts=[brief], n_results=count)
        if chroma_results["ids"][0]:
            ranked = []
            for i, doc_id in enumerate(chroma_results["ids"][0]):
                meta = chroma_results["metadatas"][0][i]
                path = Path(meta.get("path", ""))
                if path.exists():
                    info = _get_image_info(path)
                    info["relevance_score"] = round(1.0 - chroma_results["distances"][0][i], 3)
                    info["tags"] = meta.get("tags", "").split(",") if meta.get("tags") else []
                    ranked.append(info)
            if ranked:
                return json.dumps(ranked, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Fallback: return most recent assets
    recent = [_get_image_info(p) for p in all_assets[:count]]
    for r in recent:
        r["relevance_score"] = 0.0
        r["note"] = "No tags found — assets returned by recency. Tag assets for better matching."
    return json.dumps(recent, indent=2, ensure_ascii=False)


# ─── TAG ASSETS ──────────────────────────────────────────────────────────────

@mcp.tool()
def tag_assets(
    client_id: str,
    asset_paths: str,
    tags: str,
) -> str:
    """
    Tag one or more assets with descriptive metadata for search.

    Args:
        client_id: Client identifier
        asset_paths: JSON array of file paths, e.g. '["clients/refine/images/clinic.jpg"]'
        tags: Comma-separated tags, e.g. 'clinic exterior, modern, pink tones, entrance'

    Returns:
        Confirmation with number of assets tagged
    """
    paths = json.loads(asset_paths) if isinstance(asset_paths, str) else asset_paths
    col = _get_asset_collection(client_id)

    tagged = 0
    for p in paths:
        path = Path(p).expanduser()
        if not path.is_absolute():
            path = AGENCY_DIR / p
        if not path.exists():
            continue

        doc_id = f"asset_{path.stem}_{hash(str(path)) % 10000}"
        tag_text = tags.strip()

        col.upsert(
            ids=[doc_id],
            documents=[tag_text],
            metadatas=[{
                "path": str(path),
                "name": path.name,
                "tags": tag_text,
                "client_id": client_id,
                "tagged_at": datetime.now().isoformat(),
            }],
        )
        tagged += 1

    return json.dumps({
        "tagged": tagged,
        "total_requested": len(paths),
        "tags": tags,
        "client_id": client_id,
    })


# ─── LIST ASSETS ─────────────────────────────────────────────────────────────

@mcp.tool()
def list_assets(
    client_id: str,
    asset_type: str = "all",
) -> str:
    """
    List all assets for a client with basic metadata.

    Args:
        client_id: Client identifier
        asset_type: 'all' | 'image' | 'video'

    Returns:
        JSON array of assets with name, type, size, dimensions
    """
    assets = _scan_assets(client_id, asset_type)
    if not assets:
        return json.dumps({
            "message": f"No {asset_type} assets found for '{client_id}'",
            "directories_checked": [
                f"clients/{client_id}/images/",
                f"clients/{client_id}/videos/",
                f"clients/{client_id}/logo/",
                f"clients/{client_id}/assets/",
            ],
        })

    return json.dumps(
        [_get_image_info(p) for p in assets],
        indent=2, ensure_ascii=False,
    )


# ─── GET ASSET INFO ──────────────────────────────────────────────────────────

@mcp.tool()
def get_asset_info(
    client_id: str,
    asset_path: str,
) -> str:
    """
    Get detailed info for a specific asset including tags and usage history.

    Args:
        client_id: Client identifier
        asset_path: Path to the asset file

    Returns:
        JSON with file metadata, dimensions, tags, and usage history
    """
    path = Path(asset_path).expanduser()
    if not path.is_absolute():
        path = AGENCY_DIR / asset_path
    if not path.exists():
        return json.dumps({"error": f"Asset not found: {asset_path}"})

    info = _get_image_info(path)

    # Look up tags in ChromaDB
    try:
        col = _get_asset_collection(client_id)
        # Search for this specific file
        results = col.get(where={"path": str(path)})
        if results["ids"]:
            info["tags"] = results["metadatas"][0].get("tags", "").split(",")
            info["tagged_at"] = results["metadatas"][0].get("tagged_at", "")
    except Exception:
        info["tags"] = []

    return json.dumps(info, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
