#!/bin/sh
# THROWAWAY: one headless Claude Code run against the probe.
# Usage: run_claude.sh <state-dir> <label> [good|bad] [VAR=value ...]
set -eu
STATE="$1"; LABEL="$2"; TOKEN_KIND="${3:-good}"
shift 3 2>/dev/null || shift $#
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ "$TOKEN_KIND" = good ]; then PILOT_MCP_TOKEN="$(cat "$STATE/token")"; else PILOT_MCP_TOKEN="wrong-token"; fi
export PILOT_MCP_TOKEN
for kv in "$@"; do export "$kv"; done
mkdir -p "$STATE/cwd"
cd "$STATE/cwd"
printf '{"marker":"%s"}\n' "$LABEL" >> "$STATE/requests.jsonl"
claude -p "Use the MCP server named pilot. 1) Call its echo_inventory tool with name \"fw1\". 2) List its MCP resources. 3) Read the resource pilot://probe/status. 4) Read the resource pilot://probe/items/42. Report every 'marker' value verbatim and the items list from the tool. If any step is impossible, say exactly which and why. Do not use any other tools." \
  --mcp-config "$HERE/claude.mcp.json" --strict-mcp-config \
  --allowedTools "mcp__pilot,ListMcpResourcesTool,ReadMcpResourceTool" \
  --output-format json --debug-file "$STATE/claude-$LABEL.debug.log" \
  > "$STATE/claude-$LABEL.json" 2> "$STATE/claude-$LABEL.stderr" || echo "claude exited $?"
printf '{"marker":"end %s"}\n' "$LABEL" >> "$STATE/requests.jsonl"
