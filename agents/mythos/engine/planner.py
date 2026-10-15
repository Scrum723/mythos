from __future__ import annotations

import json
import re
from typing import Any

from .languages import detect

PLAN_HINTS = (
    ("test", "Run the relevant tests and report failures honestly"),
    ("deploy", "Treat deploy as destructive: confirm unless autonomy is 5"),
    ("auth", "Handle auth/crypto with extra care; no hardcoded secrets"),
    ("database", "Use parameterized queries; flag schema-destroying SQL"),
    ("refactor", "Keep the diff small and match existing style"),
    ("agent", "If a new agent is requested, spawn a standalone module"),
)


def heuristic_plan(task: str, root: Any = None, language: dict | None = None) -> dict[str, Any]:
    lang = language or (detect(root) if root is not None else {"primary": "unknown", "idiom": ""})
    lower = task.lower()
    subgoals = [
        {
            "id": "explore",
            "title": "Explore the repo and identify the files that matter",
            "depends_on": [],
            "risk": "safe",
        },
        {
            "id": "plan",
            "title": "Decompose the request, sequence work, and list dependencies",
            "depends_on": ["explore"],
            "risk": "safe",
        },
        {
            "id": "implement",
            "title": "Implement incrementally in the detected language",
            "depends_on": ["plan"],
            "risk": "write",
        },
        {
            "id": "verify",
            "title": "Run tests or the closest substitute and fix failures",
            "depends_on": ["implement"],
            "risk": "safe",
        },
        {
            "id": "review",
            "title": "Log one improvement and report honestly",
            "depends_on": ["verify"],
            "risk": "write",
        },
    ]
    risks = [
        "Path escape outside the project root",
        "Secret leakage via .env or credentials files",
        "Destructive shell if autonomy is set too high",
    ]
    extra = []
    for needle, title in PLAN_HINTS:
        if needle in lower:
            extra.append(title)
    if "rm " in lower or "delete" in lower:
        risks.append("Requested delete may be irreversible")
    return {
        "task": task,
        "language": lang.get("primary"),
        "idiom": lang.get("idiom"),
        "subgoals": subgoals,
        "risks": risks,
        "notes": extra,
        "source": "heuristic",
    }


def parse_llm_plan(raw: str, task: str, language: dict) -> dict[str, Any]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        plan = heuristic_plan(task, None, language)
        plan["source"] = "heuristic-fallback"
        return plan
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        plan = heuristic_plan(task, None, language)
        plan["source"] = "heuristic-fallback"
        return plan
    subgoals = data.get("subgoals") or []
    cleaned = []
    for i, item in enumerate(subgoals):
        if not isinstance(item, dict):
            continue
        cleaned.append(
            {
                "id": str(item.get("id") or f"g{i+1}"),
                "title": str(item.get("title") or item.get("name") or "untitled"),
                "depends_on": list(item.get("depends_on") or []),
                "risk": str(item.get("risk") or "write"),
            }
        )
    if not cleaned:
        return heuristic_plan(task, None, language)
    return {
        "task": task,
        "language": data.get("language") or language.get("primary"),
        "idiom": language.get("idiom"),
        "subgoals": cleaned,
        "risks": list(data.get("risks") or []),
        "notes": list(data.get("notes") or []),
        "source": "llm",
    }
