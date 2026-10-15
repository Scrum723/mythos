from __future__ import annotations

import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8790
DEFAULT_PROVIDER = "local"
DEFAULT_LOCAL_MODEL = "qwen2.5-coder:7b"
DEFAULT_LOCAL_BASE = "http://127.0.0.1:11434/v1"
DEFAULT_XAI_MODEL = "grok-4.6"
DEFAULT_XAI_BASE = "https://api.x.ai/v1"


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _parse_autonomy(raw: str | None, default: int = 3) -> int:
    if raw is None or raw == "":
        return default
    try:
        level = int(raw)
    except ValueError as exc:
        raise ValueError(f"autonomy must be an integer 1-5, got {raw!r}") from exc
    if level < 1 or level > 5:
        raise ValueError(f"autonomy must be 1-5, got {level}")
    return level


@dataclass
class Settings:
    root: Path
    autonomy: int
    provider: str
    model: str
    api_key: str
    api_base: str
    host: str
    port: int
    max_steps: int
    shell_timeout: int
    allow_secrets: bool

    @property
    def uses_xai(self) -> bool:
        return self.provider == "xai"

    @property
    def has_llm(self) -> bool:
        if self.uses_xai:
            return bool(self.api_key)
        return local_reachable(self.api_base)

    @classmethod
    def load(
        cls,
        *,
        root: str | Path | None = None,
        autonomy: int | None = None,
        allow_secrets: bool = False,
    ) -> Settings:
        return _load_settings(root=root, autonomy=autonomy, allow_secrets=allow_secrets)


def local_reachable(api_base: str) -> bool:
    root = api_base.rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    url = root + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _load_settings(
    *,
    root: str | Path | None = None,
    autonomy: int | None = None,
    allow_secrets: bool = False,
) -> Settings:
    _load_dotenv(PACKAGE_ROOT / ".env")
    cwd = Path.cwd().resolve()
    root_path = Path(root or os.environ.get("CODING_ROOT") or cwd).expanduser().resolve()
    level = autonomy if autonomy is not None else _parse_autonomy(os.environ.get("CODING_AUTONOMY"))
    port_raw = os.environ.get("CODING_PORT", str(DEFAULT_PORT))
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError(f"CODING_PORT must be an integer, got {port_raw!r}") from exc
    requested = (os.environ.get("CODING_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if requested and requested not in {"local", "xai"}:
        raise ValueError(f"CODING_PROVIDER must be local or xai, got {requested!r}")
    # Standing order: NO CHARGES. Never load an xAI key or api.x.ai base.
    # CODING_ALLOW_XAI / CODING_PROVIDER=xai / XAI_API_KEY are ignored.
    provider = "local"
    model = os.environ.get("CODING_MODEL") or DEFAULT_LOCAL_MODEL
    api_base = os.environ.get("CODING_API_BASE") or DEFAULT_LOCAL_BASE
    api_key = ""
    return Settings(
        root=root_path,
        autonomy=level,
        provider=provider,
        model=model,
        api_key=api_key,
        api_base=api_base,
        host=os.environ.get("CODING_HOST") or "127.0.0.1",
        port=port,
        max_steps=int(os.environ.get("CODING_MAX_STEPS") or "24"),
        shell_timeout=int(os.environ.get("CODING_SHELL_TIMEOUT") or "60"),
        allow_secrets=allow_secrets,
    )
