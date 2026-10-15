from __future__ import annotations

import re
from pathlib import Path

SECRET_NAME_RE = re.compile(
    r"(api[_-]?key|secret|password|passwd|token|private[_-]?key|credential|auth)",
    re.IGNORECASE,
)
SECRET_VALUE_RE = re.compile(
    r"(?im)^(\s*(?:export\s+)?[A-Z0-9_]*"
    r"(?:API[_-]?KEY|SECRET|PASSWORD|TOKEN|PRIVATE[_-]?KEY|CREDENTIAL)[A-Z0-9_]*)"
    r"(\s*[=:]\s*)(.+)$"
)
BLOCKED_NAMES = (
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
    "authorized_keys",
)
BLOCKED_SUFFIXES = (".pem", ".p12", ".pfx", ".key")


class PathEscapeError(ValueError):
    pass


class SecretFileError(PermissionError):
    pass


def resolve_in_root(root: Path, rel: str) -> Path:
    if not rel or rel.strip() in {".", "./"}:
        return root.resolve()
    raw = Path(rel)
    if raw.is_absolute():
        candidate = raw.resolve()
    else:
        candidate = (root / raw).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise PathEscapeError(f"path {rel!r} escapes project root {root_resolved}") from exc
    if candidate.is_symlink():
        real = candidate.resolve()
        try:
            real.relative_to(root_resolved)
        except ValueError as exc:
            raise PathEscapeError(f"symlink {rel!r} escapes project root") from exc
    return candidate


def is_secret_file(path: Path) -> bool:
    name = path.name.lower()
    if name in BLOCKED_NAMES or name.startswith(".env"):
        return True
    if name.endswith(BLOCKED_SUFFIXES):
        return True
    if SECRET_NAME_RE.search(name) and name.endswith((".json", ".yml", ".yaml", ".txt", ".pem")):
        return True
    return False


def redact(text: str) -> str:
    def _sub(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}***REDACTED***"

    return SECRET_VALUE_RE.sub(_sub, text)


def assert_readable(path: Path, *, allow_secrets: bool) -> None:
    if is_secret_file(path) and not allow_secrets:
        raise SecretFileError(
            f"refusing to read secret-like file {path.name}; pass --allow-secrets if you really need it"
        )
