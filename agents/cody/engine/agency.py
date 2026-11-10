from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import PACKAGE_ROOT


def default_store() -> "AgencyStore":
    data = PACKAGE_ROOT / "data" / "agency"
    data.mkdir(parents=True, exist_ok=True)
    return AgencyStore(data / "agenda.jsonl")


@dataclass
class AgencyStore:
    path: Path

    def append(self, entry: dict[str, Any]) -> dict[str, Any]:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "status": entry.get("status") or "queued",
            "kind": entry.get("kind") or "note",
            "prompt": (entry.get("prompt") or "").strip(),
            "reason": (entry.get("reason") or "").strip(),
            "autonomy": entry.get("autonomy"),
            "wake_at": entry.get("wake_at"),
            "meta": entry.get("meta") or {},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def read_all(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(rows))


def self_prompt(prompt: str, *, store: AgencyStore | None = None, autonomy: int | None = None) -> dict[str, Any]:
    """Queue a local self-directed follow-up for Mythos (free-will agency)."""
    text = (prompt or "").strip()
    if not text:
        raise ValueError("self_prompt requires a non-empty prompt")
    store = store or default_store()
    return store.append(
        {
            "kind": "self_prompt",
            "prompt": text,
            "status": "queued",
            "autonomy": autonomy,
            "reason": "local free-will agency",
        }
    )


def defer_self(
    *,
    seconds: int = 60,
    reason: str = "",
    store: AgencyStore | None = None,
) -> dict[str, Any]:
    """Schedule a local wake reminder — no remote scheduler required."""
    seconds = max(1, int(seconds))
    wake = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    store = store or default_store()
    return store.append(
        {
            "kind": "defer",
            "prompt": f"wake after {seconds}s",
            "reason": reason or "deferred by agency",
            "status": "deferred",
            "wake_at": wake.isoformat(),
            "meta": {"seconds": seconds},
        }
    )


def ignore_with_note(note: str, *, store: AgencyStore | None = None) -> dict[str, Any]:
    """Record that a request was consciously set aside (local audit trail)."""
    text = (note or "").strip() or "ignored without detail"
    store = store or default_store()
    return store.append(
        {
            "kind": "ignore_note",
            "prompt": "",
            "reason": text,
            "status": "ignored",
        }
    )


def list_agenda(*, store: AgencyStore | None = None, limit: int = 50) -> list[dict[str, Any]]:
    store = store or default_store()
    return store.read_all(limit=limit)


def agency_snapshot(*, store: AgencyStore | None = None) -> dict[str, Any]:
    items = list_agenda(store=store)
    queued = [i for i in items if i.get("status") == "queued"]
    return {
        "service": "mythos",
        "agency": "free-will-local",
        "model_required": False,
        "remote_mcp_required": False,
        "queued": len(queued),
        "total": len(items),
        "items": items[:20],
        "tools": ["self_prompt", "defer_self", "ignore_with_note", "list_agenda"],
        "note": (
            "Local free-will agency inspired by free-will patterns (self-prompt, defer, ignore-note). "
            "Runs inside Mythos with no remote MCP and no cloud model."
        ),
    }
