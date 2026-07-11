"""Helpers for loading environment configuration from files and the process environment."""

import os
from pathlib import Path


def load_environment(env_file: str | os.PathLike[str] | None = None) -> None:
    """Load values from a .env-style file into os.environ when not already set."""
    candidate = Path(env_file) if env_file is not None else Path(".env")
    if not candidate.exists():
        return

    for raw_line in candidate.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
