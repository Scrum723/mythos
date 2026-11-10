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
    {
        "id": "agency",
        "title": "Local free-will agency",
        "body": "self-prompt / defer / ignore-note agenda under data/agency/. No remote MCP required. Run: python agent.py agency status",
    },
    {
        "id": "poteto",
        "title": "Poteto ops method",
        "body": "Trust ladder, one job per bot, chief of staff, routines ≤ hourly, closed loops with proof. See data/knowledge/playbooks/poteto-ops.md",
    },
    {
        "id": "creator",
        "title": "Creator flywheel",
        "body": "Learn→idea→script→edit→distribute→analyze. Human-in-the-loop publish. See data/knowledge/playbooks/creator-flywheel.md",
    },
    {
        "id": "neural",
        "title": "Neural pattern graph",
        "body": "Ingested open-source Grok-bot/agent patterns under data/knowledge/neural/. Run: python agent.py neural status && python agent.py neural train",
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
