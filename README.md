# Mythos

Owner-controlled standalone intelligence for **coding**, **generative**, **creative**, **local LLM/ML**, and **defense**.
**Standalone stage needs no model** — tools, knowledge library, and defense run locally with zero LLM dependency.
Optional **Ollama** / **GGUF** only upgrades free-form generation quality.
**NO CHARGES** to xAI. Never calls `api.x.ai`.

```bash
python3 agent.py health      # offline_ready, runner, gguf_present
python3 agent.py educate     # local teaching report (no remote fetches)
python3 agent.py knowledge   # coding + spoken-language library + defense posture
python3 agent.py agency status
python3 agent.py agency self-prompt "review defense posture"
set MYTHOS_AIRGAP=1          # refuse remote model pulls
```

Local knowledge lives in `data/knowledge/` (coding cards, ISO spoken-language catalog, combined capabilities). Mythos synthesizes coding/generative/creative/defense into one **local** unit — it does not merge proprietary cloud model weights.

## Setup (once)

```bash
cd ~/mythos
python3 agent.py setup
```

That installs Ollama if needed and, **only if the brain is missing**, clones the GGUF from Hugging Face git (not xAI, not a paid API). If you already have the model, it will not download a second copy.

## Modes

| Command | Mode | Behavior |
| ------- | ---- | -------- |
| `run` / default desk | `code` | Explore, implement, verify |
| `create` | `create` | Generative / creative — no forced code-explore cycle |
| `chat` | `chat` | Interactive conversation |

## Terminal

Already on disk. One-time: `./install-mythos.sh` puts `mythos` on your PATH.

```bash
mythos                 # interactive chat
mythos chat -r ~/some-project
mythos -r ~/some-project run "add tests"
mythos create "write a short myth about a river AI"
mythos -r ~/some-project run --mode create "draft release notes in a playful tone"
mythos serve           # web desk http://127.0.0.1:8790
```

Local Ollama brain. **NO CHARGES** to xAI.

Preferences grow in `data/preferences.md` (`/prefer …` in chat). Speed check: `mythos bench`.

## Run

```bash
python3 agent.py serve --port 8790
python3 agent.py improve
python3 agent.py -r /real/project/path run "add tests"
python3 agent.py create "invent three product names for a weather agent"
```

Desk: http://127.0.0.1:8790

`improve` with no path scans this agent. Do not type `/path/to/other-agent` — that is not a real folder.

## Billing

| Provider | Env | Who gets paid |
| -------- | --- | ------------- |
| **local (only)** | `CODING_PROVIDER=local` | Nobody. Your electricity. |
| xAI | disabled | Standing order: **NO CHARGES**. `XAI_API_KEY` is ignored. This agent will not call `api.x.ai`. |

Talking to cloud Grok is a different product. The Mythos process does not use it — local Ollama only.
