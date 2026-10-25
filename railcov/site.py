"""GitHub Pages site: trip replay on a Leaflet map, ping chart, route strip and longest gaps.

Usage: python -m railcov.site  (reads trips/*/, writes site/trips.js and site/index.html from site/template.html)
"""
import glob
import json
import os
import shutil

from .data import load

ROW_KEYS = ("time", "ts", "km", "loss", "min", "avg", "max", "lat", "lon", "where", "grade", "pos_src", "excluded",
            "site_km", "site_op", "site_place")


def main():
    trips = []
    for d in sorted(glob.glob("trips/*/"), reverse=True):
        if not os.path.exists(os.path.join(d, "ping.csv")):
            continue
        trip, rows, sites, track = load(d)
        m = trip.meta
        step = max(1, len(track) // 2000)
        trips.append({
            "date": m["date"], "train": f"{m['train']['number']} {m['train']['name']}", "from": m["from"], "to": m["to"],
            "network": m["network"]["operator"],
            "stations": [{k: (round(s[k], 2) if k == "km" else s[k]) for k in ("name", "lat", "lon", "km", "arr", "dep")} for s in trip.stops],
            "rows": [{k: r[k] for k in ROW_KEYS} for r in rows],
            "sites": [{k: s[k] for k in ("lat", "lon", "op", "place", "bands")} for s in sites],
            "track": [[round(la, 5), round(lo, 5)] for _, la, lo in track[::step]],
        })
    os.makedirs("site", exist_ok=True)
    open("site/trips.js", "w").write("const TRIPS=" + json.dumps(trips, ensure_ascii=False, separators=(",", ":")) + ";")
    shutil.copy("site/template.html", "site/index.html")
    print(len(trips), "trips")


if __name__ == "__main__":
    main()
