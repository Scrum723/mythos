from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import coach, improve
from .agent import run_task
from .config import Settings
from .constitution import identity
from .languages import detect
from .spawn import list_agents, spawn


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mythos",
        description="Mythos — standalone local general-purpose intelligence (coding, generative, creative). NO CHARGES.",
    )
    parser.add_argument("-a", "--autonomy", type=int, choices=range(1, 6), help="1-5, default 3")
    parser.add_argument("-r", "--root", help="Project root the agent may touch")
    parser.add_argument("--allow-secrets", action="store_true", help="Allow reading secret-like files")
    sub = parser.add_subparsers(dest="cmd", required=False)

    run_p = sub.add_parser("run", help="Run one coding (or --mode) task")
    run_p.add_argument("task", help="What to do")
    run_p.add_argument(
        "--mode",
        choices=["code", "create", "chat", "generative", "creative"],
        default="code",
        help="code | create (generative/creative) | chat",
    )

    create_p = sub.add_parser("create", help="Generative / creative task (no forced code-explore)")
    create_p.add_argument("task", help="What to create")

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
    sub.add_parser("educate", help="Offline teaching report (no remote fetches)")
    sub.add_parser("knowledge", help="Local knowledge library (coding + spoken + defense + neural)")
    neural_p = sub.add_parser("neural", help="Mythos neural pattern graph (ingested open-source)")
    neural_sub = neural_p.add_subparsers(dest="neural_cmd", required=True)
    neural_sub.add_parser("status", help="Neural graph snapshot")
    neural_sub.add_parser("train", help="Local train step: log + enqueue Extreme apply")
    agency_p = sub.add_parser("agency", help="Local free-will agency (self-prompt / defer / list)")
    agency_sub = agency_p.add_subparsers(dest="agency_cmd", required=True)
    sp = agency_sub.add_parser("self-prompt", help="Queue a self-directed follow-up")
    sp.add_argument("prompt", help="What Mythos should pursue next")
    df = agency_sub.add_parser("defer", help="Defer a wake reminder locally")
    df.add_argument("--seconds", type=int, default=60)
    df.add_argument("--reason", default="")
    ig = agency_sub.add_parser("ignore", help="Record a conscious ignore-note")
    ig.add_argument("note", help="Why this was set aside")
    agency_sub.add_parser("list", help="List agenda items")
    agency_sub.add_parser("status", help="Agency snapshot")

    extreme_p = sub.add_parser("extreme", help="Mythos Extreme council swarm (+ watchdog)")
    extreme_p.add_argument("mission", help="Mission for the local multi-agent council")
    council_p = sub.add_parser("council", help="Run Extreme council only")
    council_p.add_argument("mission", help="Council mission")
    evolve_p = sub.add_parser("evolve", help="Self-evolution loop")
    evolve_sub = evolve_p.add_subparsers(dest="evolve_cmd", required=True)
    evolve_once_p = evolve_sub.add_parser("once", help="Run one evolution cycle")
    evolve_once_p.add_argument("--mission", default=None, help="Override agency queue")
    evolve_sub.add_parser("status", help="Evolution ledger status")
    watch_p = sub.add_parser("watch", help="Network/device/devices watchdog over time")
    watch_sub = watch_p.add_subparsers(dest="watch_cmd", required=True)
    watch_sub.add_parser("once", help="Take one local snapshot")
    watch_sub.add_parser("status", help="Watchdog history summary")
    watch_sub.add_parser("history", help="Show recent snapshots")

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
    if args.cmd == "educate":
        from .educate import educate_report

        print(json.dumps(educate_report(settings), indent=2))
        return 0
    if args.cmd == "knowledge":
        from .defense import scan_exterior_risks
        from .knowledge import knowledge_snapshot

        snap = knowledge_snapshot()
        snap["exterior_risks"] = scan_exterior_risks(
            api_base=settings.api_base,
            airgap=bool(getattr(settings, "airgap", False)),
        )
        print(json.dumps(snap, indent=2))
        return 0
    if args.cmd == "neural":
        from .neural import neural_snapshot, train_from_neural

        cmd = getattr(args, "neural_cmd", None)
        if cmd == "status":
            print(json.dumps(neural_snapshot(), indent=2))
            return 0
        if cmd == "train":
            print(json.dumps(train_from_neural(), indent=2))
            return 0
        print("usage: neural status|train", file=sys.stderr)
        return 2
    if args.cmd == "agency":
        return _agency(args, settings)
    if args.cmd == "extreme":
        from .extreme import run_extreme

        out = run_extreme(args.mission, settings=settings)
        print(out.get("report") or json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1
    if args.cmd == "council":
        from .council import run_council

        out = run_council(args.mission, settings=settings)
        print(out.get("synthesis") or json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1
    if args.cmd == "evolve":
        return _evolve(args, settings)
    if args.cmd == "watch":
        return _watch(args, settings)
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
        return _run(args.task, settings, mode=getattr(args, "mode", "code"))
    if args.cmd == "create":
        return _run(args.task, settings, mode="create")
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
        from .brain_status import brain_status

        ident = identity()
        status = brain_status(settings)
        print(
            json.dumps(
                {
                    "service": ident.get("name") or "mythos",
                    "role": ident.get("role") or "",
                    "modes": ident.get("modes") or ["code", "create", "chat"],
                    "objective": ident.get("objective") or ["coding", "generative", "creative"],
                    "root": str(settings.root),
                    "autonomy": settings.autonomy,
                    "provider": settings.provider,
                    "model": settings.model,
                    "has_llm": settings.has_llm,
                    "bills_xai": settings.uses_xai,
                    "host": settings.host,
                    "port": settings.port,
                    "offline_ready": status.get("offline_ready"),
                    "standalone_ready": status.get("standalone_ready"),
                    "model_required": status.get("model_required", False),
                    "model_optional": status.get("model_optional", True),
                    "gguf_present": status.get("gguf_present"),
                    "gguf_path": status.get("gguf_path"),
                    "runner": status.get("runner"),
                    "airgap": status.get("airgap"),
                    "network_mode": status.get("network_mode"),
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
                "Mythos is a standalone local general-purpose intelligence.",
                "Modes: code (implement), create (generative/creative), chat (talk).",
                "Default brain is a local model, not Grok.",
                f"Provider: {settings.provider}  brain: {brain}",
                f"Standalone (no model required): yes",
                f"Optional local model: {'yes' if settings.has_llm else 'not running — Mythos still works'}",
                "",
                "  python3 agent.py setup",
                "  python3 agent.py serve --port 8790",
                "  python3 agent.py improve",
                '  python3 agent.py -r ~/some-real-dir run "add tests"',
                '  python3 agent.py create "write a short myth about rivers"',
                '  python3 agent.py run --mode create "invent three product names"',
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
    # Model is optional — standalone engine can still apply an improve task.
    settings.root = path
    return _run(coach.improve_task(path, apply=True), settings)


def _evolve(args: Any, settings: Settings) -> int:
    from .evolution import evolve_once, evolution_status

    cmd = getattr(args, "evolve_cmd", None)
    if cmd == "once":
        out = evolve_once(settings=settings, mission=getattr(args, "mission", None))
        print(json.dumps({"ok": out.get("ok"), "cycle": out.get("cycle")}, indent=2))
        print("\n" + (out.get("extreme") or {}).get("report", ""))
        return 0 if out.get("ok") else 1
    if cmd == "status":
        print(json.dumps(evolution_status(), indent=2))
        return 0
    print("usage: evolve once|status", file=sys.stderr)
    return 2


def _watch(args: Any, settings: Settings) -> int:
    from .watchdog import snapshot_path, watch_once, watch_status

    cmd = getattr(args, "watch_cmd", None)
    if cmd == "once":
        print(json.dumps(watch_once(settings=settings), indent=2))
        return 0
    if cmd == "status":
        print(json.dumps(watch_status(), indent=2))
        return 0
    if cmd == "history":
        path = snapshot_path()
        rows = []
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines()[-10:]:
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        print(json.dumps({"count": len(rows), "items": rows}, indent=2))
        return 0
    print("usage: watch once|status|history", file=sys.stderr)
    return 2


def _agency(args: Any, settings: Settings) -> int:
    from .agency import (
        agency_snapshot,
        defer_self,
        ignore_with_note,
        list_agenda,
        self_prompt,
    )

    cmd = getattr(args, "agency_cmd", None)
    if cmd == "self-prompt":
        print(json.dumps(self_prompt(args.prompt, autonomy=settings.autonomy), indent=2))
        return 0
    if cmd == "defer":
        print(json.dumps(defer_self(seconds=args.seconds, reason=args.reason), indent=2))
        return 0
    if cmd == "ignore":
        print(json.dumps(ignore_with_note(args.note), indent=2))
        return 0
    if cmd == "list":
        items = list_agenda()
        print(json.dumps({"count": len(items), "items": items}, indent=2))
        return 0
    if cmd == "status":
        print(json.dumps(agency_snapshot(), indent=2))
        return 0
    print("usage: agency self-prompt|defer|ignore|list|status", file=sys.stderr)
    return 2


def _run(task: str, settings: Settings, *, mode: str = "code") -> int:
    result = run_task(task, settings=settings, confirmer=_confirmer, mode=mode)
    print(result.report)
    return 0 if result.ok else 1


def _chat(settings: Settings) -> int:
    print(f"mythos  local  no-charges  autonomy={settings.autonomy}")
    print(f"workspace: {settings.root}")
    print("Standalone local intelligence (coding + generative + creative). /help  /quit")
    if not settings.has_llm:
        print("Optional local model not running — standalone engine is active (no model required).")
    chat_mode = "chat"
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
            print("  /mode code|create|chat   switch REPL mode (default chat)")
            print("  /create PROMPT           one-shot generative/creative turn")
            print("  /root PATH               work in that project")
            print("  /prefer NOTE             save a lasting preference")
            print("  /autonomy 1-5            3 is default")
            print("  /improve PATH            scan another agent folder")
            print("  /bench                   speed report vs old prompts")
            print("  /quit")
            continue
        if line.startswith("/mode"):
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                print("usage: /mode code|create|chat")
                continue
            from .prompt_build import normalize_mode

            chat_mode = normalize_mode(parts[1])
            print(f"mode={chat_mode}")
            continue
        if line.startswith("/create"):
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                print("usage: /create write a short myth about …")
                continue
            result = run_task(parts[1], settings=settings, confirmer=_confirmer, mode="create")
            print(result.report)
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
        result = run_task(line, settings=settings, confirmer=_confirmer, mode=chat_mode)
        print(result.report)
    return 0
