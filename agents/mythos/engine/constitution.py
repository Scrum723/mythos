from __future__ import annotations

import json
from typing import Any

from .config import PACKAGE_ROOT

FALLBACK = """You are the Coding agent. Ship working code. Be honest.
Never fabricate results. Stay in the project root. Confirm destructive actions
unless autonomy is 5. After each task, log one improvement.
This project is independent. Other agents are targets to improve, not parents.
"""


def load_constitution() -> str:
    path = PACKAGE_ROOT / "CONSTITUTION.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return FALLBACK


def load_prompt() -> str:
    path = PACKAGE_ROOT / "PROMPT.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def identity() -> dict[str, Any]:
    path = PACKAGE_ROOT / "manifest.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        name = str(data.get("name") or "coding")
        role = str(data.get("role") or "local coding agent")
        return {"name": name, "role": role, "tools": data.get("tools") or []}
    return {"name": "coding", "role": "local coding agent", "tools": []}
