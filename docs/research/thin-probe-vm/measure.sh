#!/bin/sh
# Smoke-test both API keys and measure per-call latency (10 sequential calls each, new TLS connection per call).
PROBE="$HOME/.local/share/opnsense-pilot-probe"
. "$PROBE/credentials.env"

call() { # user-label key secret path
  printf '%-9s %-46s ' "$1" "$4"
  i=0; codes=""; times=""
  while [ $i -lt 10 ]; do
    out=$(curl -sk -u "$2:$3" -o /dev/null -w '%{http_code} %{time_total}' "$PROBE_URL/api/$4")
    codes="$codes ${out% *}"; times="$times ${out#* }"; i=$((i + 1))
  done
  echo "$codes" | tr ' ' '\n' | sort -u | tr '\n' ' '
  echo "$times" | tr ' ' '\n' | grep . | sort -n | awk '{a[NR]=$1} END {printf "min=%.3fs median=%.3fs max=%.3fs\n", a[1], a[int((NR+1)/2)], a[NR]}'
}

for p in diagnostics/system/system_information core/firmware/status interfaces/overview/interfaces_info firewall/alias/search_item auth/user/search; do
  call admin "$PROBE_ADMIN_API_KEY" "$PROBE_ADMIN_API_SECRET" "$p"
  call readonly "$PROBE_READONLY_API_KEY" "$PROBE_READONLY_API_SECRET" "$p"
done
printf 'no-auth   %-46s ' diagnostics/system/system_information
curl -sk -o /dev/null -w '%{http_code}\n' "$PROBE_URL/api/diagnostics/system/system_information"
