#!/bin/sh
# Stop the probe VM. Asks the guest to power down over QMP (ACPI), then falls back to killing QEMU.
PROBE="$HOME/.local/share/opnsense-pilot-probe"
PID="$(cat "$PROBE/run/qemu.pid" 2>/dev/null)" || { echo "not running"; exit 0; }

printf '%s\n' '{"execute":"qmp_capabilities"}' '{"execute":"system_powerdown"}' | nc -U -w 2 "$PROBE/run/qmp.sock" >/dev/null 2>&1

i=0
while kill -0 "$PID" 2>/dev/null && [ "$i" -lt "${1:-120}" ]; do sleep 1; i=$((i + 1)); done
if kill -0 "$PID" 2>/dev/null; then echo "guest did not power down; killing QEMU"; kill "$PID"; fi
rm -f "$PROBE/run/qemu.pid" "$PROBE/run/serial.sock" "$PROBE/run/qmp.sock"
echo stopped
