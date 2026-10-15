from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .config import Settings
from .index import build_index, ensure_index, retrieve
from .prompt_build import prompt_stats
from .tools import ToolBox, tool_schemas


def report(settings: Settings) -> dict[str, Any]:
    prompt = prompt_stats(settings, mode="chat")
    prompt_code = prompt_stats(settings, mode="code")
    old_tools = 13  # prior schema count before retrieve/batch/prefer
    new_chat = len(tool_schemas(mode="chat"))
    new_code = len(tool_schemas(mode="code"))

    t0 = time.perf_counter()
    build_index(settings.root, allow_secrets=settings.allow_secrets)
    index_ms = round((time.perf_counter() - t0) * 1000, 1)
    t1 = time.perf_counter()
    ensure_index(settings.root, allow_secrets=settings.allow_secrets)
    cache_ms = round((time.perf_counter() - t1) * 1000, 1)
    t2 = time.perf_counter()
    hits = retrieve(settings.root, "Settings load autonomy tool", limit=5)
    retrieve_ms = round((time.perf_counter() - t2) * 1000, 1)

    box = ToolBox(settings)
    paths = ["engine/config.py", "engine/agent.py", "engine/tools.py", "README.md"]
    t3 = time.perf_counter()
    for p in paths:
        box.execute("read_file", {"path": p, "limit": 40})
    seq_ms = round((time.perf_counter() - t3) * 1000, 1)
    t4 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda p: box.execute("read_file", {"path": p, "limit": 40}), paths))
    par_ms = round((time.perf_counter() - t4) * 1000, 1)
    t5 = time.perf_counter()
    box.execute("batch_read", {"paths": ",".join(paths), "limit": 40})
    batch_ms = round((time.perf_counter() - t5) * 1000, 1)

    return {
        "bottlenecks_fixed": [
            "slow response generation — slim per-mode system prompt + prefs cache",
            "stiff/verbose chat — chat mode, short style rules, fewer tools",
            "slow retrieval — local inverted index + retrieve tool",
        ],
        "prompt": {
            "chat": prompt,
            "code": prompt_code,
        },
        "tools": {
            "old_count": old_tools,
            "chat_count": new_chat,
            "code_count": new_code,
        },
        "index": {
            "build_ms": index_ms,
            "cache_hit_ms": cache_ms,
            "retrieve_ms": retrieve_ms,
            "hits": hits,
            "speedup_vs_cold": round(index_ms / max(cache_ms, 0.01), 1),
        },
        "reads": {
            "sequential_ms": seq_ms,
            "parallel_ms": par_ms,
            "batch_ms": batch_ms,
            "parallel_speedup": round(seq_ms / max(par_ms, 0.01), 2),
            "batch_speedup": round(seq_ms / max(batch_ms, 0.01), 2),
        },
        "no_charges": True,
    }
