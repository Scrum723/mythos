# Morning status — Mythos / coding-agent

Checked while you slept. **NO CHARGES.**

## Locked down
- `.env` has **no** `XAI_API_KEY` — local Ollama only (`qwen2.5-coder:7b` @ `127.0.0.1:11434`).
- Even `CODING_PROVIDER=xai` + `CODING_ALLOW_XAI=1` + a key still loads as **local** with an **empty** key and **no** `api.x.ai` base.
- `LLMClient.chat` still refuses any xAI path with **NO CHARGES**.
- Spawned children (including refreshed `agents/mythos/`) ship local `.env.example` — no grok / no API key required.
- Health: `provider=local`, `bills_xai=false`.
- Tests: **22 OK**.

## How to run (free)
```bash
cd ~/coding-agent
python3 agent.py health
mythos                 # or: python3 agent.py chat
mythos serve           # http://127.0.0.1:8790
```

If Ollama is down, the agent refuses honestly — it does **not** fall back to a paid API.
