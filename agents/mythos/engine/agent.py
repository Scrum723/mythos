from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from .autonomy import gate
from .config import Settings
from .index import ensure_index
from .llm import LLMClient, LLMError
from .planner import heuristic_plan
from .prompt_build import build_system, language_for
from .security import redact
from .tools import ConfirmationRequired, ToolBox, tool_schemas

Confirmer = Callable[[str, dict[str, Any], str, str], bool]
Listener = Callable[[dict[str, Any]], None]

PARALLEL_OK = frozenset(
    {
        "list_dir",
        "read_file",
        "batch_read",
        "grep",
        "retrieve",
        "git_status",
        "detect_language",
        "read_improvements",
        "list_agents",
    }
)


@dataclass
class RunResult:
    ok: bool
    report: str
    plan: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)
    language: str = "unknown"
    used_llm: bool = False


def system_prompt(settings: Settings, extra: str | None = None, *, mode: str = "code") -> str:
    return build_system(settings, mode=mode, extra=extra)


def run_task(
    task: str,
    *,
    settings: Settings | None = None,
    extra_system: str | None = None,
    confirmer: Confirmer | None = None,
    listener: Listener | None = None,
    mode: str = "code",
) -> RunResult:
    settings = settings or Settings.load()
    events: list[dict[str, Any]] = []

    def emit(event: dict[str, Any]) -> None:
        events.append(event)
        if listener:
            listener(event)

    lang = language_for(settings.root)
    emit({"type": "language", "data": lang})
    if mode == "code":
        try:
            idx = ensure_index(settings.root, allow_secrets=settings.allow_secrets)
            emit({"type": "index", "data": idx})
        except OSError as exc:
            emit({"type": "index", "data": {"error": str(exc)}})

    box = ToolBox(settings, confirmer=confirmer)
    plan = heuristic_plan(task, settings.root, lang) if mode == "code" else {"task": task, "subgoals": [], "source": "chat"}
    emit({"type": "plan", "data": plan})

    client = LLMClient(settings)
    if not client.available:
        report = (
            client.missing_brain_message()
            + f"\nDetected language: {lang.get('primary')}\n"
            + "Heuristic plan:\n"
            + json.dumps(plan, indent=2)
        )
        emit({"type": "report", "data": {"ok": False, "report": report}})
        return RunResult(False, report, plan, events, lang.get("primary", "unknown"), False)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt(settings, extra_system, mode=mode)},
        {"role": "user", "content": task},
    ]
    tools = tool_schemas(mode=mode)
    final_text = ""
    max_steps = min(settings.max_steps, 8 if mode == "chat" else settings.max_steps)
    try:
        for step in range(max_steps):
            emit({"type": "step", "data": {"n": step + 1}})
            reply = client.chat(messages, tools)
            content = reply.get("content") or ""
            calls = reply.get("tool_calls") or []
            if content:
                emit({"type": "model", "data": {"text": content[:4000]}})
            if not calls:
                final_text = content
                break
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": content or None, "tool_calls": []}
            parsed_calls: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for call in calls:
                assistant_msg["tool_calls"].append(
                    {
                        "id": call["id"] or f"call_{step}",
                        "type": "function",
                        "function": {"name": call["name"], "arguments": call["arguments"]},
                    }
                )
                try:
                    args = json.loads(call["arguments"] or "{}")
                    if not isinstance(args, dict):
                        args = {}
                except json.JSONDecodeError:
                    args = {}
                parsed_calls.append((call, args))
            messages.append(assistant_msg)

            results = _run_calls(box, parsed_calls, emit)
            for call, output in results:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"] or f"call_{step}",
                        "content": output[:12_000],
                    }
                )
        else:
            final_text = "Stopped at max steps. Partial work may exist."
    except LLMError as exc:
        final_text = f"LLM error: {exc}"
        emit({"type": "error", "data": {"message": str(exc)}})
        return RunResult(False, final_text, plan, events, lang.get("primary", "unknown"), True)

    report = redact(final_text or "(empty model response)")
    emit({"type": "report", "data": {"ok": True, "report": report}})
    return RunResult(True, report, plan, events, lang.get("primary", "unknown"), True)


def _run_calls(
    box: ToolBox,
    parsed_calls: list[tuple[dict[str, Any], dict[str, Any]]],
    emit: Listener,
) -> list[tuple[dict[str, Any], str]]:
    if not parsed_calls:
        return []
    can_parallel = len(parsed_calls) > 1 and all(call["name"] in PARALLEL_OK for call, _ in parsed_calls)
    for call, args in parsed_calls:
        emit({"type": "tool", "data": {"name": call["name"], "args": _public_args(call["name"], args)}})

    def exec_one(call: dict[str, Any], args: dict[str, Any]) -> str:
        try:
            return box.execute(call["name"], args)
        except ConfirmationRequired as pending:
            return f"ERROR: blocked ({pending.risk}): {pending.reason}"

    outputs: list[str]
    if can_parallel:
        outputs = [""] * len(parsed_calls)
        with ThreadPoolExecutor(max_workers=min(6, len(parsed_calls))) as pool:
            futures = {pool.submit(exec_one, call, args): i for i, (call, args) in enumerate(parsed_calls)}
            for fut in as_completed(futures):
                outputs[futures[fut]] = fut.result()
    else:
        outputs = [exec_one(call, args) for call, args in parsed_calls]

    out: list[tuple[dict[str, Any], str]] = []
    for (call, _args), output in zip(parsed_calls, outputs):
        ok = not output.startswith("ERROR:")
        emit({"type": "tool_result", "data": {"name": call["name"], "ok": ok, "output": output[:4000]}})
        out.append((call, output))
    return out


def _public_args(name: str, args: dict[str, Any]) -> dict[str, Any]:
    public = dict(args)
    if name == "write_file" and "content" in public:
        content = str(public["content"])
        public["content"] = content[:200] + ("…" if len(content) > 200 else "")
        public["bytes"] = len(content)
    if "command" in public:
        decision = gate(3, "run_shell", str(public["command"]))
        public["risk"] = decision.risk
    return public
