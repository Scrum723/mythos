# Wavemaker for AI agents

[Wavemaker](https://wavemaker.io) is a complete creative studio your agent can use. Ask for a
product video, a set of ad images, a jingle, a voiceover, sound effects or a full HTML5 banner
set, and Wavemaker writes, designs, shoots, scores and edits it, then checks the result against
the spec of where it is going (YouTube, TikTok, Instagram, Meta, Google Ads, IAB display).

This repository holds Wavemaker's plugin for every agent host. They all connect the same remote
MCP server and carry the same skill:

| Setting | Value |
| --- | --- |
| MCP server | `https://api.wavemaker.io/mcp` (Streamable HTTP) |
| Sign-in | OAuth 2.1 with PKCE; dynamic client registration and client ID metadata documents; scopes `read run write` |
| Without OAuth | `Authorization: Bearer <workspace key>` from the Wavemaker web app |
| Registry name | `io.wavemaker/wavemaker` on the [official MCP Registry](https://registry.modelcontextprotocol.io) |

There is no key or secret in this repository. Sign-in opens a browser page; a new account is
free at [wavemaker.io](https://wavemaker.io). Generation spends your workspace's credits, and
the agent prices work before spending it.

## Install

**Claude Code**

```sh
/plugin install wavemaker --marketplace AdwaveInc/wavemaker-plugins
```

Or `claude plugin marketplace add AdwaveInc/wavemaker-plugins` then
`claude plugin install wavemaker@adwave`. Run `/mcp` and choose **Authenticate** once.

**Claude (web, desktop, mobile)**: Customize → Connectors → Add custom connector →
`https://api.wavemaker.io/mcp`.

**ChatGPT**: Plugins → + → Add custom MCP server → `https://api.wavemaker.io/mcp`, OAuth.

**Codex**

```sh
codex plugin marketplace add AdwaveInc/wavemaker-plugins
```

then install **Wavemaker** from `/plugins`. MCP only: `codex mcp add wavemaker --url
https://api.wavemaker.io/mcp` and `codex mcp login wavemaker`.

**Cursor and Grok Bot**: install **Wavemaker** from the Cursor Marketplace (Settings →
Plugins). The MCP server alone installs from the deeplink
`cursor://anysphere.cursor-deeplink/mcp/install?name=wavemaker&config=eyJ1cmwiOiJodHRwczovL2FwaS53YXZlbWFrZXIuaW8vbWNwIn0=`.
For a local copy: `ln -s "$PWD" ~/.cursor/plugins/local/wavemaker` and reload the window.

**Grok Build**: install **wavemaker** from the xAI plugin marketplace. Grok Build reads this
repository's root `plugin.json` and `.mcp.json`.

**Gemini CLI**

```sh
gemini extensions install https://github.com/AdwaveInc/wavemaker-plugins
```

**VS Code and GitHub Copilot**: search `@mcp wavemaker` in Extensions, or

```sh
code --add-mcp '{"name":"wavemaker","type":"http","url":"https://api.wavemaker.io/mcp"}'
```

**OpenClaw**

```sh
openclaw mcp add wavemaker --url https://api.wavemaker.io/mcp --transport streamable-http
openclaw mcp login wavemaker
openclaw skills install wavemaker      # the skill, from ClawHub
```

**Hermes Agent**: add to `~/.hermes/config.yaml`, then `hermes mcp login wavemaker`:

```yaml
mcp_servers:
  wavemaker:
    url: https://api.wavemaker.io/mcp
    auth: oauth
```

and the skill with `hermes skills tap add AdwaveInc/wavemaker-plugins`.

**Any other skill-aware agent**: `npx skills add AdwaveInc/wavemaker-plugins`.

**Windsurf, Zed, Cline, Goose, Kiro and other MCP hosts**: add the server URL above as a
remote (Streamable HTTP) server. A host that only runs local servers can use
`npx -y mcp-remote https://api.wavemaker.io/mcp`.

## What's inside

| Path | For |
| --- | --- |
| `plugin.json`, `mcp.json` | [Agent Plugins 1.0](https://agent-plugins.org): Codex and ChatGPT (with `extensions.com.openai`), Cursor, Kiro, Grok Build |
| `.cursor-plugin/plugin.json` | Cursor Marketplace and Grok Bot |
| `.claude-plugin/`, `.mcp.json` | Claude Code plugin and the `adwave` marketplace (also Copilot CLI, OpenClaw bundles) |
| `.agents/plugins/marketplace.json` | Codex repo marketplace |
| `gemini-extension.json` | Gemini CLI extension |
| `server.json` | Official MCP Registry entry |
| `skills/wavemaker/SKILL.md` | The [Agent Skill](https://agentskills.io) every host loads: when to use Wavemaker and how to drive its twelve tools |
| `llms-install.md` | Install steps for agents that install servers themselves (Cline) |

The server also publishes an [MCP Server Card](https://api.wavemaker.io/mcp/server-card) and
an [AI Catalog](https://wavemaker.io/.well-known/ai-catalog.json).

## Try it

- "Make a 15-second vertical product video for https://example.com"
- "Design display banners for this campaign in the standard IAB sizes"
- "Write and produce a 30-second jingle with a voiceover, then check its loudness for YouTube"

## Develop

`node scripts/validate.mjs` checks every manifest against its host's rules and that they agree
on name, version and server URL. `claude plugin validate --strict .` and
`mcp-publisher validate` check the Claude and registry manifests. Releases bump `version` in
every manifest together (see [CHANGELOG.md](CHANGELOG.md)).

Docs: [connect an agent](https://wavemaker.io/docs/mcp) · [help](https://wavemaker.io/help) ·
[privacy](https://wavemaker.io/privacy) · [terms](https://wavemaker.io/terms) · support@adwave.com

## License

MIT, © Adwave. Copies published to ClawHub are distributed under MIT-0, as ClawHub requires.
