from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import PACKAGE_ROOT, Settings
from .defense import local_threat_posture, scan_exterior_risks
from .knowledge import knowledge_snapshot
from .languages import detect
from .planner import heuristic_plan
from .prompt_build import mode_skips_code_explore, normalize_mode, resolve_mode
from .security import redact
from .tools import ToolBox


def is_standalone_ready() -> bool:
    """True when Mythos can operate with zero model dependency."""
    knowledge = PACKAGE_ROOT / "data" / "knowledge"
    required = (
        knowledge / "coding_languages.json",
        knowledge / "spoken_iso6391.json",
        knowledge / "capabilities.json",
        PACKAGE_ROOT / "engine" / "tools.py",
        PACKAGE_ROOT / "engine" / "defense.py",
    )
    return all(p.is_file() for p in required)


def run_standalone(
    task: str,
    *,
    settings: Settings,
    mode: str | None = None,
    confirmer=None,
) -> dict[str, Any]:
    """Deterministic local engine — no Ollama, GGUF, or remote LLM."""
    mode = resolve_mode(task, mode)
    lang = detect(settings.root)
    box = ToolBox(settings, confirmer=confirmer)
    events: list[dict[str, Any]] = [{"type": "standalone", "data": {"mode": mode, "model_required": False}}]

    if mode_skips_code_explore(mode) and mode == "create":
        report = _create_without_model(task, lang)
        events.append({"type": "report", "data": {"ok": True, "report": report}})
        return {
            "ok": True,
            "report": report,
            "plan": {"task": task, "subgoals": [], "source": "standalone-create"},
            "events": events,
            "language": lang.get("primary", "unknown"),
            "used_llm": False,
        }

    if mode == "chat" or mode_skips_code_explore(mode):
        report = _chat_without_model(task, settings, lang)
        events.append({"type": "report", "data": {"ok": True, "report": report}})
        return {
            "ok": True,
            "report": report,
            "plan": {"task": task, "subgoals": [], "source": "standalone-chat"},
            "events": events,
            "language": lang.get("primary", "unknown"),
            "used_llm": False,
        }

    plan = heuristic_plan(task, settings.root, lang)
    plan["source"] = "standalone-heuristic"
    events.append({"type": "plan", "data": plan})
    report = _code_without_model(task, settings, lang, plan, box)
    events.append({"type": "report", "data": {"ok": True, "report": report}})
    return {
        "ok": True,
        "report": report,
        "plan": plan,
        "events": events,
        "language": lang.get("primary", "unknown"),
        "used_llm": False,
    }


def _chat_without_model(task: str, settings: Settings, lang: dict[str, Any]) -> str:
    snap = knowledge_snapshot()
    posture = local_threat_posture()
    risks = scan_exterior_risks(api_base=settings.api_base, airgap=bool(getattr(settings, "airgap", False)))
    lower = task.lower()
    parts = [
        "Mythos standalone (model-independent).",
        f"Workspace language: {lang.get('primary')} — {lang.get('idiom')}",
        f"Coding library: {snap['coding']['count']} languages; spoken catalog: {snap['spoken']['count']}.",
        f"Defense: local_only={posture['local_only']}, allows_remote_llm={posture['allows_remote_llm']}.",
    ]
    if any(k in lower for k in ("health", "status", "ready", "offline")):
        parts.append("Standalone stage: ready without any model. Optional local brains only accelerate generative quality.")
    if any(k in lower for k in ("threat", "protect", "security", "airgap", "risk")):
        parts.append("Exterior risks: " + json.dumps(risks, indent=2))
    if any(k in lower for k in ("language", "coding", "python", "cobol", "matlab")):
        parts.append("Supported coding ids: " + ", ".join(snap["coding"]["ids"][:20]) + ", …")
    if "mcp" in lower:
        mcp = snap.get("mcp") or {}
        parts.append(
            f"MCP catalog: scraped={mcp.get('scraped_count')} relevant={mcp.get('relevant_count')} "
            f"(catalog only — not required to run)."
        )
    parts.append(f"You asked: {task.strip()}")
    parts.append(
        "Answer (standalone): I can inspect this project with local tools, apply the knowledge library, "
        "and enforce local defense without calling any model. Ask a concrete coding or create task to go further."
    )
    return redact("\n\n".join(parts))


def _create_without_model(task: str, lang: dict[str, Any]) -> str:
    seed = task.strip() or "a quiet machine that keeps watch"
    # Deterministic creative scaffold — not an LLM, but usable offline generative output.
    title = "Mythos fragment"
    body = (
        f"In a valley of {lang.get('primary', 'code')} rivers, {seed.rstrip('.')}. "
        "The local guardian kept every secret inside the mountain and refused the distant towers. "
        "No bill crossed the water. No stranger model was required. "
        "When storms asked for tribute, Mythos answered with tools already on the shore."
    )
    return redact(
        "Mythos standalone create (no model).\n\n"
        f"# {title}\n\n{body}\n\n"
        "— generated locally from the task text + knowledge posture; quality improves if you later add an optional on-disk brain, "
        "but standalone operation does not depend on one."
    )


def _code_without_model(
    task: str,
    settings: Settings,
    lang: dict[str, Any],
    plan: dict[str, Any],
    box: ToolBox,
) -> str:
    listing = box.execute("list_dir", {"path": "."})
    detect_out = box.execute("detect_language", {})
    retrieve_out = ""
    lower = task.lower()
    if any(k in lower for k in ("explore", "summarize", "structure", "repo", "find", "where")):
        try:
            retrieve_out = box.execute("retrieve", {"query": task[:120], "limit": 5})
        except Exception:
            retrieve_out = ""
    git_out = ""
    if "git" in lower or "status" in lower:
        git_out = box.execute("git_status", {})

    sections = [
        "Mythos standalone coding pass (model-independent).",
        f"Task: {task}",
        f"Detected: {detect_out}",
        "Plan:\n" + json.dumps(plan, indent=2),
        "Root listing:\n" + listing[:4000],
    ]
    if retrieve_out:
        sections.append("Retrieve:\n" + retrieve_out[:4000])
    if git_out:
        sections.append("Git:\n" + git_out[:2000])
    sections.append(
        "Next (still no model required): name a file to read/edit, or ask to run tests. "
        "Optional local Ollama/GGUF only upgrades free-form generation — tools and defense already work."
    )
    return redact("\n\n".join(sections))
