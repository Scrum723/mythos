# grok-game-mcp

A standalone **MCP server** for Grok-powered **game-asset generation** — sprites,
directional animation sheets, voiceover, SFX, and chiptune music. Extracted from the
`claude-mermaid-collab` dogfood into a self-contained project (only dependency on Grok is
an API key; rendering is pure-TS via **jimp** + **ffmpeg**, both bundled).

## Setup

```bash
bun install
export XAI_API_KEY=xai-...        # or put it in ./config.json or ~/.grok-game-mcp/config.json
```

Run the MCP server (stdio):

```bash
bun run src/server.ts            # artifacts → ./out (override with GROK_GAME_OUT)
```

Register it with any MCP client (e.g. Claude) as a stdio server running `bun run src/server.ts`.

## Tools

| Tool | What it makes |
| --- | --- |
| `generate_image` | a still image (Grok Imagine) |
| `generate_sprite_sheet` | directional animation sheet: `{character, animation, frames, angles}` → packed `[angles×frames]` transparent atlas + manifest + engine exports (Aseprite/Phaser/Godot) |
| `generate_voiceover` | Grok TTS (voices eve/ara/rex/sal/leo) + optional shared DSP preset |
| `generate_sfx` | retro SFX — Grok-text picks sfxr params → pure-JS synth |
| `generate_music` | loopable NES-style chiptune — Grok-text composes → pure-JS synth |
| `apply_audio_dsp` | apply a shared DSP/effect preset to any audio file (same presets for voice/SFX/music) |
| `list_dsp_presets` | the shared audio DSP presets |
| `generate_vfx` | effect animation sheet (explosion/spark/smoke) — chroma or luminance (glow) key |
| `generate_tileset` | seamless tileable tiles → tilesheet + Tiled/Godot manifest |
| `generate_background` | scene background; optional horizontal-seamless + transparent parallax layers |
| `define_character` / `generate_character_animations` | a reusable character (locked reference) → its whole animation set |
| `estimate_cost` | preview the USD cost of an op before running it |
| `replace_sheet_cell` | composite a replacement into one cell of a sheet (per-cell fixup) |
| `generate_game_pack` | **one brief → a whole cohesive asset pack** (style + characters + tiles + bg + SFX + music + VO); dry-run by default |
| `set_style` / `get_style` | the project style (palette + prompt fragment + voice) applied to every asset |

Music exports OGG/MP3/WAV (default OGG) + a `.mid` sidecar. Run `bun run preview` for a local
gallery (animate sheets, play audio, A/B the DSP presets).

## How it works (the patterns)

- **Grok decides, our code renders.** Grok generates the image/video/voice or, for SFX/music,
  the *parameters/score* (sfxr params, chiptune pattern); pure-TS synthesizes the audio.
- **Sprite sheets** use the turntable trick: a grid of frozen poses on cyan pedestals →
  one Grok-video orbit rotates every cell in place → frames keyed + sliced + packed.
- **Shared audio DSP** (ffmpeg filterchains) applies uniformly to voice, SFX, and music
  (epic-announcer, ice-demon, robot-8bit, bitcrush, …).

## Architecture

- `tooling/imagegen` — image/video/sprite pipeline (jimp + ffmpeg). Provider-agnostic, xAI-first.
- `tooling/audiogen` — TTS provider, sfxr synth, chiptune synth, shared DSP.
- `tooling/config.ts` — secret access (env → config.json).
- `src/core.ts` — standalone generators that write artifacts to `out/`.
- `src/server.ts` — the MCP server.

## Status

Full parity with the collab dogfood — all 14 tools ported to standalone `core` (write to
`out/`): image, sprite sheet, voiceover (+DSP), SFX, music, apply-audio-dsp, list-dsp-presets,
VFX, tileset, background, define-character, character-animations, estimate-cost,
replace-sheet-cell. `tsc` clean; image/sprite/TTS/SFX/music/tileset paths verified live.

Roadmap done: preview gallery, project-style cohesion, `generate_game_pack` meta-tool,
music OGG/MIDI export. Remaining: neural image→3D (the visual-hull spike — port the pure-TS
hull as an optional tool; hosted neural only if a 3D game needs it) and `--out` packaging
(per-asset folders, a pack index/zip).
