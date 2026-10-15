from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from .config import Settings, local_reachable
from .security import redact

CHAT_PATH = "/chat/completions"
TEXT_TOOLS_RE = re.compile(r"\{[^{}]*\"(?:tool_calls|name)\"[^{}]*\}", re.DOTALL)


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def available(self) -> bool:
        if self.settings.uses_xai:
            return bool(self.settings.api_key)
        return local_reachable(self.settings.api_base)

    def missing_brain_message(self) -> str:
        if self.settings.uses_xai:
            return "CODING_PROVIDER=xai but XAI_API_KEY is empty. This agent defaults to a local model so you are not billed by xAI."
        return (
            "No local model is running. This agent does not use Grok.\n"
            "Install once, then it runs on your machine:\n"
            "  python3 agent.py setup\n"
            "or:\n"
            "  brew install ollama && ollama serve && ollama pull qwen2.5-coder:7b"
        )

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if self.settings.uses_xai:
            raise LLMError(
                "NO CHARGES: this agent will not call xAI. "
                "Keep CODING_PROVIDER=local. Local Ollama only."
            )
        if not self.available:
            raise LLMError(self.missing_brain_message())
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            data = self._post(payload)
        except LLMError as exc:
            if tools and "tool" in str(exc).lower():
                data = self._post({k: v for k, v in payload.items() if k not in {"tools", "tool_choice"}})
            else:
                raise
        result = _normalize(data)
        if not result["tool_calls"] and result.get("content"):
            parsed = _parse_text_tools(result["content"])
            if parsed:
                result["tool_calls"] = parsed
        return result

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        url = self.settings.api_base.rstrip("/") + CHAT_PATH
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "coding-agent/0.1",
        }
        if self.settings.uses_xai:
            if not self.settings.api_key:
                raise LLMError("XAI_API_KEY missing while CODING_PROVIDER=xai")
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
        who = "xAI" if self.settings.uses_xai else "local Ollama"
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMError(f"{who} HTTP {exc.code}: {redact(detail)[:800]}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"{who} network error: {exc.reason}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(f"{who} returned non-JSON") from exc


def _parse_text_tools(content: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
    calls = data.get("tool_calls") if isinstance(data, dict) else None
    if isinstance(data, dict) and not calls and data.get("name"):
        calls = [data]
    if not isinstance(calls, list):
        return []
    out = []
    for i, call in enumerate(calls):
        if not isinstance(call, dict):
            continue
        fn = call.get("function") if isinstance(call.get("function"), dict) else call
        args = fn.get("arguments") or call.get("arguments") or {}
        if isinstance(args, dict):
            args = json.dumps(args)
        out.append({"id": call.get("id") or f"call_{i}", "name": fn.get("name") or "", "arguments": args or "{}"})
    return out


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []
        parsed = []
        for call in tool_calls:
            fn = call.get("function") or {}
            parsed.append(
                {
                    "id": call.get("id") or "",
                    "name": fn.get("name") or call.get("name") or "",
                    "arguments": fn.get("arguments") or call.get("arguments") or "{}",
                }
            )
        if not parsed and message.get("function_call"):
            fc = message["function_call"]
            parsed.append({"id": "call_0", "name": fc.get("name") or "", "arguments": fc.get("arguments") or "{}"})
        return {
            "content": message.get("content") or "",
            "tool_calls": parsed,
            "finish_reason": choices[0].get("finish_reason"),
        }
    return {"content": "", "tool_calls": [], "finish_reason": data.get("finish_reason")}
