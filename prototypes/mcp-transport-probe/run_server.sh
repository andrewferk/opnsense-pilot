#!/bin/sh
# THROWAWAY: start the probe on loopback. Usage: run_server.sh <state-dir> [stateless: 1|0]
# <state-dir>/token is created if missing; requests are logged to <state-dir>/requests.jsonl.
set -eu
STATE="$1"
cd "$(dirname "$0")"
if [ ! -s "$STATE/token" ]; then
  python3 -c "import secrets; print(secrets.token_urlsafe(32))" > "$STATE/token"
  chmod 600 "$STATE/token"
fi
PILOT_MCP_TOKEN="$(cat "$STATE/token")"
PROBE_LOG="$STATE/requests.jsonl"
PROBE_STATELESS="${2:-1}"
export PILOT_MCP_TOKEN PROBE_LOG PROBE_STATELESS
mise exec uv@0.11.29 python@3.13.14 -- uv run uvicorn --factory probe_server:from_env \
  --host 127.0.0.1 --port 8765 --log-level warning
