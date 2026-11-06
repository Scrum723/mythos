from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings, local_reachable
from .setup_local import BRAINS, models_dir


def llama_cpp_available() -> bool:
    try:
        import llama_cpp  # noqa: F401

        return True
    except Exception:
        return False


def resolve_gguf(settings: Settings | None = None) -> Path | None:
    model_name = (settings.model if settings else None) or ""
    spec = BRAINS.get(model_name) or BRAINS.get("qwen2.5-coder:7b")
    if not spec:
        return None
    path = models_dir() / spec["file"]
    if path.is_file() and path.stat().st_size > 1_000_000:
        return path
    # Any large GGUF in models/ counts as an owned brain on disk.
    root = models_dir()
    if root.is_dir():
        for candidate in sorted(root.glob("*.gguf")):
            if candidate.is_file() and candidate.stat().st_size > 1_000_000:
                return candidate
    return None


def brain_status(settings: Settings) -> dict[str, Any]:
    gguf = resolve_gguf(settings)
    ollama_up = local_reachable(settings.api_base)
    llama = llama_cpp_available() and gguf is not None
    if ollama_up:
        runner = "ollama"
    elif llama:
        runner = "llama_cpp"
    else:
        runner = "none"
    offline_ready = runner in {"ollama", "llama_cpp"} and (
        ollama_up or (gguf is not None and llama_cpp_available())
    )
    airgap = bool(getattr(settings, "airgap", False))
    network_mode = getattr(settings, "network_mode", None) or ("airgap" if airgap else "local")
    return {
        "gguf_present": gguf is not None,
        "gguf_path": str(gguf) if gguf else None,
        "runner": runner,
        "offline_ready": bool(offline_ready),
        "airgap": airgap,
        "network_mode": network_mode,
        "model": settings.model,
        "provider": settings.provider,
        "bills_xai": False,
    }
