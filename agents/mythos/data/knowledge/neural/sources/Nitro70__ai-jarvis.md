# Jarvis

A real, working voice assistant for your PC. Talk to it like JARVIS from Iron Man — play music, open apps, control windows, look things up — without giving up control of your system.

- Modular: pick your LLM (Claude subscription, Anthropic API, OpenAI, xAI/Grok, local LM Studio…), pick your tools, pick voice or text mode.
- Safe by design: every capability is a small, typed tool. There is no `run_arbitrary_shell_command` tool. The worst misunderstanding opens the wrong app — it can't delete your files.
- Local speech-to-text (Whisper) and free high-quality text-to-speech (Edge TTS). No paid subscription required for the audio layer.
- Wake-word activated ("Jarvis…") with auto-endpoint detection — no push-to-talk.

---

## Quick start

```bash
git clone https://github.com/your-username/jarvis
cd jarvis

# Pick the install profile that matches what you want
pip install -r requirements.txt              # core only (text mode, no tools)
pip install -r requirements-voice.txt        # adds wake word + STT + TTS
pip install -r requirements-music.txt        # adds YouTube Music control
pip install -r requirements-all.txt          # everything

# Configure
cp config.example.yaml config.yaml
# edit config.yaml — pick LLM backend, paste API keys, enable tools

# Run
python jarvis.py
```

First run with voice mode will download the Whisper models (~75-150MB, one time).

---

## LLM backends

Configure under `llm.backend` in `config.yaml`. Pick one:

### `claude_agent` — Claude with your Claude subscription, no API key

Uses the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Requires that Claude Code is installed and logged in on your machine — auth flows through your Claude Pro/Max plan. **No API spending.**

```yaml
llm:
  backend: claude_agent
  model: claude-sonnet-4-6
```

### `claude_api` — Anthropic API with a key

