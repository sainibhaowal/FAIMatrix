"""FAIM Environment Loader.

Loads environment variables from .env file.
SECURITY: Loads from project root .env file only.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file() -> None:
    """Load environment variables from .env file.

    Looks for .env in:
    1. FAIM_ENV_FILE environment variable
    2. Project root (parent of faim package)
    3. Current working directory
    """
    if os.getenv("FAIM_ENV_LOADED") == "1":
        return

    # Find project root (parent of faim package)
    faim_root = Path(os.getenv("FAIM_ROOT", Path(__file__).resolve().parents[1])).resolve()

    # Possible .env locations (in priority order)
    possible_paths = [
        Path(os.getenv("FAIM_ENV_FILE", "")) if os.getenv("FAIM_ENV_FILE") else None,
        faim_root / ".env",
        Path.cwd() / ".env",
    ]

    env_path = None
    for p in possible_paths:
        if p and p.exists():
            env_path = p
            break

    if env_path and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            if not key:
                continue
            value = value.strip().strip('"').strip("'")
            # Only set if not already in environment (env vars take precedence)
            if key not in os.environ:
                os.environ[key] = value

    os.environ["FAIM_ENV_LOADED"] = "1"
