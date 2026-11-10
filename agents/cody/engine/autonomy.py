from __future__ import annotations

import re
from dataclasses import dataclass

SAFE_TOOLS = frozenset(
    {
        "list_dir",
        "read_file",
        "batch_read",
        "grep",
        "retrieve",
        "index_repo",
        "git_status",
        "detect_language",
        "plan_task",
        "run_tests",
        "list_agents",
        "read_improvements",
    }
)
WRITE_TOOLS = frozenset(
    {
        "write_file",
        "spawn_agent",
        "log_improvement",
        "remember_preference",
        "run_shell",
    }
)

DESTRUCTIVE_RE = re.compile(
    r"""
    (
        \brm\b
        | \brmdir\b
        | \bunlink\b
        | \bdel\b
        | \bshred\b
        | git\s+reset
        | git\s+checkout\s+--
        | git\s+clean
        | git\s+push\b[^\n]*--force
        | git\s+push\b[^\n]*\s-f\b
        | drop\s+(table|database|schema)
        | truncate\s+table
        | mkfs
        | format\s+
        | diskutil\s+erase
        | dd\s+if=
        | chmod\s+-R\s+777
        | chown\s+-R
        | kill\s+-9
        | pkill
        | shutdown
        | reboot
        | docker\s+system\s+prune
        | kubectl\s+delete
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

IRREVERSIBLE_RE = re.compile(
    r"""
    (
        rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)*-[a-zA-Z]*r
        | rm\s+-[a-zA-Z]*r[a-zA-Z]*\s+-[a-zA-Z]*f
        | \brm\s+-rf\b
        | \brm\s+-fr\b
        | git\s+reset\s+--hard
        | git\s+push\b[^\n]*--force
        | git\s+push\b[^\n]*\s-f\b
        | drop\s+database
        | mkfs
        | diskutil\s+erase
        | dd\s+if=
        | shutdown
        | reboot
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    needs_confirm: bool
    reason: str
    risk: str  # safe | write | destructive | irreversible


def command_risk(command: str) -> str:
    text = command.strip()
    if IRREVERSIBLE_RE.search(text):
        return "irreversible"
    if DESTRUCTIVE_RE.search(text):
        return "destructive"
    return "write"


def gate(level: int, tool: str, command: str | None = None) -> GateDecision:
    if level < 1 or level > 5:
        raise ValueError(f"autonomy must be 1-5, got {level}")

    risk = "safe"
    if tool == "run_shell" and command:
        risk = command_risk(command)
    elif tool in WRITE_TOOLS:
        risk = "write"
    elif tool not in SAFE_TOOLS:
        risk = "write"

    if risk == "irreversible":
        if level >= 5:
            return GateDecision(True, False, "autonomy 5: irreversible allowed, report after", risk)
        return GateDecision(False, True, "irreversible action needs explicit confirmation", risk)

    if level <= 1:
        return GateDecision(False, True, "autonomy 1: confirm every tool call", risk)
    if level == 2:
        if tool in SAFE_TOOLS:
            return GateDecision(True, False, "autonomy 2: safe tool", risk)
        return GateDecision(False, True, "autonomy 2: confirm writes and shell", risk)
    if level == 3:
        if risk in {"destructive", "irreversible"}:
            return GateDecision(False, True, "autonomy 3: confirm destructive actions", risk)
        return GateDecision(True, False, "autonomy 3: safe or non-destructive write", risk)
    if level == 4:
        if risk == "irreversible":
            return GateDecision(False, True, "autonomy 4: confirm irreversible actions", risk)
        return GateDecision(True, False, "autonomy 4: allowed", risk)
    return GateDecision(True, False, "autonomy 5: full auto", risk)
