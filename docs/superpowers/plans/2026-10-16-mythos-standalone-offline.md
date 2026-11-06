# Mythos Standalone Offline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Mythos a fully owner-controlled standalone local agent that can code, generate, and run local LLM/ML inference without any remote server after brains are on disk.

**Architecture:** Keep Ollama-on-loopback as the default runner; add an airgap/network policy, offline brain inventory, and an optional in-process `llama_cpp` GGUF backend when Ollama is down. Extend health + educate so the owner can verify and improve Mythos offline.

**Tech Stack:** Python 3, urllib, optional `llama_cpp`, local GGUF under `models/`, unittest.

**Spec:** `docs/superpowers/specs/2026-10-16-mythos-standalone-offline.md`

## Global Constraints

- NO CHARGES / never call `api.x.ai` / never require `XAI_API_KEY`.
- Preserve modes `code` | `create` | `chat` and existing provider/health/tool tests.
- Airgap default for inference hosts: only `127.0.0.1` / `localhost` loopback allowed for LLM HTTP.
- Optional dependency: `llama_cpp` — code must work when it is missing (skip in-process path).
- Windows-friendly paths; no brew-only assumptions in new code paths.

## Review Focus

- Airgap on + remote `CODING_API_BASE` → LLM client refuses before any network call.
- GGUF present + Ollama down + no llama_cpp → clear offline message, no crash.
- GGUF present + llama_cpp available → chat returns content without contacting non-loopback hosts.
- `educate` with airgap on never opens remote URLs.
- Health JSON stays stable across two runs for offline fields.

---

### Task 1: Commit baseline general-intelligence work on a feature branch

**Files:**
- Modify: existing uncommitted Mythos AGI/mode files (already on disk)
- Test: `tests/test_modes.py`, `tests/test_health.py`, `tests/test_provider.py`

**Interfaces:**
- Consumes: current dirty tree on `main`
- Produces: branch `feature/mythos-standalone-offline` with baseline committed

- [x] **Step 1: Create branch `feature/mythos-standalone-offline` from current tree**

Run: `git checkout -b feature/mythos-standalone-offline`
Expected: on new branch

- [x] **Step 2: Run baseline suite**

Run: `python -m unittest discover -s tests -v`
Expected: all tests PASS

- [x] **Step 3: Commit baseline**

```bash
git add -A
git commit -m "feat: Mythos general modes (code/create/chat) and standalone identity"
```

---

### Task 2: Airgap / loopback network policy for LLM hosts

**Files:**
- Create: `engine/network_policy.py`
- Modify: `engine/config.py`, `engine/llm.py`, `engine/setup_local.py`
- Test: `tests/test_offline.py`

**Interfaces:**
- Consumes: `Settings.api_base`, env `MYTHOS_AIRGAP` / `CODING_AIRGAP`
- Produces:
  - `is_loopback_url(url: str) -> bool`
  - `airgap_enabled() -> bool`
  - `assert_local_llm_base(api_base: str) -> None` raises `LLMError` / `ValueError` on non-loopback
  - `Settings.airgap: bool`, `Settings.network_mode: str` (`"airgap"` | `"local"`)

- [ ] **Step 1: Write failing tests in `tests/test_offline.py`**

```python
def test_is_loopback_accepts_localhost_and_rejects_remote():
    assert is_loopback_url("http://127.0.0.1:11434/v1")
    assert is_loopback_url("http://localhost:11434/v1")
    assert not is_loopback_url("https://api.x.ai/v1")
    assert not is_loopback_url("http://8.8.8.8:11434/v1")

def test_llm_chat_refuses_non_loopback_base():
    # Settings with api_base https://example.com/v1 → chat raises, message mentions loopback or airgap/local-only
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m unittest tests.test_offline -v`
Expected: FAIL (module/functions missing)

- [ ] **Step 3: Implement `engine/network_policy.py` and wire into config + llm**

