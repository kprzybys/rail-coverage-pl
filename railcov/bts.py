"""Base stations near the route from the UKE radio permit lists (bip.uke.gov.pl).

Usage: python -m railcov.bts trips/<trip-id> [--date 2026-09-25] [--corridor-km 8]
Downloads the LTE/5G xlsx files into cache/uke/, keeps Orange and T-Mobile sites
(they share sites through the NetWorkS! joint venture), merges permits per location
and writes trips/<trip-id>/bts.json.
"""
import argparse
import glob
import json
import os
import re
import urllib.request

import openpyxl

from .model import Trip

BASE = "https://bip.uke.gov.pl/download/gfx/bip/pl/defaultaktualnosci/140/12/99/{band}_-_stan_na_{date}.xlsx"
BANDS = ["lte800", "lte1800", "lte2100", "lte2600", "5g2100"]
OPS = {"Orange Polska S.A.": "Orange", "T-Mobile Polska S.A.": "T-Mobile",
       "P4 Sp. z o.o.": "Play", "Polkomtel Sp. z o.o.": "Plus"}


def dms(s):
    m = re.match(r"(\d+)[EN](\d+)'(\d+)", s)
    return int(m[1]) + int(m[2]) / 60 + int(m[3]) / 3600


def fetch(date, cache):
    os.makedirs(cache, exist_ok=True)
    for band in BANDS:
        dst = os.path.join(cache, f"{band}_{date}.xlsx")
        if not os.path.exists(dst):
            req = urllib.request.Request(BASE.format(band=band, date=date), headers={"User-Agent": "rail-coverage-pl"})
            with urllib.request.urlopen(req, timeout=300) as r, open(dst + ".part", "wb") as f:
                f.write(r.read())
            os.rename(dst + ".part", dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trip_dir")
    ap.add_argument("--date", default="2026-09-25", help="'stan na' date of the UKE lists")
    ap.add_argument("--corridor-km", type=float, default=8)
    ap.add_argument("--operators", default="Orange,T-Mobile")
    a = ap.parse_args()
    trip, keep = Trip(a.trip_dir), set(a.operators.split(","))
    cache = os.path.join("cache", "uke")
    fetch(a.date, cache)
    sites = {}
    for f in sorted(glob.glob(os.path.join(cache, f"*_{a.date}.xlsx"))):
        band = os.path.basename(f).split("_")[0].upper()
        for r in openpyxl.load_workbook(f, read_only=True).worksheets[0].iter_rows(min_row=2, values_only=True):
            op = OPS.get(r[0])
            if op not in keep:
                continue
            lat, lon = dms(r[5]), dms(r[4])
            d = trip.dist_to_route(lat, lon)
            if d > a.corridor_km:
                continue
            s = sites.setdefault((op, round(lat, 4), round(lon, 4)),
                                 {"lat": round(lat, 5), "lon": round(lon, 5), "op": op, "bands": set(), "place": r[6], "dist_km": round(d, 2)})
            s["bands"].add(band)
    out = [{**s, "bands": sorted(s["bands"])} for s in sites.values()]
    json.dump({"source": f"UKE, wykaz pozwoleń radiowych, stan na {a.date}", "sites": out},
              open(os.path.join(a.trip_dir, "bts.json"), "w"), ensure_ascii=False, indent=0)
    print(len(out), "sites")


if __name__ == "__main__":
    main()
