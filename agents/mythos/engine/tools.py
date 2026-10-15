from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from . import improve
from .autonomy import gate
from .config import Settings
from .languages import detect
from .planner import heuristic_plan
from .security import (
    PathEscapeError,
    SecretFileError,
    assert_readable,
    redact,
    resolve_in_root,
)
from .verify import suggested_test_command

MAX_READ_BYTES = 200_000
MAX_WRITE_BYTES = 1_000_000
MAX_GREP_HITS = 80


CHAT_TOOLS = {
    "list_dir",
    "read_file",
    "batch_read",
    "grep",
    "retrieve",
    "git_status",
    "remember_preference",
}


def tool_schemas(*, mode: str = "code") -> list[dict[str, Any]]:
    all_tools = [
        _fn(
            "list_dir",
            "List files in a directory under the project root.",
            {"path": {"type": "string", "description": "Relative directory. Use . for root."}},
            [],
        ),
        _fn(
            "read_file",
            "Read a text file under the project root. Secret-like files are blocked.",
            {
                "path": {"type": "string"},
                "offset": {"type": "integer", "description": "1-based start line"},
                "limit": {"type": "integer", "description": "Max lines to return"},
            },
            ["path"],
        ),
        _fn(
            "batch_read",
            "Read several small text files in one call. Prefer this over many read_file calls.",
            {
                "paths": {
                    "type": "string",
                    "description": "Comma-separated relative paths (max 8)",
                },
                "limit": {"type": "integer", "description": "Max lines per file (default 120)"},
            },
            ["paths"],
        ),
        _fn(
            "write_file",
            "Create or overwrite a text file under the project root.",
            {"path": {"type": "string"}, "content": {"type": "string"}},
            ["path", "content"],
        ),
        _fn(
            "grep",
            "Regex search. Prefer retrieve for symbol/name lookup.",
            {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "Relative file or directory"},
                "glob": {"type": "string"},
            },
            ["pattern"],
        ),
        _fn(
            "retrieve",
            "One-step codebase lookup via the local index. Query with symbols or keywords.",
            {"query": {"type": "string"}, "limit": {"type": "integer"}},
            ["query"],
        ),
        _fn(
            "index_repo",
            "Rebuild the local code index (usually automatic).",
            {},
            [],
        ),
        _fn(
            "run_shell",
            "Run a shell command in the project root. Destructive commands are gated by autonomy.",
            {"command": {"type": "string"}},
            ["command"],
        ),
        _fn(
            "run_tests",
            "Run the project's tests or compile check.",
            {"command": {"type": "string", "description": "Override test command"}},
            [],
        ),
        _fn("git_status", "Read-only git status for the project root.", {}, []),
        _fn("detect_language", "Detect primary language from files and markers.", {}, []),
        _fn(
            "plan_task",
            "Build a short plan with subgoals (skip for tiny tasks).",
            {"task": {"type": "string"}},
            ["task"],
        ),
        _fn(
            "spawn_agent",
            "Write a standalone sub-agent module.",
            {
                "name": {"type": "string"},
                "role": {"type": "string"},
                "tools": {"type": "string"},
                "constraints": {"type": "string"},
                "prompt": {"type": "string"},
            },
            ["name", "role", "prompt"],
        ),
        _fn(
            "log_improvement",
            "Append a self-review note.",
            {"area": {"type": "string"}, "note": {"type": "string"}},
            ["note"],
        ),
        _fn(
            "remember_preference",
            "Save a durable user preference (style, stack, explanation taste).",
            {"note": {"type": "string"}},
            ["note"],
        ),
        _fn("list_agents", "List spawned sub-agents.", {}, []),
        _fn("read_improvements", "Read recent improvement log entries.", {}, []),
    ]
    if mode == "chat":
        return [t for t in all_tools if t["function"]["name"] in CHAT_TOOLS]
    return all_tools


def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


class ToolError(RuntimeError):
    pass


class ConfirmationRequired(Exception):
    def __init__(self, tool: str, args: dict[str, Any], reason: str, risk: str) -> None:
        super().__init__(reason)
        self.tool = tool
        self.args = args
        self.reason = reason
        self.risk = risk


