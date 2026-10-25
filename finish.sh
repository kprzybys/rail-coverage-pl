#!/usr/bin/env bash
# Rebuild everything for a trip after it ends: optional GPX import, base stations, report, images, site.
# Usage: ./finish.sh trips/<trip-id> [recording.gpx]
set -euo pipefail
cd "$(dirname "$0")"
TRIP=${1:?usage: finish.sh trips/<trip-id> [recording.gpx]}
if [ -n "${2:-}" ]; then
  python3 -m railcov.gpx "$TRIP" "$2"
fi
[ -f "$TRIP/bts.json" ] || python3 -m railcov.bts "$TRIP"
python3 -m railcov.report "$TRIP"
python3 -m railcov.promo "$TRIP"
python3 -m railcov.site
git status --short
