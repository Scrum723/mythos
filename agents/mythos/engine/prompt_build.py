from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from . import prefs
from .config import PACKAGE_ROOT, Settings
from .languages import detect

CORE = """You are Mythos, a local coding agent. NO CHARGES — local Ollama only, never xAI.
Stay in the project root. Never invent tool results. Never hardcode secrets.
Be direct: answer first, then brief detail. No filler. Match the user's tone.
Short by default. Prefer small diffs and existing patterns.
"""

CHAT_ADDON = """Mode: conversation. Reply like a sharp teammate.
Unless the user asks for code changes, do not start a long explore/plan cycle.
Use retrieve or batch_read when you need code context — one step, not wandering.
"""

CODE_ADDON = """Mode: coding. Explore with retrieve first, then batch_read the hits.
Implement, verify with tests when relevant, report what changed in a few lines.
Skip ceremonial planning for tiny tasks.
"""


@lru_cache(maxsize=8)
def _prefs_cached(mtime: float) -> str:
    return prefs.load()


def _prefs_block() -> str:
    path = prefs.prefs_path()
    mtime = path.stat().st_mtime if path.is_file() else 0.0
    text = _prefs_cached(mtime)
    # Keep prefs lean in the prompt.
    lines = [ln for ln in text.splitlines() if ln.strip()][:40]
    return "User preferences:\n" + "\n".join(lines)


@lru_cache(maxsize=32)
def _lang_cached(root: str, stamp: float) -> dict:
    return detect(Path(root))


def language_for(root: Path) -> dict:
    try:
        stamp = root.stat().st_mtime
    except OSError:
        stamp = 0.0
    return _lang_cached(str(root.resolve()), stamp)


def build_system(settings: Settings, *, mode: str = "code", extra: str | None = None) -> str:
    lang = language_for(settings.root)
    parts = [
        CORE,
        CHAT_ADDON if mode == "chat" else CODE_ADDON,
        f"Root: {settings.root}",
        f"Autonomy: {settings.autonomy}",
        f"Language: {lang.get('primary')} — {lang.get('idiom')}",
        _prefs_block(),
    ]
    if extra:
        parts.append(extra)
    return "\n\n".join(parts)


def prompt_stats(settings: Settings, *, mode: str = "code") -> dict:
    slim = build_system(settings, mode=mode)
    # Old behavior dumped constitution + prompt every turn.
    old_bits = []
    for name in ("CONSTITUTION.md", "PROMPT.md"):
        path = PACKAGE_ROOT / name
        if path.is_file():
            old_bits.append(path.read_text(encoding="utf-8"))
    old = "\n\n".join(old_bits) if old_bits else slim
    return {
        "mode": mode,
        "slim_chars": len(slim),
        "old_chars": len(old),
        "reduction_pct": round(100.0 * (1 - len(slim) / max(len(old), 1)), 1),
    }
