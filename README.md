# Coding agent

A **separate local entity**. It does not use Grok unless you opt in. Default brain is **Ollama on this machine**, so you are not billed by xAI.

## Setup (once)

```bash
cd ~/coding-agent
python3 agent.py setup
```

That installs Ollama if needed and, **only if the brain is missing**, clones the GGUF from Hugging Face git (not xAI, not a paid API). If you already have the model, it will not download a second copy.

## Terminal (like Grok / Astra)

Already on disk. One-time: `./install-mythos.sh` puts `mythos` on your PATH.

```bash
mythos                 # interactive chat
mythos chat -r ~/some-project
mythos -r ~/some-project run "add tests"
mythos serve           # web desk http://127.0.0.1:8790
```

Local Ollama brain. **NO CHARGES** to xAI.

Preferences grow in `data/preferences.md` (`/prefer …` in chat). Speed check: `mythos bench`.

## Run

```bash
python3 agent.py serve --port 8790
python3 agent.py improve
python3 agent.py -r /real/project/path run "add tests"
```

Desk: http://127.0.0.1:8790

`improve` with no path scans this agent. Do not type `/path/to/other-agent` — that is not a real folder.

## Billing

| Provider | Env | Who gets paid |
| -------- | --- | ------------- |
| **local (only)** | `CODING_PROVIDER=local` | Nobody. Your electricity. |
| xAI | disabled | Standing order: **NO CHARGES**. `XAI_API_KEY` is ignored. This agent will not call `api.x.ai`. |

This Grok chat is a different product. Talking to me here still uses xAI. The coding-agent process does not — local Ollama only.