class ToolBox:
    def __init__(self, settings: Settings, confirmer: Callable[[str, dict, str, str], bool] | None = None) -> None:
        self.settings = settings
        self.confirmer = confirmer
        self.handlers: dict[str, Callable[[dict[str, Any]], str]] = {
            "list_dir": self.list_dir,
            "read_file": self.read_file,
            "batch_read": self.batch_read,
            "write_file": self.write_file,
            "grep": self.grep,
            "retrieve": self.retrieve,
            "index_repo": self.index_repo,
            "run_shell": self.run_shell,
            "run_tests": self.run_tests,
            "git_status": self.git_status,
            "detect_language": self.detect_language,
            "plan_task": self.plan_task,
            "spawn_agent": self.spawn_agent,
            "log_improvement": self.log_improvement,
            "remember_preference": self.remember_preference,
            "list_agents": self.list_agents,
            "read_improvements": self.read_improvements,
        }

    def execute(self, name: str, args: dict[str, Any], *, confirmed: bool = False) -> str:
        if name not in self.handlers:
            raise ToolError(f"unknown tool: {name}")
        command = args.get("command") if name in {"run_shell", "run_tests"} else None
        decision = gate(self.settings.autonomy, name, command)
        if decision.needs_confirm and not confirmed:
            if self.confirmer and self.confirmer(name, args, decision.reason, decision.risk):
                confirmed = True
            else:
                raise ConfirmationRequired(name, args, decision.reason, decision.risk)
        if not decision.allowed and not confirmed:
            raise ConfirmationRequired(name, args, decision.reason, decision.risk)
        try:
            result = self.handlers[name](args)
        except (PathEscapeError, SecretFileError, ToolError) as exc:
            return f"ERROR: {exc}"
        return redact(result)

    def list_dir(self, args: dict[str, Any]) -> str:
        root = self.settings.root.resolve()
        path = resolve_in_root(root, args.get("path") or ".")
        if not path.exists():
            raise ToolError(f"not found: {path}")
        if not path.is_dir():
            raise ToolError(f"not a directory: {path}")
        entries = []
        for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
            if child.name.startswith("."):
                continue
            kind = "dir" if child.is_dir() else "file"
            entries.append(f"{kind}\t{child.relative_to(root)}")
        return "\n".join(entries) or "(empty)"

    def read_file(self, args: dict[str, Any]) -> str:
        path = resolve_in_root(self.settings.root, args["path"])
        if not path.is_file():
            raise ToolError(f"not a file: {args['path']}")
        assert_readable(path, allow_secrets=self.settings.allow_secrets)
        data = path.read_bytes()
        if len(data) > MAX_READ_BYTES:
            data = data[:MAX_READ_BYTES]
            truncated = True
        else:
            truncated = False
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()
        offset = max(int(args.get("offset") or 1), 1)
        limit = int(args.get("limit") or 400)
        slice_ = lines[offset - 1 : offset - 1 + limit]
        numbered = [f"{i}\t{line}" for i, line in enumerate(slice_, start=offset)]
        out = "\n".join(numbered)
        if truncated:
            out += "\n[truncated]"
        return out

    def batch_read(self, args: dict[str, Any]) -> str:
        raw = args.get("paths") or ""
        paths = [p.strip() for p in str(raw).split(",") if p.strip()]
        if not paths:
            raise ToolError("paths is required")
        if len(paths) > 8:
            paths = paths[:8]
        limit = int(args.get("limit") or 120)
        chunks = []
        for rel in paths:
            try:
                body = self.read_file({"path": rel, "offset": 1, "limit": limit})
            except (ToolError, PathEscapeError, SecretFileError, KeyError) as exc:
                body = f"ERROR: {exc}"
            chunks.append(f"## {rel}\n{body}")
        return "\n\n".join(chunks)

    def retrieve(self, args: dict[str, Any]) -> str:
        from .index import retrieve

        query = (args.get("query") or "").strip()
        if not query:
            raise ToolError("query is required")
        limit = int(args.get("limit") or 8)
        hits = retrieve(self.settings.root, query, limit=limit)
        if not hits:
            return "(no index hits — try grep or index_repo)"
        return "\n".join(f"{h['score']:.1f}\t{h['path']}" for h in hits)

    def index_repo(self, args: dict[str, Any]) -> str:
        from .index import build_index

        stats = build_index(self.settings.root, allow_secrets=self.settings.allow_secrets)
        return json.dumps(stats, indent=2)

    def remember_preference(self, args: dict[str, Any]) -> str:
        from . import prefs

        return prefs.append(str(args.get("note") or ""))

    def write_file(self, args: dict[str, Any]) -> str:
        rel = args["path"]
        content = args.get("content") or ""
        if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
            raise ToolError("file too large to write")
        path = resolve_in_root(self.settings.root, rel)
        if path.suffix.lower() in {".pem", ".key", ".p12"} and not self.settings.allow_secrets:
            raise SecretFileError("refusing to write credential material")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"wrote {path.relative_to(self.settings.root)} ({len(content)} chars)"

    def grep(self, args: dict[str, Any]) -> str:
        pattern = args["pattern"]
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ToolError(f"invalid regex: {exc}") from exc
        start = resolve_in_root(self.settings.root, args.get("path") or ".")
        glob = args.get("glob") or "*"
        files: list[Path] = []
        if start.is_file():
            files = [start]
        else:
            files = [p for p in start.rglob(glob) if p.is_file()]
        hits: list[str] = []
        for path in files:
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".woff", ".zip"}:
                continue
            if any(part in {".git", "node_modules", ".venv", "__pycache__"} for part in path.parts):
                continue
            try:
                assert_readable(path, allow_secrets=self.settings.allow_secrets)
                text = path.read_text(encoding="utf-8", errors="replace")
            except (SecretFileError, OSError):
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    rel = path.relative_to(self.settings.root)
                    hits.append(f"{rel}:{i}:{line[:240]}")
                    if len(hits) >= MAX_GREP_HITS:
                        hits.append("[truncated]")
                        return "\n".join(hits)
        return "\n".join(hits) or "(no matches)"

    def run_shell(self, args: dict[str, Any]) -> str:
        command = (args.get("command") or "").strip()
        if not command:
            raise ToolError("command is required")
        return self._run(command)

    def run_tests(self, args: dict[str, Any]) -> str:
        command = (args.get("command") or "").strip() or suggested_test_command(self.settings.root)
        if not command:
            return "ERROR: no test command detected. Pass command=..."
        return self._run(command)

    def _run(self, command: str) -> str:
        env = os.environ.copy()
        env.pop("XAI_API_KEY", None)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.settings.root,
                capture_output=True,
                text=True,
                timeout=self.settings.shell_timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return f"ERROR: timed out after {self.settings.shell_timeout}s"
        out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        out = out[-12_000:]
        return f"exit {proc.returncode}\n{out}".strip()

    def git_status(self, args: dict[str, Any]) -> str:
        return self._run("git status --short --branch")

    def detect_language(self, args: dict[str, Any]) -> str:
        return json.dumps(detect(self.settings.root), indent=2)

    def plan_task(self, args: dict[str, Any]) -> str:
        task = args.get("task") or ""
        plan = heuristic_plan(task, self.settings.root)
        return json.dumps(plan, indent=2)

    def spawn_agent(self, args: dict[str, Any]) -> str:
        from .spawn import spawn

        result = spawn(
            name=args["name"],
            role=args["role"],
            prompt=args["prompt"],
            tools=args.get("tools") or "list_dir,read_file,write_file,grep,run_shell,run_tests",
            constraints=args.get("constraints") or "Stay in project root. No secrets. Honesty first.",
        )
        return json.dumps(result, indent=2)

    def log_improvement(self, args: dict[str, Any]) -> str:
        record = improve.append({"area": args.get("area"), "note": args["note"], "task": args.get("task")})
        return json.dumps(record, indent=2)

    def list_agents(self, args: dict[str, Any]) -> str:
        from .spawn import list_agents

        return json.dumps(list_agents(), indent=2)

    def read_improvements(self, args: dict[str, Any]) -> str:
        return json.dumps(improve.read_all(), indent=2)
