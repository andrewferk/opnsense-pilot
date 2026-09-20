#!/bin/sh
# Print the guest's mutation-relevant state over the serial console.
#   guest_state.sh            state only
#   guest_state.sh start-cap  state, then start a WAN capture in the guest
#   guest_state.sh stop-cap   stop the capture, print it, then state
set -eu
PROBE="$HOME/.local/share/opnsense-pilot-probe"
. "$PROBE/credentials.env"
STATE='echo EPOCH $(date +%s); echo CONFIG_SHA $(sha256 -q /conf/config.xml); echo CONFIG_MTIME $(stat -f %m /conf/config.xml); echo BACKUPS $(ls /conf/backup | wc -l) NEWEST $(ls -t /conf/backup | head -1); echo CONFIGD_LINES $(wc -l < /var/log/configd/latest.log); echo AUDIT_LINES $(wc -l < /var/log/audit/latest.log); echo SYSTEM_LINES $(wc -l < /var/log/system/latest.log); echo PROCS $(ps -axo comm | sort | uniq -c | sort -rn | awk "{printf \"%s:%s \", \$2, \$1}")'
case "${1:-}" in
  start-cap) CMD="$STATE; rm -f /tmp/wan13.pcap; (nohup tcpdump -ni vtnet1 -w /tmp/wan13.pcap >/dev/null 2>&1 &) ; echo CAPTURE started" ;;
  stop-cap)  CMD="pkill -INT tcpdump; /bin/sleep 2; echo CAPTURE_BEGIN; tcpdump -ttnr /tmp/wan13.pcap 2>/dev/null | head -200; echo CAPTURE_END; $STATE" ;;
  file)      CMD="$(tr '\n' ' ' < "$2")" ;;
  *)         CMD="$STATE" ;;
esac
"$PROBE/console-run.exp" "$PROBE_ROOT_PASSWORD" "$CMD" 180
