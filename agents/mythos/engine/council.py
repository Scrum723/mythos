from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .agent import run_task
from .config import Settings
from .defense import local_threat_posture, scan_exterior_risks
from .knowledge import knowledge_snapshot

SEATS: list[dict[str, Any]] = [
    {
        "id": "coder",
        "role": "Implement and explore with project tools. Prefer small diffs and verification.",
        "mode": "code",
    },
    {
        "id": "creator",
        "role": "Generative/creative angle — vivid options without forced code-explore.",
        "mode": "create",
    },
    {
        "id": "defender",
        "role": "Local defense: airgap, loopback LLM, secrets, exterior risks, watchdog posture.",
        "mode": "chat",
    },
    {
        "id": "critic",
        "role": "Attack the plan. List failure modes, missing tests, and overclaims.",
        "mode": "chat",
    },
    {
        "id": "synthesizer",
        "role": "Merge prior seats into one actionable verdict for the owner.",
        "mode": "chat",
    },
]


def run_council(mission: str, *, settings: Settings, max_workers: int = 4) -> dict[str, Any]:
    """Local multi-agent deliberation. Uses Ollama when present; standalone otherwise."""
    mission = (mission or "").strip() or "report Mythos status"
    seats_out: list[dict[str, Any]] = []

    # Defender gets structured local facts injected (no remote calls).
    posture = local_threat_posture()
    risks = scan_exterior_risks(api_base=settings.api_base, airgap=bool(getattr(settings, "airgap", False)))
    knowledge = knowledge_snapshot()
    defender_extra = (
        f"Mission: {mission}\n"
        f"Threat posture: {posture}\n"
        f"Exterior risks: {risks}\n"
        f"Knowledge coding langs: {knowledge['coding']['count']}; spoken: {knowledge['spoken']['count']}\n"
        "Respond with concrete local defenses and gaps."
    )

    def run_seat(seat: dict[str, Any]) -> dict[str, Any]:
        sid = seat["id"]
        if sid == "synthesizer":
            return {"id": sid, "role": seat["role"], "report": "", "ok": True, "deferred": True}
        prompt = f"You are the Mythos Extreme council seat '{sid}'. {seat['role']}\nMission: {mission}"
        if sid == "defender":
            prompt = defender_extra
        elif sid == "critic":
            prompt = (
                f"You are the critic seat. Mission: {mission}\n"
                "List top failure modes, security gaps, and what a peer standalone agent would check "
                "(network, this device, devices over time). Be harsh and specific."
            )
        try:
            result = run_task(prompt, settings=settings, mode=seat["mode"])
            return {
                "id": sid,
                "role": seat["role"],
                "ok": bool(result.ok),
                "used_llm": bool(result.used_llm),
                "report": result.report,
            }
        except Exception as exc:  # noqa: BLE001 — seat isolation
            return {
                "id": sid,
                "role": seat["role"],
                "ok": False,
                "used_llm": False,
                "report": f"Seat error (isolated): {exc}",
            }

    workers = [s for s in SEATS if s["id"] != "synthesizer"]
    # Local Ollama on modest RAM: prefer sequential seats to avoid parallel inference crashes.
    use_parallel = max_workers > 1 and not settings.has_llm
    if use_parallel:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(workers))) as pool:
            futures = {pool.submit(run_seat, seat): seat["id"] for seat in workers}
            for fut in as_completed(futures):
                seats_out.append(fut.result())
    else:
        for seat in workers:
            seats_out.append(run_seat(seat))

    # Stable order
    order = {s["id"]: i for i, s in enumerate(SEATS)}
    seats_out.sort(key=lambda r: order.get(r["id"], 99))

    synthesis = _synthesize(mission, seats_out, settings)
    seats_out.append(
        {
            "id": "synthesizer",
            "role": next(s["role"] for s in SEATS if s["id"] == "synthesizer"),
            "ok": True,
            "used_llm": False,
            "report": synthesis,
        }
    )
    return {
        "ok": True,
        "mission": mission,
        "seats": seats_out,
        "synthesis": synthesis,
        "bills_xai": False,
        "model_required": False,
    }


def _synthesize(mission: str, seats: list[dict[str, Any]], settings: Settings) -> str:
    chunks = [f"# Mythos Extreme Council\nMission: {mission}\n"]
    for seat in seats:
        body = (seat.get("report") or "").strip()
        if len(body) > 1200:
            body = body[:1200] + "…"
        chunks.append(f"## {seat['id']}\n{body}\n")
    chunks.append(
        "## Verdict\n"
        "Combine the seats above into local action: keep NO CHARGES, prefer loopback inference, "
        "use agency/evolve for follow-ups, and run watchdog watches for network/device drift. "
        f"Workspace: {settings.root}"
    )
    # Prefer LLM synthesizer when available for richer merge; else deterministic merge.
    try:
        from .llm import LLMClient

        client = LLMClient(settings)
        if client.available:
            prompt = (
                "Synthesize this Mythos Extreme council into a short actionable verdict "
                "(bullets: do-now, risks, next self-prompt).\n\n" + "\n\n".join(chunks)
            )
            result = run_task(prompt, settings=settings, mode="chat")
            if result.ok and result.report.strip():
                return result.report.strip()
    except Exception:
        pass
    return "\n".join(chunks)
