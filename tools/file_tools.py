"""File tools — safe file operations scoped to agency roots."""
import shutil
from pathlib import Path

from core.paths import get_agency_dir

AGENCY_DIR = get_agency_dir()

ALLOWED_ROOTS = [
    AGENCY_DIR / "clients",
    AGENCY_DIR / "skills",
    AGENCY_DIR / "memory",
]


def _safe_path(path: str) -> Path:
    """Resolve path and verify it's inside an allowed root. Raises ValueError if not."""
    resolved = Path(path).expanduser().resolve()
    for root in ALLOWED_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            continue
    raise ValueError(
        f"Path '{path}' is outside allowed directories: {[str(r) for r in ALLOWED_ROOTS]}"
    )


def read_file(path: str) -> str:
    """Read and return file contents."""
    p = _safe_path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return p.read_text(encoding="utf-8")


def write_file(path: str, content: str, overwrite: bool = True) -> str:
    """Write content to a file. Creates parent directories if needed."""
    p = _safe_path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {path}. Set overwrite=True to replace.")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Written: {path} ({len(content)} chars)"


def append_file(path: str, content: str) -> str:
    """Append content to a file. Creates file if it doesn't exist."""
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(content)
    return f"Appended {len(content)} chars to {path}"


def list_dir(path: str, pattern: str = "*") -> list[str]:
    """List files in a directory matching a glob pattern."""
    p = _safe_path(path)
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")
    return [str(item.relative_to(AGENCY_DIR)) for item in p.glob(pattern)]


def create_dir(path: str) -> str:
    """Create a directory (and parents) if it doesn't exist."""
    p = _safe_path(path)
    p.mkdir(parents=True, exist_ok=True)
    return f"Directory ready: {path}"


def delete_file(path: str) -> str:
    """Delete a file."""
    p = _safe_path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    p.unlink()
    return f"Deleted: {path}"


def move_file(src: str, dst: str) -> str:
    """Move a file from src to dst."""
    src_p = _safe_path(src)
    dst_p = _safe_path(dst)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_p), str(dst_p))
    return f"Moved: {src} → {dst}"


def file_exists(path: str) -> bool:
    """Check if a file exists."""
    try:
        p = _safe_path(path)
        return p.exists()
    except ValueError:
        return False
