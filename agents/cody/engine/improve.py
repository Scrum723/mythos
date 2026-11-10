from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import PACKAGE_ROOT


def log_path() -> Path:
    data = PACKAGE_ROOT / "data"
    data.mkdir(parents=True, exist_ok=True)
    return data / "improvements.jsonl"


def append(entry: dict[str, Any]) -> dict[str, Any]:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "area": entry.get("area") or "general",
        "note": (entry.get("note") or "").strip(),
        "task": entry.get("task") or "",
    }
    if not record["note"]:
        raise ValueError("improvement note is required")
    path = log_path()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_all(limit: int = 50) -> list[dict[str, Any]]:
    path = log_path()
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(rows))
