# Songstats for Gemini CLI and Grok Build

<img src="assets/icon.png" alt="Songstats" width="96" />

Official Songstats integration from The Stats Company. Ask questions about your
artists, labels, collaborators, and tracks through the Songstats MCP server.
The package includes the `songstats-music-analytics` skill and a remote MCP connection.

## Gemini CLI

```bash
gemini extensions install https://github.com/Songstats/songstats-ai-plugin
```

Review the extension's permissions when prompted. Start a new Gemini CLI session
and complete the Songstats OAuth sign-in when prompted. If needed, run
`/mcp auth songstats` inside Gemini CLI. Use `/mcp` to check the connection.

## Grok Build

Install from this source repository while marketplace review is pending:

```bash
grok plugin install Songstats/songstats-ai-plugin --trust
```

The `--trust` option enables this plugin's skill and MCP connection; review the
source before granting trust. Restart the session or refresh the Plugins tab,
then use `/mcps` to complete OAuth sign-in and check the connection.

## Try it

> Summarize the first artist I can access and explain their Spotify growth over the last 30 days.

## Access and data handling

- Requires eligible Songstats subscription access or an eligible Enterprise API agreement.
- Uses the HTTPS MCP endpoint `https://api.songstats.com/mcp` and the OAuth
  authorization, registration, token, and revocation endpoints under
  `https://api.songstats.com/oauth/`. Sign-in and consent use `songstats.com`.
- Requests only `mcp:read` and `enterprise:read`. The client stores its OAuth
  credentials; this package includes no credentials and does not request an API key.
- Analytics access is limited to the profiles, sources, and data your account
  can access. Existing subscription, source-authorization, and usage limits apply.
- Reads retain normal request, search, and object accounting. The package does
  not expose catalog edits, provider-authorization changes, or Enterprise API writes.
- No executable helpers, dependencies, hooks, local file access, or separate
  telemetry are included. The AI client handles transport and OAuth.

[Documentation](https://developers.stats.company/mcp?product=songstats) ·
[Support](https://help.songstats.com) ·
[Privacy](https://songstats.com/privacy-policy) ·
[Terms](https://songstats.com/terms-of-service)

## Maintenance

Both client manifests must keep the same product endpoint and read-only scopes.
The shared `skills/songstats-music-analytics/SKILL.md` is used by both clients; changes must be
compatible with both. Runtime tool schemas and access rules come from the MCP
server. Bump both manifest versions together for a release. Gemini discovers
this repository through its `gemini-cli-extension` topic; Grok marketplace
updates must pin the published commit and regenerate the marketplace index.

## License

MIT. See [LICENSE](LICENSE). The license covers this package; service access
remains subject to the linked product terms.
