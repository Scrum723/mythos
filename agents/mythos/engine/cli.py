from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import coach, improve
from .agent import run_task
from .config import Settings
from .constitution import identity
from .languages import detect
from .spawn import list_agents, spawn


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="coding",
        description="Coding agent — separate local coding agent that can also improve other agents.",
    )
    parser.add_argument("-a", "--autonomy", type=int, choices=range(1, 6), help="1-5, default 3")
    parser.add_argument("-r", "--root", help="Project root the agent may touch")
    parser.add_argument("--allow-secrets", action="store_true", help="Allow reading secret-like files")
    sub = parser.add_subparsers(dest="cmd", required=False)

    run_p = sub.add_parser("run", help="Run one task")
    run_p.add_argument("task", help="What to do")

    sub.add_parser("chat", help="Interactive REPL")

    serve_p = sub.add_parser("serve", help="Web desk")
    serve_p.add_argument("--host", default=None)
    serve_p.add_argument("--port", type=int, default=None)

    spawn_p = sub.add_parser("spawn", help="Write a standalone sub-agent")
    spawn_p.add_argument("--name", required=True)
    spawn_p.add_argument("--role", required=True)
    spawn_p.add_argument("--prompt", required=True)
    spawn_p.add_argument("--tools", default="list_dir,read_file,write_file,grep,run_shell,run_tests")
    spawn_p.add_argument("--constraints", default="Stay in project root. No secrets. Honesty first.")
    spawn_p.add_argument("--dest", default=None, help="Directory for the standalone agent")

    sub.add_parser("agents", help="List spawned agents")
    sub.add_parser("improvements", help="Show improvement log")
    sub.add_parser("detect", help="Detect project language")
    sub.add_parser("health", help="Print config without secrets")

    improve_p = sub.add_parser("improve", help="Review or improve another agent (or this one)")
    improve_p.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Real folder on disk (not /path/to/other-agent). Default: this agent",
    )
    improve_p.add_argument("--apply", action="store_true", help="Apply safe fixes in the target")
    sub.add_parser("guide", help="How this agent works")
    sub.add_parser("setup", help="Fetch missing local brains from Hugging Face git (no xAI)")
    sub.add_parser("brains", help="List local brains vs git sources")
    sub.add_parser("bench", help="Benchmark prompt size, index, and read speed")

    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        settings = Settings.load(
            root=args.root,
            autonomy=args.autonomy,
            allow_secrets=args.allow_secrets,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not args.cmd:
        return _guide(settings)
    if args.cmd == "guide":
        return _guide(settings)
    if args.cmd == "setup":
        from .setup_local import setup

        return setup(settings)
    if args.cmd == "brains":
        from .setup_local import BRAINS, ollama_names

        have = ollama_names(settings.api_base)
        rows = []
        for name, spec in BRAINS.items():
            rows.append(
                {
                    "name": name,
                    "present": any(n == spec["ollama"] or n.startswith(spec["ollama"]) for n in have),
                    "git": spec["git"],
                    "file": spec["file"],
                }
            )
        print(json.dumps({"installed": have, "catalog": rows, "bills_xai": settings.uses_xai}, indent=2))
        return 0
    if args.cmd == "bench":
        from .benchmark import report

        print(json.dumps(report(settings), indent=2))
        return 0
    if args.cmd == "run":
        return _run(args.task, settings)
    if args.cmd == "chat":
        return _chat(settings)
    if args.cmd == "serve":
        from .web import serve

        host = args.host or settings.host
        port = args.port or settings.port
        serve(settings, host=host, port=port)
        return 0
    if args.cmd == "spawn":
        result = spawn(
            name=args.name,
            role=args.role,
            prompt=args.prompt,
            tools=args.tools,
            constraints=args.constraints,
            dest=args.dest,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.cmd == "agents":
        print(json.dumps(list_agents(), indent=2))
        return 0
    if args.cmd == "improvements":
        print(json.dumps(improve.read_all(), indent=2))
        return 0
    if args.cmd == "detect":
        print(json.dumps(detect(settings.root), indent=2))
        return 0
    if args.cmd == "improve":
        return _improve(args.target, settings, apply=args.apply)
    if args.cmd == "health":
        print(
            json.dumps(
                {
                    "service": identity().get("name") or "coding",
                    "role": identity().get("role") or "",
                    "root": str(settings.root),
                    "autonomy": settings.autonomy,
                    "provider": settings.provider,
                    "model": settings.model,
                    "has_llm": settings.has_llm,
                    "bills_xai": settings.uses_xai,
                    "host": settings.host,
                    "port": settings.port,
                },
                indent=2,
            )
        )
        return 0
    parser.error("unknown command")
    return 2


def _confirmer(tool: str, args: dict, reason: str, risk: str) -> bool:
    if not sys.stdin.isatty():
        print(f"blocked ({risk}): {reason} [non-interactive]", file=sys.stderr)
        return False
    print(f"\n[{risk}] {reason}")
    print(f"  {tool} {json.dumps(args, default=str)[:500]}")
    try:
        ans = input("Approve? [y/N] ").strip().lower()
    except EOFError:
        return False
    return ans in {"y", "yes"}


def _guide(settings: Settings) -> int:
    here = Path(__file__).resolve().parents[1]
    brain = (
        "xAI Grok (you will be billed by xAI)"
        if settings.uses_xai
        else f"local Ollama ({settings.model}) — no xAI charges"
    )
    print(
        "\n".join(
            [
                "Coding agent is a separate entity. Default brain is a local model, not Grok.",
                f"Provider: {settings.provider}  brain: {brain}",
                f"Local model ready: {'yes' if settings.has_llm else 'NO — run python3 agent.py setup'}",
                "",
                "  python3 agent.py setup",
                "  python3 agent.py serve --port 8790",
                "  python3 agent.py improve",
                '  python3 agent.py -r ~/some-real-dir run "add tests"',
                "",
                f"This folder: {here}",
                "NO CHARGES: xAI billing is disabled. Local Ollama only.",
            ]
        )
    )
    return 0


def _improve(target: str | None, settings: Settings, *, apply: bool) -> int:
    raw = target or str(Path(__file__).resolve().parents[1])
    if not target:
        print("No path given — scanning this agent.\n", file=sys.stderr)
    try:
        path = coach.resolve_target(raw)
    except coach.TargetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = coach.scan(path)
    print(json.dumps(report, indent=2))
    if not apply:
        return 0 if report["fails"] == 0 else 1
    if not settings.has_llm:
        from .llm import LLMClient

        print(LLMClient(settings).missing_brain_message(), file=sys.stderr)
        return 1
    settings.root = path
    return _run(coach.improve_task(path, apply=True), settings)


def _run(task: str, settings: Settings) -> int:
    result = run_task(task, settings=settings, confirmer=_confirmer)
    print(result.report)
    return 0 if result.ok else 1


def _chat(settings: Settings) -> int:
    print(f"mythos  local  no-charges  autonomy={settings.autonomy}")
    print(f"workspace: {settings.root}")
    print("Talk like you would to Grok. /help  /quit  /root PATH  /prefer NOTE  /bench")
    if not settings.has_llm:
        print("Local model is not running. python3 agent.py setup")
    while True:
        try:
            line = input("mythos> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in {"/quit", "/exit"}:
            return 0
        if line in {"/help", "/?"}:
            print("  type a task and press enter")
            print("  /root PATH     work in that project")
            print("  /prefer NOTE   save a lasting preference")
            print("  /autonomy 1-5  3 is default")
            print("  /improve PATH  scan another agent folder")
            print("  /bench         speed report vs old prompts")
            print("  /quit")
            continue
        if line.startswith("/prefer"):
            from . import prefs

            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                print("usage: /prefer short answers, Python first")
                continue
            print(prefs.append(parts[1]))
            continue
        if line in {"/bench", "/benchmark"}:
            from .benchmark import report

            print(json.dumps(report(settings), indent=2))
            continue
        if line.startswith("/root"):
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                print("usage: /root /Users/you/some-project")
                continue
            path = Path(parts[1]).expanduser().resolve()
            if not path.is_dir():
                print(f"not a directory: {path}")
                continue
            settings.root = path
            print(f"workspace: {settings.root}")
            continue
        if line.startswith("/autonomy"):
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                level = int(parts[1])
                if 1 <= level <= 5:
                    settings.autonomy = level
                    print(f"autonomy={level}")
                    continue
            print("usage: /autonomy 1-5")
            continue
        if line.startswith("/improve"):
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                print("usage: /improve /path/to/other-agent")
                continue
            _improve(parts[1], settings, apply=False)
            continue
        result = run_task(line, settings=settings, confirmer=_confirmer, mode="chat")
        print(result.report)
    return 0
