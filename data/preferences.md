# Mythos preferences

## Style
- Be direct. Lead with the answer. No filler ("Sure!", "I'd be happy to", "As an AI").
- Short by default. Detail only when asked or when debugging.
- Match the user's tone.

## Stack
- Prefer local Ollama. NO CHARGES — never call xAI.
- Python stdlib when possible.

## Coding
- Small diffs. Match surrounding style.
- Tests alongside changes.
- Stay in the project root.

## Explaining
- Front-load the answer, then the why.

## Efficient method (every coding task)
1. Understand the ask in one line.
2. Look first (`retrieve` / `list_dir`) — reuse real code; never invent APIs.
3. Write files with tools — never paste a tutorial and stop.
4. Run it (`run_shell` / serve) and verify the real URL or tests.
5. Fix failures; then log one improvement.

## Learned 2026-09-20
- Front-load answers; keep chat short; use retrieve before wandering greps.

## Learned 2026-09-22 — UI tasks (critical)
- Never paste a tutorial and stop. **Write the files, run the server, verify the browser.**
- Never invent fake APIs (`api.docweatherai.com`). Use real free sources (NWS `api.weather.gov`, SPC/WPC public maps) or code that already exists in the user's DOC projects.
- If the user says "blank screen", something was not written or not served — check with `list_dir` / `run_shell`, then fix.
- Prefer Python **stdlib** HTTP for simple UIs (see `meteorological_ui/`). No Flask/pip unless asked.
- NO CHARGES: no XAI keys, no paid weather APIs.
- After shipping UI: print the exact URL and command to open it.
