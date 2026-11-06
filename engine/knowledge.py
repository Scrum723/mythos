from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import PACKAGE_ROOT
from .languages import IDIOMS

KNOWLEDGE_DIR = PACKAGE_ROOT / "data" / "knowledge"


def _read_json(name: str) -> dict[str, Any]:
    path = KNOWLEDGE_DIR / name
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=4)
def coding_languages() -> tuple[dict[str, Any], ...]:
    data = _read_json("coding_languages.json")
    rows = data.get("languages") or []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        lid = str(row.get("id") or "").strip().lower()
        if not lid or lid in seen:
            continue
        seen.add(lid)
        out.append(
            {
                "id": lid,
                "name": row.get("name") or lid,
                "extensions": list(row.get("extensions") or []),
                "idiom": row.get("idiom") or IDIOMS.get(lid, ""),
                "threat_notes": row.get("threat_notes") or "",
            }
        )
    # Ensure detector-supported languages appear even if JSON lags.
    for lid, idiom in IDIOMS.items():
        if lid in seen:
            continue
        out.append({"id": lid, "name": lid, "extensions": [], "idiom": idiom, "threat_notes": ""})
    return tuple(sorted(out, key=lambda r: r["id"]))


@lru_cache(maxsize=2)
def spoken_languages() -> tuple[dict[str, Any], ...]:
    data = _read_json("spoken_iso6391.json")
    rows = data.get("languages") or []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip().lower()
        name = str(row.get("name") or "").strip()
        if not code or not name or code in seen:
            continue
        seen.add(code)
        out.append({"code": code, "name": name, "scope": row.get("scope") or "spoken"})
    return tuple(sorted(out, key=lambda r: r["name"].lower()))


def spoken_language_count() -> int:
    return len(spoken_languages())


def synthesize_capabilities() -> dict[str, Any]:
    data = _read_json("capabilities.json")
    from .defense import local_threat_posture

    posture = local_threat_posture()
    return {
        "unit": data.get("unit") or "mythos",
        "honesty": data.get("honesty")
        or "Local synthesis of agent capabilities — not merged cloud model weights.",
        "combined_from": data.get("combined_from") or [],
        "domains": data.get("domains")
        or ["coding", "generative", "creative", "local-llm-ml", "defense"],
        "no_charges": bool(data.get("no_charges", True)),
        "remote_llm_forbidden": bool(data.get("remote_llm_forbidden", True)),
        "defense": posture,
        "coding_language_count": len(coding_languages()),
        "spoken_language_count": spoken_language_count(),
    }


def mcp_catalog() -> dict[str, Any]:
    data = _read_json("mcp_catalog.json")
    servers = data.get("servers") or []
    relevant = data.get("relevant_servers") or [s for s in servers if s.get("mythos_relevant")]
    return {
        "source": data.get("source") or "https://github.com/mcp",
        "scraped_pages": data.get("scraped_pages") or [],
        "scraped_count": data.get("scraped_count") or len(servers),
        "relevant_count": data.get("relevant_count") or len(relevant),
        "install_policy": data.get("install_policy")
        or "Catalog only — Mythos does not mass-install remote MCP servers.",
        "servers": servers,
        "relevant_servers": relevant,
    }


def knowledge_snapshot() -> dict[str, Any]:
    coding = coding_languages()
    spoken = spoken_languages()
    caps = synthesize_capabilities()
    mcp = mcp_catalog()
    from .defense import local_threat_posture

    return {
        "service": "mythos",
        "library_root": str(KNOWLEDGE_DIR),
        "coding": {
            "count": len(coding),
            "ids": [r["id"] for r in coding],
            "cards": list(coding),
        },
        "spoken": {
            "count": len(spoken),
            "languages": list(spoken),
        },
        "mcp": {
            "source": mcp["source"],
            "scraped_count": mcp["scraped_count"],
            "relevant_count": mcp["relevant_count"],
            "install_policy": mcp["install_policy"],
            "relevant_servers": mcp["relevant_servers"],
        },
        "capabilities": caps,
        "defense": local_threat_posture(),
        "weights_note": (
            "Mythos 'weights' here means local knowledge cards + local GGUF/Ollama brains on disk — "
            "not proprietary cloud model merges."
        ),
    }
