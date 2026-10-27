#!/usr/bin/env bash
# Sample which cellular operator the on-board Wi-Fi egresses through, every 30 s.
# The router's public IP (from Cloudflare's trace) tells which modem carried the
# request; run alongside logger.sh, offset from the ping bursts. railcov.uplink
# maps each IP to an operator. Usage: uplink-logger.sh trips/<trip-id>/uplink.csv
CSV=${1:?usage: uplink-logger.sh <out.csv>}
[ -s "$CSV" ] || echo "czas_iso,ip,colo" > "$CSV"
sleep 12
while true; do
  r=$(curl -s -m 5 https://1.1.1.1/cdn-cgi/trace)
  ip=$(echo "$r" | sed -n 's/^ip=//p')
  colo=$(echo "$r" | sed -n 's/^colo=//p')
  echo "$(date -Iseconds),${ip:-},${colo:-}" >> "$CSV"
  sleep 30
done
