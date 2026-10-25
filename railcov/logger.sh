#!/usr/bin/env bash
# Ping logger for a train trip: every 30 s sends 10 pings and appends one CSV row.
# Usage: railcov/logger.sh trips/<trip-id>/ping.csv [target]
# Do not download anything else over the same link while measuring: it saturates
# the mobile uplink queue and shows up as fake dead zones.
set -u
CSV=${1:?usage: logger.sh <out.csv> [target]}
TARGET=${2:-1.1.1.1}
[ -s "$CSV" ] || echo "czas_iso,strata_proc,min_ms,avg_ms,max_ms" > "$CSV"
while true; do
  t=$(date -Iseconds)
  r=$(ping -c 10 -i 0.3 -q -W 2 "$TARGET" 2>&1)
  loss=$(echo "$r" | grep -oP '[0-9.]+(?=% packet loss)')
  rtt=$(echo "$r" | grep -oP 'rtt [^=]+= \K[0-9.]+/[0-9.]+/[0-9.]+' | tr / ,)
  echo "$t,${loss:-100},${rtt:-,,}" >> "$CSV"
  sleep 27
done
