"""Tiny .env loader (no dependency). Variables already set in the environment win.

Format: KEY=VALUE per line; blank lines and lines starting with # are ignored;
an optional `export ` prefix and matching single or double quotes are stripped.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env(path: str | Path | None = None) -> dict[str, str]:
    """Load the first .env found (given path, then the working directory, then the project root).

    Returns the variables that were set by this call.
    """
    candidates = [Path(path)] if path else [Path.cwd() / ".env", PROJECT_ROOT / ".env"]
    for file in candidates:
        if file.is_file():
            return _apply(file.read_text(encoding="utf-8-sig"))
    return {}


def _apply(text: str) -> dict[str, str]:
    applied: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            applied[key] = value
    return applied
