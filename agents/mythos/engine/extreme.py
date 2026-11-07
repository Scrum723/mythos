from __future__ import annotations

from typing import Any

from . import improve
from .agency import self_prompt
from .brain_status import brain_status
from .config import Settings
from .council import run_council
from .watchdog import watch_once, watch_status


def run_extreme(
    mission: str,
    *,
    settings: Settings | None = None,
    enqueue_followup: bool = True,
    include_watch: bool = True,
) -> dict[str, Any]:
    """Mythos Extreme: council swarm (+ optional watchdog) for one mission."""
    settings = settings or Settings.load()
    watch = None
    if include_watch:
        try:
            watch = watch_once(settings=settings)
        except Exception as exc:  # noqa: BLE001
            watch = {"error": str(exc)}
    council = run_council(mission, settings=settings)
    report = council.get("synthesis") or ""
    if watch and not watch.get("error"):
        changes = ((watch.get("diff_from_previous") or {}).get("changes")) or []
        report = (
            report
            + "\n\n## Watchdog\n"
            + f"loopback_llm={watch.get('network', {}).get('loopback_llm')} "
            + f"hostname={watch.get('device', {}).get('hostname')} "
            + f"devices={len(watch.get('devices') or [])}\n"
        )
        if changes:
            report += "Recent changes:\n- " + "\n- ".join(changes[:12]) + "\n"

    try:
        improve.append(
            {
                "area": "extreme",
                "note": f"Extreme council on: {mission[:120]}",
                "task": mission,
            }
        )
    except Exception:
        pass

    follow = None
    if enqueue_followup:
        follow = self_prompt(
            f"Continue Extreme evolution on: {mission[:160]}",
            autonomy=settings.autonomy,
        )

    return {
        "ok": bool(council.get("ok")),
        "mission": mission,
        "council": council,
        "watch": watch,
        "report": report,
        "followup": follow,
        "bills_xai": False,
        "model_required": False,
    }


def extreme_status(*, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.load()
    status = brain_status(settings)
    return {
        "service": "mythos-extreme",
        "layer": "council+evolution+watchdog",
        "standalone_ready": status.get("standalone_ready"),
        "model_required": False,
        "runner": status.get("runner"),
        "has_llm": settings.has_llm,
        "watch": watch_status(),
        "bills_xai": False,
        "note": (
            "Mythos Extreme is a local multi-agent swarm with self-evolution and device/network "
            "watchdog. Not cloud AGI; no xAI."
        ),
    }
