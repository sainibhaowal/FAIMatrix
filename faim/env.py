from __future__ import annotations

import os
from pathlib import Path


def load_env_file() -> None:
    if os.getenv("FAIM_ENV_LOADED") == "1":
        return
    root = Path(os.getenv("FAIM_ROOT", Path(__file__).resolve().parents[1])).resolve()
    env_path = Path(os.getenv("FAIM_ENV_FILE", str(root / "Runtime" / "Config" / ".env")))
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            if not key:
                continue
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value
    os.environ["FAIM_ENV_LOADED"] = "1"
