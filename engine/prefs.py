from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .config import PACKAGE_ROOT

DEFAULT = """# Mythos preferences

## Style
- Be direct. Lead with the answer. No filler ("Sure!", "I'd be happy to", "As an AI").
- Short by default. Detail only when asked or when debugging.
- Match the user's tone.

## Stack
- Prefer local Ollama. NO CHARGES — never call xAI.
- Python stdlib when possible.

## Coding
- Small diffs. Match surrounding style.
- Tests alongside changes.
- Stay in the project root.

## Explaining
- Front-load the answer, then the why.
"""


def prefs_path() -> Path:
    data = PACKAGE_ROOT / "data"
    data.mkdir(parents=True, exist_ok=True)
    path = data / "preferences.md"
    if not path.is_file():
        path.write_text(DEFAULT, encoding="utf-8")
    return path


def load() -> str:
    return prefs_path().read_text(encoding="utf-8")


def append(note: str) -> str:
    note = (note or "").strip()
    if not note:
        raise ValueError("preference note is required")
    path = prefs_path()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## Learned {stamp}\n- {note}\n")
    return f"recorded preference ({len(note)} chars)"