Standard Anthropic API. Pay per token. Get a key at [console.anthropic.com](https://console.anthropic.com).

```yaml
llm:
  backend: claude_api
  model: claude-sonnet-4-6
  api_key: ${ANTHROPIC_API_KEY}   # or paste the key directly
```

### `openai_compat` — OpenAI, xAI/Grok, Groq, OpenRouter, LM Studio, Ollama

Anything that speaks the OpenAI Chat Completions API. Set `base_url` and `api_key`. Examples:

```yaml
# OpenAI
llm:
  backend: openai_compat
  base_url: https://api.openai.com/v1
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o-mini

# xAI / Grok
llm:
  backend: openai_compat
  base_url: https://api.x.ai/v1
  api_key: ${XAI_API_KEY}
  model: grok-4

# Groq (fast inference, free tier)
llm:
  backend: openai_compat
  base_url: https://api.groq.com/openai/v1
  api_key: ${GROQ_API_KEY}
  model: llama-3.3-70b-versatile

# Local LM Studio / Ollama
llm:
  backend: openai_compat
  base_url: http://localhost:1234/v1
  api_key: not-needed
  model: your-local-model-name
```

> The `${ENV_VAR}` syntax pulls from environment variables. Put your keys in a `.env` file (gitignored) or your shell profile.

---

## Tools

Each tool module is independently enableable in `config.yaml`. Off by default if its dependencies aren't installed.

| Tool | What it does | Needs |
|---|---|---|
| `system_info` | Time, date, weather (wttr.in, no key) | — |
| `web_browser` | Open URLs, search/play YouTube videos | `yt-dlp` for video search |
| `music_ytmd` | YouTube Music control (play/pause/next/queue/volume) | YT Music desktop app — see below |
| `windows_apps` | Launch any app installed in your Start Menu | Windows |
| `windows_state` | Minimize/maximize/close/focus windows | Windows |

### Setting up `music_ytmd`

YouTube Music control uses the unofficial [th-ch/youtube-music](https://github.com/th-ch/youtube-music) desktop app, which exposes a local HTTP API.

1. **Download** the latest Windows portable from [their releases](https://github.com/th-ch/youtube-music/releases) — pick the `YouTube-Music-X.Y.Z.exe` file (single binary, no installer).
2. **Launch it** and sign in with your Google account. YouTube Premium works automatically.
3. **Enable the API plugin**: ≡ menu → Plugins → toggle on **API Server**.
4. **Fully quit** the app (right-click tray icon → Quit) and relaunch — the plugin needs a restart to start its server.
5. In `config.yaml`:
   ```yaml
   tools:
     music_ytmd:
       enabled: true
       # Optional: path to youtube-music.exe so Jarvis can auto-launch it.
       # Leave null and start it manually if you prefer.
       exe_path: C:\path\to\youtube-music.exe
   ```
6. First time Jarvis tries to use it, a dialog appears in the YT Music app asking to authorize "jarvis" — click **Allow**. The token gets saved to `.ytmd_token` (gitignored) and reused.

---

## Persistent memory (`memory.md`)

Jarvis can remember things about you across sessions via a plain markdown file.

**Setup** — copy the template and edit:

```bash
cp memory.example.md memory.md
```

The example file has placeholder facts wrapped in HTML comments:

```markdown
<!-- - My name is [your name]. -->
<!-- - Address me as "[sir / ma'am / their name / etc.]". -->
<!-- - I prefer [coffee / tea] in the morning. -->
```

To activate one, delete the surrounding `<!--` and `-->` and fill in your info:

```markdown
- My name is Alex.
- Address me as "sir".
- I prefer coffee in the morning.
```

Anything still inside `<!-- ... -->` comments is **never sent to the LLM** — they're just templates.

**Auto-learning** — when you share something worth remembering ("by the way, my dog's name is Max", "I always go to bed at midnight"), Jarvis calls the `remember` tool and appends the fact to a `# Learned` section at the bottom of `memory.md`. You can edit or delete anything in there at any time — it's just plain text. The tool is idempotent: it won't add the same fact twice.

**Forgetting** — ask Jarvis to forget something ("forget what I said about pizza"), and it'll remove matching entries from the Learned section. Your hand-written sections at the top are never touched by tools.

**Privacy** — `memory.md` is gitignored. Only you (and Jarvis at runtime) ever see it.

Disable by removing `persona.memory_file` from `config.yaml`, or by setting `tools.memory.enabled: false` (which keeps reading the file but doesn't let Jarvis write to it).

---

## Voice settings

```yaml
voice:
  # Wake word — Jarvis listens for this between commands.
  wake_word: jarvis

  # Mishearings to also count as the wake word. Whisper often hears "jarvis"
  # as one of these. Trade-off: bigger list = more responsive but more false
  # triggers from normal speech.
  wake_word_variants: [jarvis, jervis, service, travis]

  # How long of silence ends a command (after you've started speaking).
  silence_end_seconds: 2.5

  # Hard cap on a single command's length.
  max_command_seconds: 30

  stt:
    # Whisper model for command transcription. Bigger = more accurate, slower.
    # tiny.en (~40MB) | base.en (~75MB) | small.en (~250MB) | medium.en (~770MB)
    model: base.en

    # Separate smaller model used only for wake-word detection. Runs constantly
    # so smaller is better. tiny.en is the sweet spot.
    wake_model: tiny.en

  tts:
    enabled: true
    # Edge TTS voice. Run `edge-tts --list-voices` to see all options.
    # British male: en-GB-RyanNeural, en-GB-ThomasNeural
    # American: en-US-GuyNeural, en-US-AndrewNeural
    voice: en-GB-RyanNeural
```

---

## Text mode (no microphone needed)

You type a message, Jarvis answers in text **and speaks the reply aloud**. No wake word, no microphone, no Whisper models — just typing.

Good when:
- You don't have a microphone, or it's broken, or it's a desktop without one
- You're somewhere you can't talk (library, office, late at night)
- You're testing a new tool or LLM backend and want quick iteration
- You're SSH'd into a remote machine that has no mic but does have speakers
- Voice mode just isn't working and you need to use Jarvis right now

### Three ways to turn it on

**1. Make text mode the default** — edit `config.yaml`:

```yaml
mode: text
```

**2. Override at launch** — keep your config on voice, flip to text for one session:

```bash
python jarvis.py --text
```

The flag wins over whatever's in the config. Useful when your mic is misbehaving and you want to fall back without editing files.

**3. The opposite** — if your config defaults to text:

```bash
python jarvis.py --voice
```

### Spoken replies in text mode

By default, replies are both **printed and spoken** — you type, you read the answer, you also hear it. To silence the speaking and keep replies text-only:

```bash
python jarvis.py --text --no-tts
```

Or permanently in `config.yaml`:

```yaml
voice:
  tts:
    enabled: false
```

`--no-tts` also works in voice mode (mic stays on, just no spoken replies).

### What you actually need to install for text mode

Bare minimum for text-only with a hosted LLM backend:

```bash
pip install -r requirements.txt        # pyyaml + httpx
pip install -r requirements-llm.txt    # the SDK for your backend
```

That's it. No `faster-whisper`, no `sounddevice`, no `numpy`, no `pygame`. If you also want spoken replies, add:

```bash
pip install edge-tts pygame
```

(those two specific packages — you don't need the whole voice profile).

If voice deps aren't installed and you try to launch voice mode, you get a friendly error pointing you at `--text` instead of a crash.

### Quick start, text-only path

```bash
git clone https://github.com/Nitro70/ai-jarvis
cd ai-jarvis
pip install -r requirements.txt -r requirements-llm.txt edge-tts pygame
cp config.example.yaml config.yaml
# edit config.yaml — set mode: text, pick an LLM backend, paste API key
python jarvis.py
```

You should be talking (well, typing) to Jarvis within five minutes.

---

## File layout

```
jarvis/
├── jarvis.py              ← entry point
├── config.example.yaml    ← copy to config.yaml and edit
├── core/                  ← config loader, tool registry, logging
├── llm/                   ← LLM backend implementations
├── tools/                 ← each tool module is independently enableable
└── voice/                 ← STT (Whisper) and TTS (Edge TTS)
```

---

## Adding your own tool

Create `tools/my_tool.py`:

```python
from core.tools import Tool


async def hello(args: dict) -> str:
    return f"Hello, {args['name']}!"


def get_tools(config: dict) -> list[Tool]:
    if not config.get("enabled", True):
        return []
    return [
        Tool(
            name="say_hello",
            description="Say hello to a person by name.",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            handler=hello,
        ),
    ]
```

Add it to `config.yaml`:

```yaml
tools:
  my_tool:
    enabled: true
```

That's it — the tool is now visible to Jarvis across every LLM backend.

---

## Safety model

By default, every tool is a typed function with a narrow input schema. There is no `eval`, no shell, no `run_command`. File ops are not exposed by any built-in tool. `windows_state.close_window` calls Windows' `WM_CLOSE` — exactly what clicking the X does, including the "unsaved work?" prompt. `open_url` only allows `http://` and `https://`. `open_app` only launches apps Windows already says are installed in the Start Menu.

The worst-case for a mistranscribed command in the default configuration is "Jarvis opened the wrong app." That's by design.

You can give Jarvis genuine shell access if you want to — see **Danger Zone** below — but it's off by default and double-gated by config flags.

---

## Danger Zone — unrestricted system access

> **⚠️ Read this whole section before enabling.** Once on, the LLM can run arbitrary commands and read/write any file. A misheard "delete that test folder" could become `Remove-Item C:\Users\you\Documents -Recurse -Force`. Prompt-injection attacks from untrusted content (a webpage Jarvis reads, an email title, a song title even) 

<!-- truncated for Mythos neural library -->
