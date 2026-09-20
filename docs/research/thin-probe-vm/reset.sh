#!/bin/sh
# Cold-reset the probe VM.
#   reset.sh            back to the configured checkpoint (run/configured.qcow2), if one exists
#   reset.sh factory    back to the pristine, never-booted 26.7 nano image
PROBE="$HOME/.local/share/opnsense-pilot-probe"
"$PROBE/stop.sh" 5
rm -f "$PROBE/run/probe.qcow2" "$PROBE/run/serial.log"
if [ "${1:-}" != "factory" ] && [ -f "$PROBE/run/configured.qcow2" ]; then
  cp "$PROBE/run/configured.qcow2" "$PROBE/run/probe.qcow2"
  echo "reset to configured checkpoint; run start.sh"
else
  echo "reset to factory image; run start.sh (a fresh overlay is created)"
fi
