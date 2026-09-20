#!/bin/sh
# THROWAWAY: one headless Codex CLI run against the probe. ~/.codex/config.toml is not edited.
# Usage: run_codex.sh <state-dir> <label> [good|bad] [extra codex exec args ...]
set -eu
STATE="$1"; LABEL="$2"; TOKEN_KIND="${3:-good}"
shift 3 2>/dev/null || shift $#
if [ "$TOKEN_KIND" = good ]; then PILOT_MCP_TOKEN="$(cat "$STATE/token")"; else PILOT_MCP_TOKEN="wrong-token"; fi
export PILOT_MCP_TOKEN
mkdir -p "$STATE/cwd"
printf '{"marker":"%s"}\n' "$LABEL" >> "$STATE/requests.jsonl"
codex exec --skip-git-repo-check -s read-only -C "$STATE/cwd" \
  -c 'mcp_servers.pilot.url="http://127.0.0.1:8765/mcp"' \
  -c 'mcp_servers.pilot.bearer_token_env_var="PILOT_MCP_TOKEN"' \
  "$@" \
  "Use the MCP server named pilot. 1) Call its echo_inventory tool with name \"fw1\". 2) List its MCP resources and resource templates. 3) Read the resource pilot://probe/status. 4) Read the resource pilot://probe/items/42. Report every 'marker' value verbatim and the items list from the tool. If any step is impossible, say exactly which and why. Do not run shell commands." \
  > "$STATE/codex-$LABEL.out" 2> "$STATE/codex-$LABEL.stderr" < /dev/null || echo "codex exited $?"
printf '{"marker":"end %s"}\n' "$LABEL" >> "$STATE/requests.jsonl"
