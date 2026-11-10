from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import PACKAGE_ROOT

NEURAL_DIR = PACKAGE_ROOT / "data" / "knowledge" / "neural"
PLAYBOOKS_DIR = PACKAGE_ROOT / "data" / "knowledge" / "playbooks"


@lru_cache(maxsize=2)
def load_graph() -> dict[str, Any]:
    path = NEURAL_DIR / "graph.json"
    if not path.is_file():
        return {
            "version": 1,
            "unit": "mythos-neural-network",
            "source_count": 0,
            "ingested_readmes": 0,
            "nodes": [],
            "edges": [],
            "honesty": "Neural graph missing — run ingest.",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "nodes": [], "edges": [], "source_count": 0, "ingested_readmes": 0}
    return data if isinstance(data, dict) else {"nodes": [], "edges": []}


def playbooks() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not PLAYBOOKS_DIR.is_dir():
        return rows
    for path in sorted(PLAYBOOKS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        rows.append({"id": path.stem, "path": str(path.relative_to(PACKAGE_ROOT)), "chars": len(text)})
    return rows


def neural_snapshot() -> dict[str, Any]:
    graph = load_graph()
    nodes = graph.get("nodes") or []
    domains: dict[str, int] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        dom = str(node.get("domain") or "general")
        domains[dom] = domains.get(dom, 0) + 1
    return {
        "unit": graph.get("unit") or "mythos-neural-network",
        "honesty": graph.get("honesty")
        or "Local pattern graph — not proprietary weight merge; no xAI required.",
        "no_charges": bool(graph.get("no_charges", True)),
        "source_count": graph.get("source_count") or len(nodes),
        "ingested_readmes": graph.get("ingested_readmes")
        or sum(1 for n in nodes if isinstance(n, dict) and n.get("readme_ingested")),
        "domains": domains,
        "playbooks": playbooks(),
        "edges": graph.get("edges") or [],
        "nodes": [
            {
                "id": n.get("id"),
                "url": n.get("url"),
                "domain": n.get("domain"),
                "readme_ingested": n.get("readme_ingested"),
                "vendor_policy": n.get("vendor_policy"),
                "summary": (n.get("summary") or "")[:240],
            }
            for n in nodes
            if isinstance(n, dict)
        ],
    }


def train_from_neural(*, note: str | None = None) -> dict[str, Any]:
    """Local 'train' step: log an improvement + enqueue evolution from neural graph.

    Does not fine-tune model weights. Hardens Mythos knowledge/ops from ingested patterns.
    """
    from . import improve
    from .agency import self_prompt

    snap = neural_snapshot()
    msg = note or (
        f"Neural train: {snap['source_count']} sources, {snap['ingested_readmes']} readmes, "
        f"playbooks={[p['id'] for p in snap['playbooks']]}"
    )
    logged = improve.append({"area": "neural", "note": msg, "task": "neural-train"})
    follow = self_prompt(
        "Mythos Extreme: apply poteto-ops + creator-flywheel + neural graph domains to harden council seats",
        autonomy=3,
    )
    return {"ok": True, "improvement": logged, "followup": follow, "snapshot": {
        "source_count": snap["source_count"],
        "ingested_readmes": snap["ingested_readmes"],
        "domains": snap["domains"],
        "playbooks": [p["id"] for p in snap["playbooks"]],
    }}
