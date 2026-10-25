"""Load a trip: ping rows enriched with position (GPS if available, else timetable), grade and nearest site."""
import csv
import json
import os
import xml.etree.ElementTree as ET
from bisect import bisect_left
from datetime import datetime

from .model import Trip, hav

GRADES = ["good", "weak", "bad", "dead"]
GRADE_PL = {"good": "dobre", "weak": "wahania", "bad": "słabe", "dead": "brak łącza", "excluded": "pominięty"}


def grade(loss, avg, mx):
    """Thresholds tuned for interactive use (SSH, calls)."""
    if loss >= 100:
        return "dead"
    if loss >= 30 or (avg or 0) >= 300:
        return "bad"
    if loss > 0 or (avg or 0) >= 100 or (mx or 0) > 200:
        return "weak"
    return "good"


def load_gpx(path):
    """-> sorted list of (unix time, lat, lon)."""
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    pts = []
    for p in ET.parse(path).getroot().iterfind(".//g:trkpt", ns):
        t = p.find("g:time", ns)
        if t is not None:
            pts.append((datetime.fromisoformat(t.text.replace("Z", "+00:00")).timestamp(), float(p.get("lat")), float(p.get("lon"))))
    return sorted(pts)


def gps_at(track, t, max_gap=90):
    i = bisect_left(track, (t,))
    if i == 0 or i == len(track):
        return None
    (t0, la0, lo0), (t1, la1, lo1) = track[i - 1], track[i]
    if t1 - t0 > max_gap:
        return None
    f = (t - t0) / (t1 - t0) if t1 > t0 else 0
    return la0 + (la1 - la0) * f, lo0 + (lo1 - lo0) * f


def load(trip_dir):
    trip = Trip(trip_dir)
    sites = []
    p = os.path.join(trip_dir, "bts.json")
    if os.path.exists(p):
        sites = json.load(open(p))["sites"]
    track = []
    if os.path.exists(os.path.join(trip_dir, "track.gpx")):
        track = load_gpx(os.path.join(trip_dir, "track.gpx"))
    rows = []
    for r in csv.DictReader(open(os.path.join(trip_dir, "ping.csv"))):
        t = datetime.fromisoformat(r["czas_iso"])
        ts = t.timestamp()
        loss = float(r["strata_proc"])
        mn, av, mx = (float(r[k]) if r[k] else None for k in ("min_ms", "avg_ms", "max_ms"))
        pos = trip.position(ts)
        g = gps_at(track, ts) if track else None
        lat, lon, src = (g[0], g[1], "gps") if g else (pos["lat"], pos["lon"], "rozkład")
        near = min(((hav((lat, lon), (s["lat"], s["lon"])), s) for s in sites), key=lambda x: x[0], default=None)
        excl = trip.is_excluded(ts)
        rows.append({
            "time": t.strftime("%H:%M:%S"), "ts": ts, "loss": loss, "min": mn, "avg": av, "max": mx,
            "km": round(pos["km"], 2), "where": pos["where"], "lat": round(lat, 5), "lon": round(lon, 5), "pos_src": src,
            "grade": "excluded" if excl else grade(loss, av, mx), "excluded": excl,
            "site_km": round(near[0], 2) if near else None, "site_op": near[1]["op"] if near else None,
            "site_place": near[1]["place"] if near else None,
        })
    return trip, rows, sites, track
