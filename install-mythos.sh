#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$ROOT/mythos" "$ROOT/agent.py" "$ROOT/start-desk.command"
DEST="/opt/homebrew/bin/mythos"
if [ ! -d /opt/homebrew/bin ]; then
  DEST="/usr/local/bin/mythos"
fi
ln -sf "$ROOT/mythos" "$DEST"
echo "Installed: $DEST"
echo "Try:  mythos"
echo "Chat: mythos chat -r ~/your-project"
echo "NO CHARGES — local Ollama, not xAI."
