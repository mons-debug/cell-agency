"""
Shared path resolution for Cell Agency runtime.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_agency_dir() -> Path:
    """
    Resolve the agency root directory with sensible fallbacks.

    Priority:
    1) AGENCY_DIR environment variable
    2) ~/agency (legacy default)
    3) Repository root (parent of /core)
    """
    env_dir = os.getenv("AGENCY_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    legacy_dir = (Path.home() / "agency").resolve()
    if legacy_dir.exists():
        return legacy_dir

    return Path(__file__).resolve().parent.parent
