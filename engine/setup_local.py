from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import PACKAGE_ROOT, Settings, local_reachable

# Open weights from Hugging Face git (not xAI, not the Ollama registry).
BRAINS = {
    "qwen2.5-coder:7b": {
        "git": "https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "ollama": "qwen2.5-coder:7b",
    }
}


def models_dir() -> Path:
    path = PACKAGE_ROOT / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ollama_names(api_base: str) -> list[str]:
    root = api_base.rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    try:
        with urllib.request.urlopen(root + "/api/tags", timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []
    return [m.get("name") or "" for m in data.get("models") or []]


def _ensure_git_lfs() -> str | None:
    if shutil.which("git-lfs"):
        return shutil.which("git-lfs")
    brew = shutil.which("brew")
    if not brew:
        return None
    print("Installing git-lfs (needed to fetch model files from Hugging Face git)...")
    proc = subprocess.run(["brew", "install", "git-lfs"], check=False)
    if proc.returncode != 0:
        return None
    subprocess.run(["git", "lfs", "install"], check=False)
    return shutil.which("git-lfs")


def _ensure_ollama() -> str | None:
    ollama = shutil.which("ollama")
    if ollama:
        return ollama
    brew = shutil.which("brew")
    if not brew:
        return None
    print("Installing Ollama with Homebrew (local runner, not xAI)...")
    proc = subprocess.run(["brew", "install", "ollama"], check=False)
    if proc.returncode != 0:
        return None
    return shutil.which("ollama")


def _ensure_ollama_up(settings: Settings, ollama: str) -> bool:
    if local_reachable(settings.api_base):
        return True
    print("Starting ollama serve...")
    subprocess.Popen(
        [ollama, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(20):
        time.sleep(0.5)
        if local_reachable(settings.api_base):
            return True
    return False


def _git_fetch_gguf(spec: dict[str, str]) -> Path | None:
    dest = models_dir() / spec["file"]
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        print(f"Already on disk from git: {dest}")
        return dest
    lfs = _ensure_git_lfs()
    if not lfs:
        print("git-lfs is required to download brains from Hugging Face git.")
        return None
    work = models_dir() / "hf-src"
    if work.exists():
        shutil.rmtree(work)
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    print(f"Cloning {spec['git']} (pointers only, then one GGUF)...")
    clone = subprocess.run(
        ["git", "clone", "--depth", "1", spec["git"], str(work)],
        check=False,
        env=env,
    )
    if clone.returncode != 0:
        print("git clone failed.")
        return None
    pull = subprocess.run(
        ["git", "lfs", "pull", "--include", spec["file"]],
        cwd=work,
        check=False,
    )
    src = work / spec["file"]
    if pull.returncode != 0 or not src.is_file():
        print(f"git lfs pull of {spec['file']} failed.")
        return None
    shutil.copy2(src, dest)
    return dest


def _ollama_from_gguf(ollama: str, name: str, gguf: Path) -> int:
    modelfile = gguf.parent / "Modelfile"
    modelfile.write_text(f"FROM {gguf}\n", encoding="utf-8")
    print(f"Importing git GGUF into local Ollama as {name}...")
    return subprocess.run([ollama, "create", name, "-f", str(modelfile)], check=False).returncode


def setup(settings: Settings) -> int:
    if settings.uses_xai:
        print("CODING_PROVIDER=xai — not downloading a local brain.")
        print("Set CODING_PROVIDER=local in .env to stay off xAI billing.")
        return 1
    ollama = _ensure_ollama()
    if not ollama:
        print("Could not install Ollama. Install from https://ollama.com/download")
        return 1
    if not _ensure_ollama_up(settings, ollama):
        print("ollama serve did not come up on 127.0.0.1:11434")
        return 1

    have = ollama_names(settings.api_base)
    spec = BRAINS.get(settings.model) or BRAINS["qwen2.5-coder:7b"]
    name = spec["ollama"]
    if any(n == name or n.startswith(name) for n in have):
        print(f"Brain already present locally: {name}")
        print("Not cloning a second 4.7GB copy from git (disk is tight).")
        print(f"Git source if you ever need it: {spec['git']}")
        print("No xAI key required.")
        return 0

    gguf = _git_fetch_gguf(spec)
    if not gguf:
        return 1
    code = _ollama_from_gguf(ollama, name, gguf)
    if code != 0:
        print("ollama create from git GGUF failed.")
        return code
    print("Local brain ready from Hugging Face git. No xAI key required.")
    return 0
