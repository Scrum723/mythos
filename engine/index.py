from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .config import PACKAGE_ROOT
from .security import SecretFileError, assert_readable

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "models", ".ollama", "index"}
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".woff", ".zip", ".pyc", ".gguf"}
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def index_path_for(root: Path) -> Path:
    cache = PACKAGE_ROOT / "data" / "index"
    cache.mkdir(parents=True, exist_ok=True)
    key = str(root.resolve()).replace("/", "_").replace(" ", "_")[-120:]
    return cache / f"{key}.json"


def build_index(root: Path, *, allow_secrets: bool = False, max_files: int = 2000) -> dict[str, Any]:
    root = root.resolve()
    files: list[dict[str, Any]] = []
    inv: dict[str, list[str]] = {}
    count = 0
    for path in root.rglob("*"):
        if count >= max_files:
            break
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIX:
            continue
        try:
            assert_readable(path, allow_secrets=allow_secrets)
            if path.stat().st_size > 400_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except (SecretFileError, OSError, UnicodeError):
            continue
        rel = str(path.relative_to(root))
        tokens = set(TOKEN_RE.findall(text)) | set(TOKEN_RE.findall(rel))
        files.append({"path": rel, "bytes": len(text), "tokens": len(tokens)})
        for tok in tokens:
            key = tok.lower()
            bucket = inv.setdefault(key, [])
            if rel not in bucket and len(bucket) < 40:
                bucket.append(rel)
        count += 1
    payload = {
        "root": str(root),
        "built_at": time.time(),
        "files": files,
        "inv": inv,
    }
    dest = index_path_for(root)
    dest.write_text(json.dumps(payload), encoding="utf-8")
    return {"files": len(files), "terms": len(inv), "path": str(dest)}


def load_index(root: Path) -> dict[str, Any] | None:
    path = index_path_for(root)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def ensure_index(root: Path, *, allow_secrets: bool = False, max_age_s: float = 3600) -> dict[str, Any]:
    existing = load_index(root)
    if existing and (time.time() - float(existing.get("built_at") or 0)) < max_age_s:
        if existing.get("root") == str(root.resolve()):
            return {"cached": True, "files": len(existing.get("files") or []), "terms": len(existing.get("inv") or {})}
    stats = build_index(root, allow_secrets=allow_secrets)
    stats["cached"] = False
    return stats


def retrieve(root: Path, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    data = load_index(root)
    if not data:
        ensure_index(root)
        data = load_index(root) or {"inv": {}, "files": []}
    terms = [t.lower() for t in TOKEN_RE.findall(query)]
    if not terms:
        return []
    scores: dict[str, float] = {}
    inv = data.get("inv") or {}
    for term in terms:
        for path in inv.get(term) or []:
            scores[path] = scores.get(path, 0.0) + 1.0
            if term in path.lower():
                scores[path] += 0.5
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
    return [{"path": path, "score": score} for path, score in ranked]
