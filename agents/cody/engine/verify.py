from __future__ import annotations

import shutil
from pathlib import Path

from .languages import detect


def suggested_test_command(root: Path) -> str | None:
    if (root / "package.json").is_file() and shutil.which("npm"):
        return "npm test"
    if (root / "go.mod").is_file():
        return "go test ./..."
    if (root / "Cargo.toml").is_file():
        return "cargo test"
    if (root / "tests").is_dir() and any((root / "tests").rglob("test_*.py")):
        return "python3 -m unittest discover -s tests -v"
    if any(root.glob("test_*.py")):
        return "python3 -m unittest discover -s . -p 'test_*.py' -v"
    lang = detect(root)["primary"]
    if lang == "python":
        return "python3 -m compileall -q ."
    if lang in {"javascript", "typescript"}:
        return "npm test"
    return None
