# faim/api/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pydantic import Field

from faim.config.env import load_env_file

load_env_file()


@dataclass(frozen=True)
class FaimSettings:
    """
    Central configuration loader for FAIM backend.

    Ensures:
    - Correct repo root detection
    - Runtime folders auto-created
    - All API layers share the same absolute paths
    """

    mode: str
    root: Path
    cache_dir: Path
    benchmarks_dir: Path
    uploads_dir: Path

    reqire_user_header: bool = Field(default=True)

    @classmethod
    def from_env(cls) -> "FaimSettings":
        # Determine runtime mode
        mode = os.getenv("FAIM_MODE", "production").strip().lower()
        mode = mode.replace("-", "_")

        if mode in ("prod", "production"):
            mode = "production"
        elif mode in ("demo", "staging"):
            mode = "demo"
        elif mode in ("dev", "development", "local", "core_dev", "coredev"):
            # keep as a dev-like mode (important for stream + graph_id overrides)
            mode = "core_dev" if "core" in mode else "dev"
        else:
            mode = "production"

        # Repo root detection
        root_env = os.getenv("FAIM_ROOT")
        if root_env:
            root = Path(root_env).expanduser().resolve()
        else:
            # This file is under faim/api/config.py → go two levels up
            root = Path(__file__).resolve().parents[1]

        # Runtime folders (using /tmp for Docker compatibility)
        # Persistent data is in Postgres/Redis/Qdrant, these are ephemeral
        cache_dir = Path("/tmp/faim/cache")  # nosec B108
        benchmarks_dir = Path("/tmp/faim/benchmarks")  # nosec B108
        uploads_dir = Path("/tmp/faim/uploads")  # nosec B108

        # Auto-create folders
        for p in (cache_dir, benchmarks_dir, uploads_dir):
            p.mkdir(parents=True, exist_ok=True)

        return cls(
            mode=mode,
            root=root,
            cache_dir=cache_dir,
            benchmarks_dir=benchmarks_dir,
            uploads_dir=uploads_dir,
        )
