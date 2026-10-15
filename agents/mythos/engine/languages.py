from __future__ import annotations

from pathlib import Path

MARKER_FILES = {
    "package.json": "javascript",
    "tsconfig.json": "typescript",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "Pipfile": "python",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "kotlin",
    "Gemfile": "ruby",
    "composer.json": "php",
    "Package.swift": "swift",
    "CMakeLists.txt": "cpp",
    "Makefile": "shell",
}

EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
}

IDIOMS = {
    "python": "PEP 8, type hints, pathlib, pytest or unittest, venv",
    "javascript": "ES modules if package.json type=module, otherwise match the repo; no new frameworks unless asked",
    "typescript": "strict types, match existing tsconfig, avoid any",
    "go": "gofmt, context.Context on IO, table-driven tests",
    "rust": "rustfmt, Result/Option, cargo test",
    "java": "idiomatic packages, JUnit if present",
    "cpp": "modern C++ (C++17+), RAII, no raw new/delete unless matching the file",
    "csharp": "nullable reference types if enabled, xUnit/NUnit if present",
    "ruby": "snake_case, Minitest/RSpec if present",
    "php": "match composer autoload, PHPUnit if present",
    "swift": "Swift API design guidelines, XCTest if present",
    "kotlin": "null safety, match Gradle/Android or JVM layout",
    "shell": "set -euo pipefail, quote variables, no eval",
}


_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".tox",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
}


def detect(root: Path, hint_path: str | None = None) -> dict:
    scores: dict[str, int] = {}
    root = Path(root)
    for name, lang in MARKER_FILES.items():
        if (root / name).is_file():
            scores[lang] = scores.get(lang, 0) + 5
    if hint_path:
        ext = Path(hint_path).suffix.lower()
        lang = EXTENSIONS.get(ext)
        if lang:
            scores[lang] = scores.get(lang, 0) + 8
    # Walk a few levels so nested source (engine/, src/) outweighs a lone Makefile/.sh.
    try:
        for dirpath, dirnames, filenames in root.walk(top_down=True):
            rel = dirpath.relative_to(root)
            depth = 0 if str(rel) == "." else len(rel.parts)
            if depth > 3:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
            for filename in filenames:
                lang = EXTENSIONS.get(Path(filename).suffix.lower())
                if lang:
                    scores[lang] = scores.get(lang, 0) + 1
    except AttributeError:
        # Python < 3.12: Path.walk missing
        _walk_fallback(root, scores, max_depth=3)
    except OSError:
        pass
    # Prefer non-shell when tied so a repo script does not beat real source.
    ranked = sorted(
        scores.items(),
        key=lambda item: (item[1], 0 if item[0] == "shell" else 1),
        reverse=True,
    )
    primary = ranked[0][0] if ranked else "unknown"
    return {
        "primary": primary,
        "scores": {k: v for k, v in ranked},
        "idiom": IDIOMS.get(primary, "match the surrounding files"),
        "supported": sorted(IDIOMS),
    }


def _walk_fallback(root: Path, scores: dict[str, int], *, max_depth: int) -> None:
    def visit(path: Path, depth: int) -> None:
        try:
            children = list(path.iterdir())
        except OSError:
            return
        for child in children:
            if child.is_file():
                lang = EXTENSIONS.get(child.suffix.lower())
                if lang:
                    scores[lang] = scores.get(lang, 0) + 1
            elif child.is_dir() and depth < max_depth:
                if child.name in _SKIP_DIRS or child.name.startswith("."):
                    continue
                visit(child, depth + 1)

    visit(root, 0)