`LLMClient.chat` calls `assert_local_llm_base` before `_post`. Settings load sets `airgap` from env.

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m unittest tests.test_offline tests.test_provider -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/network_policy.py engine/config.py engine/llm.py tests/test_offline.py
git commit -m "feat: loopback-only LLM network policy and airgap flag"
```

---

### Task 3: Offline brain inventory + health fields

**Files:**
- Create: `engine/brain_status.py`
- Modify: `engine/cli.py` (health), `engine/web.py` (snapshot), `engine/setup_local.py` (reuse models_dir/BRAINS)
- Test: `tests/test_offline.py` (extend)

**Interfaces:**
- Consumes: `models_dir()`, `BRAINS`, `local_reachable`, `Settings`
- Produces: `brain_status(settings: Settings) -> dict` with keys:
  - `gguf_present: bool`
  - `gguf_path: str | None`
  - `runner: str` (`"ollama"` | `"llama_cpp"` | `"none"`)
  - `offline_ready: bool`
  - `airgap: bool`
  - `network_mode: str`

- [ ] **Step 1: Write failing tests for `brain_status` and health JSON keys**

```python
def test_brain_status_reports_missing_gguf(tmp_path, monkeypatch): ...
def test_health_includes_offline_fields():
    # main(["health"]) JSON has offline_ready, gguf_present, network_mode, runner
```

- [ ] **Step 2: Run — expect FAIL**

Run: `python -m unittest tests.test_offline -v`
Expected: FAIL on missing keys/functions

- [ ] **Step 3: Implement `brain_status` and expose via health/snapshot**

- [ ] **Step 4: Run — expect PASS**

Run: `python -m unittest tests.test_offline tests.test_health -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/brain_status.py engine/cli.py engine/web.py tests/test_offline.py
git commit -m "feat: offline brain status in health"
```

---

### Task 4: In-process GGUF backend via optional llama_cpp

**Files:**
- Create: `engine/gguf_infer.py`
- Modify: `engine/llm.py` (`available`, `chat` fallback), `engine/setup_local.py` messaging
- Test: `tests/test_offline.py` (fake/stub llama path)

**Interfaces:**
- Consumes: `brain_status`, local GGUF path
- Produces:
  - `llama_cpp_available() -> bool`
  - `gguf_chat(messages: list[dict], *, model_path: Path, tools=None) -> dict` with `content` + `tool_calls`
  - `LLMClient.available` true when Ollama up **or** (GGUF present and llama_cpp available)
  - `LLMClient.chat` uses GGUF path when Ollama unreachable

- [ ] **Step 1: Write failing tests with a fake llama_cpp module injected on sys.modules**

```python
def test_llm_uses_gguf_when_ollama_down(fake_llama_cpp):
    # available True; chat returns content from fake; no non-loopback URL used
```

- [ ] **Step 2: Run — expect FAIL**

Run: `python -m unittest tests.TestOfflineGguf -v` (or tests in test_offline)
Expected: FAIL

- [ ] **Step 3: Implement `gguf_infer.py` + llm fallback**

Keep tools optional: if GGUF path cannot do tools, return text-only and rely on existing `_parse_text_tools`.

- [ ] **Step 4: Run full offline + provider suite**

Run: `python -m unittest tests.test_offline tests.test_provider tests.test_modes -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/gguf_infer.py engine/llm.py tests/test_offline.py
git commit -m "feat: optional in-process GGUF inference without Ollama daemon"
```

---

### Task 5: Offline educate path + identity sync

**Files:**
- Create: `engine/educate.py`
- Modify: `engine/cli.py` (educate command), `agent.py` COMMANDS, identity docs (`CONSTITUTION.md`, `PROMPT.md`, `README.md`, `manifest.json`)
- Test: `tests/test_offline.py`, `tests/test_modes.py` (identity bits)

**Interfaces:**
- Consumes: `improve.log`, `prefs`, `brain_status`
- Produces:
  - `educate_report(settings: Settings) -> dict` with `lessons`, `offline_ready`, `network_mode`, no remote fetches
  - CLI `educate` prints JSON

- [ ] **Step 1: Write failing test `test_educate_report_is_local_only`**

Assert report keys and that airgap educate does not call urllib to non-loopback (patch urlopen).

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement educate + CLI + identity wording for owned standalone offline LLM/ML agent**

- [ ] **Step 4: Run full suite**

Run: `python -m unittest discover -s tests -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add engine/educate.py engine/cli.py agent.py CONSTITUTION.md PROMPT.md README.md manifest.json tests/
git commit -m "feat: offline educate path and standalone ownership identity"
```
