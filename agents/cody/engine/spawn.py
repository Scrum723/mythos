from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .config import PACKAGE_ROOT

NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")

AGENT_PY = '''#!/usr/bin/env python3
"""Standalone agent: __NAME__

Role: __ROLE__

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
'''

DOCKERFILE = """FROM python:3.12-slim
WORKDIR /app
COPY . /app
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    CODING_PROVIDER=local \\
    CODING_MODEL=qwen2.5-coder:7b \\
    CODING_API_BASE=http://127.0.0.1:11434/v1 \\
    CODING_AUTONOMY=3 \\
    CODING_HOST=0.0.0.0 \\
    CODING_PORT=8790 \\
    CODING_ROOT=/workspace
RUN mkdir -p /workspace && chmod +x /app/agent.py
EXPOSE 8790
CMD ["python3", "agent.py", "serve"]
"""

README = """# __TITLE__

Standalone agent. Copy this folder to a laptop, server, or container.

**Role:** __ROLE__

**Constraints:** __CONSTRAINTS__

Autonomy default is 3: safe work runs; destructive actions wait for confirmation.

Default brain is **local Ollama** (no xAI billing). **NO CHARGES.**

## Run

```bash
cp .env.example .env   # local Ollama defaults; no XAI_API_KEY needed
python3 agent.py setup # only if the local brain is missing
python3 agent.py health
python3 agent.py -a 3 -r /path/to/project run "your task"
python3 agent.py chat -r /path/to/project
python3 agent.py serve --host 127.0.0.1 --port 8790
```

Desk: http://127.0.0.1:8790

If Ollama is not running, the agent refuses honestly instead of calling a paid API.

## Docker

```bash
docker build -t __NAME__ .
docker run --rm -p 8790:8790 -e CODING_PROVIDER=local -v "$PWD":/workspace __NAME__
```

Do not publish port 8790 to the internet. There is no login.
"""

ENV_EXAMPLE = """# Default: local Ollama. No xAI billing.
CODING_PROVIDER=local
CODING_MODEL=qwen2.5-coder:7b
CODING_API_BASE=http://127.0.0.1:11434/v1
CODING_AUTONOMY=3
CODING_HOST=127.0.0.1
CODING_PORT=8790
# CODING_ROOT=/path/to/project

# NO CHARGES. xAI billing is disabled in this agent. Local Ollama only.
"""


def agents_dir() -> Path:
    path = PACKAGE_ROOT / "agents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def spawn(
    *,
    name: str,
    role: str,
    prompt: str,
    tools: str,
    constraints: str,
    dest: str | Path | None = None,
) -> dict[str, Any]:
    name = name.strip().lower()
    if not NAME_RE.match(name):
        raise ValueError("name must be 2-64 chars, lowercase letters, digits, hyphens")
    target = Path(dest).expanduser().resolve() if dest else agents_dir() / name
    target.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": name,
        "role": role.strip(),
        "tools": [t.strip() for t in tools.split(",") if t.strip()],
        "constraints": constraints.strip(),
        "prompt": prompt.strip(),
        "standalone": True,
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (target / "PROMPT.md").write_text(
        f"# {name}\n\n**Role:** {role.strip()}\n\n## Constraints\n\n{constraints.strip()}\n\n## Prompt\n\n{prompt.strip()}\n",
        encoding="utf-8",
    )
    (target / "CONSTITUTION.md").write_text(
        f"# {name}\n\n{role.strip()}\n\n## Constraints\n\n{constraints.strip()}\n\n"
        "Honesty is non-negotiable. Never fabricate results, tests, or capabilities.\n"
        "Stay inside the project root. Never hardcode secrets. Confirm destructive "
        "actions unless autonomy is 5. After each task, log one improvement.\n",
        encoding="utf-8",
    )
    _vendor_runtime(target)
    _brand_web(target, name, role.strip())
    script = AGENT_PY.replace("__NAME__", name).replace("__ROLE__", role.strip())
    agent_path = target / "agent.py"
    agent_path.write_text(script, encoding="utf-8")
    agent_path.chmod(agent_path.stat().st_mode | 0o111)
    title = name.replace("-", " ").title()
    (target / "README.md").write_text(
        README.replace("__TITLE__", title)
        .replace("__ROLE__", role.strip())
        .replace("__CONSTRAINTS__", constraints.strip())
        .replace("__NAME__", name),
        encoding="utf-8",
    )
    (target / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
    (target / ".env.example").write_text(ENV_EXAMPLE, encoding="utf-8")
    (target / ".gitignore").write_text(".venv/\n__pycache__/\n.env\ndata/*.jsonl\n", encoding="utf-8")
    (target / "data").mkdir(exist_ok=True)
    return {
        "name": name,
        "path": str(target),
        "run": f'python3 {agent_path} -a 3 -r /path/to/project "task"',
        "serve": f"python3 {agent_path} serve --port 8790",
        "manifest": manifest,
    }


def _vendor_runtime(dest: Path) -> None:
    src = PACKAGE_ROOT / "engine"
    out = dest / "engine"
    out.mkdir(parents=True, exist_ok=True)
    for path in src.glob("*.py"):
        shutil.copy2(path, out / path.name)
    web_src = PACKAGE_ROOT / "web"
    web_dst = dest / "web"
    if web_dst.exists():
        shutil.rmtree(web_dst)
    shutil.copytree(web_src, web_dst, ignore=shutil.ignore_patterns("__pycache__"))


def _brand_web(dest: Path, name: str, role: str) -> None:
    index = dest / "web" / "index.html"
    if not index.is_file():
        return
    title = name.replace("-", " ").title()
    text = index.read_text(encoding="utf-8")
    text = text.replace("<title>Mythos</title>", f"<title>{title}</title>")
    text = text.replace("<h1>Mythos</h1>", f"<h1>{title}</h1>")
    text = text.replace("Local coding agent · CLI + desk", role[:90])
    index.write_text(text, encoding="utf-8")


def list_agents() -> list[dict[str, Any]]:
    rows = []
    root = agents_dir()
    for child in sorted(root.iterdir()):
        manifest = child / "manifest.json"
        if child.is_dir() and manifest.is_file():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {"name": child.name, "error": "invalid manifest"}
            data["path"] = str(child)
            data["standalone"] = (child / "engine" / "__init__.py").is_file()
            rows.append(data)
    return rows
