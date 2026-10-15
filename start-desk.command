#!/bin/bash
cd "$(dirname "$0")"
exec python3 agent.py serve --host 127.0.0.1 --port 8790
