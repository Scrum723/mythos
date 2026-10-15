# Mythos

Standalone agent. Copy this folder to a laptop, server, or container.

**Role:** Senior local coding agent combining Grok Build, Astra, and GPT-style strengths. Ships working code, not suggestions.

**Constraints:** Stay in project root. No secrets. Honesty first.

Autonomy default is 3: safe work runs; destructive actions wait for confirmation.

Default brain is **local Ollama** (no xAI billing). **NO CHARGES.**

## Run

```bash
cp .env.example .env   # local Ollama defaults; no XAI_API_KEY needed
python3 agent.py setup # only if the local brain is missing
python3 agent.py health
python3 agent.py -a 3 -r /path/to/project run "your task"
python3 agent.py chat -r /path/to/project
python3 agent.py serve --host 127.0.0.1 --port 8790
```

Desk: http://127.0.0.1:8790

If Ollama is not running, the agent refuses honestly instead of calling a paid API.

## Docker

```bash
docker build -t mythos .
docker run --rm -p 8790:8790 -e CODING_PROVIDER=local -v "$PWD":/workspace mythos
```

Do not publish port 8790 to the internet. There is no login.
