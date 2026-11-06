from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .network_policy import airgap_enabled, is_loopback_url


def local_threat_posture() -> dict[str, Any]:
    """Local exterior-threat posture for Mythos (no remote SOC dependency)."""
    return {
        "local_only": True,
        "allows_remote_llm": False,
        "airgap_default": False,
        "airgap_env": ["MYTHOS_AIRGAP", "CODING_AIRGAP"],
        "controls": [
            "LLM HTTP bases must be loopback (127.0.0.1 / localhost / ::1)",
            "NO CHARGES: api.x.ai and XAI_API_KEY are refused",
            "Project-root path sandbox; symlink escape blocked",
            "Secret-like files blocked unless --allow-secrets",
            "Secret values redacted in tool/LLM output",
            "Airgap mode refuses remote model pulls",
            "Optional GGUF in-process path avoids non-local runners",
            "Exterior risk scan flags non-loopback LLM bases and airgap violations",
        ],
        "mission": (
            "Protect the owner locally from exterior network threats to the agent "
            "(exfiltration, remote LLM billing, path escape, secret leakage)."
        ),
    }


def scan_exterior_risks(
    *,
    api_base: str | None = None,
    airgap: bool | None = None,
) -> list[dict[str, Any]]:
    """Return local risk findings. Does not contact remote hosts."""
    risks: list[dict[str, Any]] = []
    gap = airgap_enabled() if airgap is None else bool(airgap)
    if api_base:
        if not is_loopback_url(api_base):
            host = urlparse(api_base).hostname or api_base
            risks.append(
                {
                    "id": "remote_llm_base",
                    "severity": "critical",
                    "title": "Non-loopback LLM base",
                    "detail": f"api_base host {host!r} is outside loopback — exterior threat surface.",
                }
            )
        if "api.x.ai" in api_base.lower():
            risks.append(
                {
                    "id": "xai_endpoint",
                    "severity": "critical",
                    "title": "xAI endpoint configured",
                    "detail": "NO CHARGES policy forbids api.x.ai.",
                }
            )
    if gap and api_base and not is_loopback_url(api_base):
        risks.append(
            {
                "id": "airgap_violation",
                "severity": "high",
                "title": "Airgap with remote base",
                "detail": "Airgap is on but LLM base is not loopback.",
            }
        )
    if not risks:
        risks.append(
            {
                "id": "clear",
                "severity": "info",
                "title": "No exterior LLM risks detected in provided settings",
                "detail": "Continue refusing non-loopback inference hosts.",
            }
        )
    return risks
