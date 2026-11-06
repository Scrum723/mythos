from __future__ import annotations

from pathlib import Path
from typing import Any

from .brain_status import resolve_gguf


def llama_cpp_available() -> bool:
    try:
        import llama_cpp  # noqa: F401

        return True
    except Exception:
        return False


def gguf_chat(
    messages: list[dict[str, Any]],
    *,
    model_path: Path,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """In-process chat against a local GGUF via optional llama_cpp. No remote hosts."""
    if not llama_cpp_available():
        raise RuntimeError("llama_cpp is not installed")
    from llama_cpp import Llama

    path = Path(model_path)
    if not path.is_file():
        raise RuntimeError(f"GGUF missing: {path}")
    llm = Llama(model_path=str(path), n_ctx=4096, verbose=False)
    # Strip tool schemas — many GGUF builds lack native tool calling; text parse handles JSON tools.
    clean = []
    for msg in messages:
        role = msg.get("role") or "user"
        content = msg.get("content")
        if content is None:
            continue
        if role == "tool":
            clean.append({"role": "user", "content": f"Tool result: {content}"})
        else:
            clean.append({"role": role, "content": str(content)})
    out = llm.create_chat_completion(messages=clean)
    choice = (out.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return {
        "content": message.get("content") or "",
        "tool_calls": [],
        "finish_reason": choice.get("finish_reason"),
    }


def can_run_gguf(settings=None) -> bool:
    if not llama_cpp_available():
        return False
    return resolve_gguf(settings) is not None
