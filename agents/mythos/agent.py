#!/usr/bin/env python3
"""Standalone agent: mythos

Role: Senior local coding agent combining Grok Build, Astra, and GPT-style strengths. Ships working code, not suggestions.

Copy this folder anywhere. It includes its own runtime, CLI, and web desk.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from engine.cli import main as _cli_main

COMMANDS = {
    "run",
    "chat",
    "serve",
    "spawn",
    "agents",
    "improvements",
    "detect",
    "health",
    "improve",
    "guide",
    "setup",
    "brains",
    "bench",
}


def _normalize(argv: list[str]) -> list[str]:
    if not argv:
        return ["health"]
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in {"-a", "--autonomy", "-r", "--root", "--host", "--port"}:
            i += 2
            continue
        if tok in {"--allow-secrets"}:
            i += 1
            continue
        if tok.startswith("-"):
            i += 1
            continue
        break
    if i >= len(argv):
        return argv + ["health"]
    if argv[i] not in COMMANDS:
        return argv[:i] + ["run"] + argv[i:]
    return argv


def main(argv: list[str] | None = None) -> int:
    raw = list(argv) if argv is not None else sys.argv[1:]
    return _cli_main(_normalize(raw))


if __name__ == "__main__":
    raise SystemExit(main())
