from __future__ import annotations

from typing import Any

from . import improve, prefs
from .brain_status import brain_status
from .config import PACKAGE_ROOT, Settings
from .network_policy import airgap_enabled


CORE_LESSONS = [
    {
        "id": "ownership",
        "title": "You own Mythos",
        "body": "Mythos is a standalone local agent. Brains live on disk. NO CHARGES — never api.x.ai.",
    },
    {
        "id": "modes",
        "title": "Modes",
        "body": "code explores and implements; create is generative/creative without forced explore; chat is conversation.",
    },
    {
        "id": "offline",
        "title": "Offline readiness",
        "body": "Prefer loopback Ollama, or a GGUF under models/ with llama-cpp-python when the daemon is down. Airgap blocks remote pulls.",
    },
    {
        "id": "method",
        "title": "Efficient coding method",
        "body": "look → write files → run/serve → verify → fix → log one improvement. Never invent fake APIs.",
    },
    {
        "id": "knowledge",
        "title": "Local knowledge library",
        "body": "Coding cards (Python, HTML/JS/CSS, Java, C/C++, COBOL, R, MATLAB, …) and a planet-scale spoken-language catalog live under data/knowledge/. Run: python agent.py knowledge.",
    },
    {
        "id": "defense",
        "title": "Local exterior-threat protection",
        "body": "Loopback-only LLM, secret redaction, path sandbox, airgap. Mythos protects locally — it is not a cloud SOC.",
    },
    {
        "id": "mcp_catalog",
        "title": "GitHub MCP catalog (local library)",
        "body": "Pages 1–10 of https://github.com/mcp are catalogued under data/knowledge/mcp_catalog.json; later pages scoured for Mythos-relevant tools. Catalog ≠ mass-install — keep standalone local.",
    },
]


def educate_report(settings: Settings) -> dict[str, Any]:
    """Local-only teaching report. Never opens remote URLs."""
    status = brain_status(settings)
    recent = improve.read_all(limit=20)
    pref_text = prefs.load()
    lessons = list(CORE_LESSONS)
    for row in recent[:10]:
        note = (row.get("note") or "").strip()
        if not note:
            continue
        lessons.append(
            {
                "id": f"improve:{(row.get('area') or 'general')}",
                "title": f"Logged improvement — {row.get('area') or 'general'}",
                "body": note,
                "ts": row.get("ts"),
            }
        )
    constitution = PACKAGE_ROOT / "CONSTITUTION.md"
    prompt = PACKAGE_ROOT / "PROMPT.md"
    return {
        "service": "mythos",
        "lessons": lessons,
        "preferences_chars": len(pref_text or ""),
        "constitution_present": constitution.is_file(),
        "prompt_present": prompt.is_file(),
        "offline_ready": status.get("offline_ready"),
        "gguf_present": status.get("gguf_present"),
        "runner": status.get("runner"),
        "airgap": status.get("airgap") or airgap_enabled(),
        "network_mode": status.get("network_mode"),
        "bills_xai": False,
        "remote_fetches": 0,
    }
