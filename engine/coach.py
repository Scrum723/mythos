"""Read-only review of *other* agent projects. This agent does not live inside them."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

HARDCODED_SECRET = re.compile(
    r"""(?ix)
    (api[_-]?key|secret|password|token)
    \s*=\s*
    ['"][^'"]{8,}['"]
    """
)
COUPLING_IMPORT = re.compile(
    r"\b(agent-griffty|agent_griffty|wfad-ops|huge-grant|mythos-agent)\b",
    re.IGNORECASE,
)

MARKERS = (
    "SKILL.md",
    "agent.py",
    "CONSTITUTION.md",
    "PROMPT.md",
    "Dockerfile",
    "README.md",
    "main.py",
)


class TargetError(ValueError):
    pass


def resolve_target(raw: str) -> Path:
    cleaned = (raw or "").strip()
    slashy = cleaned.replace("\\", "/")
    if (
        not cleaned
        or "path/to/" in slashy
        or cleaned in {"other-agent", "project", "/path/to/other-agent", "/path/to/project"}
    ):
        raise TargetError(
            f"{cleaned!r} is a placeholder, not a real folder.\n"
            "Pass an actual directory, for example:\n"
            "  python3 agent.py improve ~/coding-agent"
        )
    path = Path(cleaned).expanduser().resolve()
    if not path.exists():
        raise TargetError(
            f"not found: {path}\n"
            "Pass a real directory on this machine, for example:\n"
            "  python3 agent.py improve ~/coding-agent"
        )
    if not path.is_dir():
        raise TargetError(f"not a directory: {path}")
    forbidden = {Path("/"), Path("/Users"), Path("/home"), Path.home()}
    if path in forbidden:
        raise TargetError(f"refusing to target {path} — pick a specific agent directory")
    return path


def scan(target: str | Path) -> dict[str, Any]:
    root = resolve_target(str(target))
    checks: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, detail: str, *, level: str = "warn") -> None:
        checks.append({"id": cid, "ok": ok, "detail": detail, "level": "ok" if ok else level})

    add("readme", (root / "README.md").is_file(), "README.md with how to run")
    tests_dir = root / "tests"
    has_tests = tests_dir.is_dir() and any(tests_dir.rglob("test_*.py"))
    has_tests = has_tests or any(root.glob("test_*.py"))
    add("tests", has_tests, "automated tests (test_*.py)")
    add("dockerfile", (root / "Dockerfile").is_file(), "Dockerfile for container runs")
    gitignore = _read(root / ".gitignore")
    add("gitignore_env", ".env" in gitignore, ".gitignore excludes .env", level="fail")
    add("env_example", (root / ".env.example").is_file(), ".env.example without real secrets")
    add(
        "entry",
        (root / "agent.py").is_file() or (root / "main.py").is_file() or (root / "SKILL.md").is_file(),
        "runnable entry (agent.py, main.py, or SKILL.md)",
    )
    add(
        "prompt",
        (root / "CONSTITUTION.md").is_file()
        or (root / "PROMPT.md").is_file()
        or (root / "SKILL.md").is_file(),
        "written role/prompt (CONSTITUTION, PROMPT, or SKILL)",
    )
    web = (root / "web").is_dir() or (root / "templates").is_dir() or (root / "frontend").is_dir()
    add("web", web, "web or UI surface (optional)", level="info")

    secret_hits = _scan_secrets(root)
    add("no_hardcoded_secrets", not secret_hits, secret_hits[0] if secret_hits else "no hardcoded key literals", level="fail")

    coupling = _scan_coupling(root)
    add(
        "independent",
        not coupling,
        coupling[0] if coupling else "no imports of other named agent projects",
        level="warn",
    )

    markers_found = [name for name in MARKERS if (root / name).is_file()]
    ok_count = sum(1 for c in checks if c["ok"])
    fail_count = sum(1 for c in checks if not c["ok"] and c["level"] == "fail")
    report = {
        "target": str(root),
        "name": root.name,
        "markers": markers_found,
        "score": f"{ok_count}/{len(checks)}",
        "fails": fail_count,
        "checks": checks,
        "apply_hint": (
            f'python3 agent.py -a 3 -r "{root}" improve "{root}"'
            if fail_count or any(not c["ok"] for c in checks)
            else "no blocking gaps"
        ),
        "note": (
            "This scan is read-only. Coding-agent is a separate project. "
            "Other agents are targets to improve, not code to inherit."
        ),
    }
    return report


def _read(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _iter_text_files(root: Path):
    skip = {".git", "node_modules", ".venv", "__pycache__", "engine", "mythos"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".ts", ".js", ".md", ".json", ".toml", ".yml", ".yaml", ".sh"}:
            continue
        if path.stat().st_size > 400_000:
            continue
        yield path


def _scan_secrets(root: Path) -> list[str]:
    hits = []
    for path in _iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if HARDCODED_SECRET.search(text):
            rel = path.relative_to(root)
            hits.append(f"possible hardcoded secret in {rel}")
            if len(hits) >= 5:
                break
    return hits


def _scan_coupling(root: Path) -> list[str]:
    hits = []
    for path in _iter_text_files(root):
        if path.suffix != ".py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if COUPLING_IMPORT.search(text):
            hits.append(f"couples to another agent project in {path.relative_to(root)}")
            if len(hits) >= 5:
                break
    return hits


def improve_task(target: Path, *, apply: bool) -> str:
    report = scan(target)
    gaps = [c for c in report["checks"] if not c["ok"]]
    gap_lines = "\n".join(f"- [{c['level']}] {c['id']}: {c['detail']}" for c in gaps) or "- none"
    action = (
        "Apply small, safe fixes inside the TARGET only. Do not copy this coding-agent into it. "
        "Do not import Griffty, WFAD, Huge Grant, or the Mythos factory. Keep the target independent."
        if apply
        else "Do not modify files. Produce a prioritized improvement plan only."
    )
    return (
        f"You are reviewing another agent as an EXTERNAL target.\n"
        f"Target: {target}\n"
        f"This coding-agent project must stay separate.\n\n"
        f"Scanner report ({report['score']}):\n{gap_lines}\n\n"
        f"{action}\n"
        "Focus: tests, secrets, .env gitignore, runnable entry, honest failure handling, "
        "CLI/web packaging, autonomy/confirmation for destructive work.\n"
        "End with what you changed (if anything) and what you did not verify."
    )
