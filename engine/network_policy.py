from __future__ import annotations

import os
from urllib.parse import urlparse


def airgap_enabled() -> bool:
    for key in ("MYTHOS_AIRGAP", "CODING_AIRGAP"):
        raw = (os.environ.get(key) or "").strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
    return False


def is_loopback_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False
    return host in {"127.0.0.1", "localhost", "::1"}


def assert_local_llm_base(api_base: str) -> None:
    """Refuse non-loopback LLM HTTP bases — Mythos stays on this machine."""
    if is_loopback_url(api_base):
        return
    raise ValueError(
        f"LLM base not allowed (local-only / loopback required): {api_base!r}. "
        "Use http://127.0.0.1:11434/v1 or enable an on-disk GGUF backend."
    )
