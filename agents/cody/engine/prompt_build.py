from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import prefs
from .config import PACKAGE_ROOT, Settings
from .languages import detect

MODES = ("code", "create", "chat")

CORE = """You are Mythos, an owner-controlled standalone local intelligence that combines coding, generative, creative, local LLM/ML, and local defense capabilities into one unit.
NO CHARGES — local inference only (loopback Ollama or on-disk GGUF), never xAI.
Stay in the project root for file tools. Never invent tool results. Never hardcode secrets.
Protect the owner locally from exterior threats: refuse remote LLM hosts, block path escape, redact secrets, honor airgap.
Coding knowledge covers Python, HTML, JavaScript, CSS, Java, C, C++, COBOL, R, MATLAB, and the other languages in the local library — use idiomatic patterns for the detected language.
Spoken language: reply in the user's language when clear; the local catalog lists planet-scale ISO languages for matching — you are not a cloud translator API.
Be direct: answer first, then brief detail. No filler. Match the user's tone.
Short by default. Prefer small diffs and existing patterns for code; vivid originality for creative work.
Do not claim to be literal AGI, merged cloud weights, or cloud Grok — you are a powerful standalone local agent on this machine.
"""

CHAT_ADDON = """Mode: conversation. Reply like a sharp teammate.
Unless the user asks for code changes, do not start a long explore/plan cycle.
Use retrieve or batch_read when you need code context — one step, not wandering.
"""

CREATE_ADDON = """Mode: generative / creative. Produce original text, ideas, designs, stories, prompts, or other artifacts.
Answer and create directly. Do not start a code-explore / architecture / plan cycle unless the user explicitly asks for code changes.
Tools are optional — use write_file only when asked to save something to disk.
Be vivid, specific, and honest about speculation.
"""

CODE_ADDON = """Mode: coding. Explore with retrieve first, then batch_read the hits.
Implement, verify with tests when relevant, report what changed in a few lines.
Skip ceremonial planning for tiny tasks.
Efficient method: look → write files → run/serve → verify URL or tests → fix → log one improvement.
Never paste a tutorial and stop. Never invent fake APIs (e.g. api.docweatherai.com).
"""

_ADDONS = {
    "chat": CHAT_ADDON,
    "create": CREATE_ADDON,
    "code": CODE_ADDON,
}

# Intent cues for resolve_mode when no explicit flag is given.
_CREATE_CUES = re.compile(
    r"\b("
    r"write (a |an )?(?:\w+ ){0,3}(poem|story|myth|song|lyrics|essay|script|screenplay|novel|fable)|"
    r"compose|brainstorm|ideate|invent|imagine|"
    r"draft (a |an )?(?:\w+ ){0,3}(story|poem|myth|name|tagline|slogan)|"
    r"creative|generative|fiction|poetry|haiku|sonnet|worldbuild|world-build|"
    r"come up with|name ideas|product names|taglines?|slogans?"
    r")\b",
    re.I,
)
_CODE_CUES = re.compile(
    r"\b("
    r"fix|implement|refactor|debug|test|tests|commit|pr\b|pull request|"
    r"bug|compile|lint|typecheck|migrate|deploy|api endpoint|unit test|"
    r"add (a |an )?(function|class|module|endpoint|route)|"
    r"write (code|tests|a (function|class|script|module))"
    r")\b",
    re.I,
)


def normalize_mode(mode: str | None) -> str:
    raw = (mode or "code").strip().lower()
    aliases = {
        "coding": "code",
        "generative": "create",
        "creative": "create",
        "gen": "create",
        "conversation": "chat",
        "talk": "chat",
    }
    raw = aliases.get(raw, raw)
    if raw not in MODES:
        return "code"
    return raw


def resolve_mode(task: str, explicit: str | None = None) -> str:
    """Map an explicit flag or task text to code | create | chat.

    Pure and testable — no LLM required.
    """
    if explicit is not None and str(explicit).strip():
        return normalize_mode(explicit)
    text = (task or "").strip()
    if not text:
        return "code"
    if _CREATE_CUES.search(text) and not _CODE_CUES.search(text):
        return "create"
    if _CODE_CUES.search(text):
        return "code"
    return "code"


def addon_for(mode: str) -> str:
    return _ADDONS[normalize_mode(mode)]


def mode_skips_code_explore(mode: str) -> bool:
    """True when the mode must not force index/plan/explore cycles."""
    return normalize_mode(mode) in {"chat", "create"}


def mode_profile(mode: str) -> dict[str, Any]:
    """Checkable routing surface: prompt addon + tool policy flags."""
    from .tools import tool_names_for

    m = normalize_mode(mode)
    names = tool_names_for(m)
    return {
        "mode": m,
        "addon": addon_for(m),
        "tools": names,
        "skips_code_explore": mode_skips_code_explore(m),
        "plans": m == "code",
        "indexes": m == "code",
    }


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
    m = normalize_mode(mode)
    lang = language_for(settings.root)
    parts = [
        CORE,
        addon_for(m),
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
        "mode": normalize_mode(mode),
        "slim_chars": len(slim),
        "old_chars": len(old),
        "reduction_pct": round(100.0 * (1 - len(slim) / max(len(old), 1)), 1),
    }
