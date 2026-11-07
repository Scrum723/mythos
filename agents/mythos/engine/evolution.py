from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agency import AgencyStore, default_store, list_agenda, self_prompt
from .config import PACKAGE_ROOT, Settings
from .extreme import run_extreme


def ledger_path() -> Path:
    path = PACKAGE_ROOT / "data" / "evolution"
    path.mkdir(parents=True, exist_ok=True)
    return path / "cycles.jsonl"


def default_agency_store() -> AgencyStore:
    return default_store()


def _pop_next_prompt(agency: AgencyStore) -> dict[str, Any] | None:
    items = agency.read_all(limit=200)
    for item in items:
        if item.get("kind") == "self_prompt" and item.get("status") == "queued":
            # Mark consumed by appending a done marker (append-only log).
            agency.append(
                {
                    "kind": "self_prompt",
                    "prompt": item.get("prompt") or "",
                    "status": "consumed",
                    "reason": "evolve once",
                    "autonomy": item.get("autonomy"),
                    "meta": {"consumed_from_ts": item.get("ts")},
                }
            )
            return item
    return None


def evolve_once(
    *,
    settings: Settings | None = None,
    mission: str | None = None,
    agency: AgencyStore | None = None,
    ledger: Path | None = None,
) -> dict[str, Any]:
    """One self-evolution cycle: agency mission → Extreme council → ledger → follow-up."""
    settings = settings or Settings.load()
    agency = agency or default_agency_store()
    ledger = ledger or ledger_path()

    source = "cli"
    prompt = (mission or "").strip()
    if not prompt:
        queued = _pop_next_prompt(agency)
        if queued:
            prompt = (queued.get("prompt") or "").strip()
            source = "agency"
        else:
            prompt = "Mythos Extreme self-check: defense, knowledge gaps, watchdog drift"
            source = "default"

    result = run_extreme(prompt, settings=settings, enqueue_followup=True, include_watch=True)
    cycle = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ok": bool(result.get("ok")),
        "source": source,
        "mission": prompt,
        "synthesis_chars": len(result.get("report") or ""),
        "followup": (result.get("followup") or {}).get("prompt"),
        "bills_xai": False,
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(cycle, ensure_ascii=False) + "\n")
    return {"ok": cycle["ok"], "cycle": cycle, "extreme": result}


def evolution_status(*, ledger: Path | None = None, agency: AgencyStore | None = None) -> dict[str, Any]:
    ledger = ledger or ledger_path()
    agency = agency or default_agency_store()
    cycles = 0
    last = None
    if ledger.is_file():
        lines = [ln for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
        cycles = len(lines)
        if lines:
            try:
                last = json.loads(lines[-1])
            except json.JSONDecodeError:
                last = None
    queued = [i for i in list_agenda(store=agency) if i.get("status") == "queued"]
    return {
        "cycles": cycles,
        "last": last,
        "agency_queued": len(queued),
        "ledger": str(ledger),
        "note": "Local evolution loop — no remote trainer, no xAI.",
    }
