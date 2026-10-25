"""Train position from the timetable: linear interpolation by distance along the station polyline.

Without GPS this is the best guess: constant speed between timed stops, straight lines
between consecutive stations (passed-through stations add shape). Accuracy: a few km.
"""
import json
import math
import os
from datetime import datetime


def hav(a, b):
    """Great-circle distance in km between (lat, lon) pairs."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def seg_dist(p, a, b):
    """Distance in km from point p to segment a-b (local flat projection)."""
    kx, ky = 111.32 * math.cos(math.radians(p[0])), 110.57
    ax, ay, bx, by, px, py = a[1] * kx, a[0] * ky, b[1] * kx, b[0] * ky, p[1] * kx, p[0] * ky
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy or 1)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


class Trip:
    def __init__(self, trip_dir):
        self.dir = trip_dir
        self.meta = json.load(open(os.path.join(trip_dir, "trip.json")))
        coords = {n: (la, lo) for n, la, lo in json.load(open(os.path.join(trip_dir, "stations.json")))}
        self.stops, km = [], 0.0
        for i, (name, arr, dep) in enumerate(self.meta["timetable"]):
            if i:
                km += hav(coords[self.meta["timetable"][i - 1][0]], coords[name])
            self.stops.append({"name": name, "lat": coords[name][0], "lon": coords[name][1], "km": km, "arr": arr, "dep": dep})
        self.knots = []  # (unix time, km)
        for s in self.stops:
            for hhmm in (s["arr"], s["dep"]):
                if hhmm:
                    self.knots.append((self.ts(hhmm), s["km"]))
        self.delays = [(datetime.fromisoformat(d["since"]).timestamp(), d["seconds"]) for d in self.meta.get("delays", [])]
        self.excluded = [(datetime.fromisoformat(e["from"]).timestamp(), datetime.fromisoformat(e["to"]).timestamp(), e["reason"])
                         for e in self.meta.get("excluded", [])]

    @property
    def length_km(self):
        return self.stops[-1]["km"]

    def ts(self, hhmm):
        return datetime.fromisoformat(f"{self.meta['date']}T{hhmm}:00{self.meta['utc_offset']}").timestamp()

    def delay(self, t):
        d = 0.0
        for since, sec in self.delays:
            if since <= t:
                d = sec
        return d

    def is_excluded(self, t):
        return next((r for a, b, r in self.excluded if a <= t <= b), None)

    def km_at(self, t):
        t -= self.delay(t)
        k = self.knots
        if t <= k[0][0]:
            return k[0][1]
        for (t0, k0), (t1, k1) in zip(k, k[1:]):
            if t0 <= t <= t1:
                return k0 + (k1 - k0) * (t - t0) / (t1 - t0) if t1 > t0 else k1
        return k[-1][1]

    def point_at_km(self, k):
        for a, b in zip(self.stops, self.stops[1:]):
            if a["km"] <= k <= b["km"]:
                f = (k - a["km"]) / (b["km"] - a["km"]) if b["km"] > a["km"] else 0
                return a["lat"] + (b["lat"] - a["lat"]) * f, a["lon"] + (b["lon"] - a["lon"]) * f, a, b
        s = self.stops[-1]
        return s["lat"], s["lon"], s, s

    def position(self, t):
        """-> dict(lat, lon, km, where) for unix time t."""
        k = self.km_at(t)
        lat, lon, a, b = self.point_at_km(k)
        da, db = k - a["km"], b["km"] - k
        if da < 1:
            where = a["name"]
        elif db < 1:
            where = b["name"]
        elif da <= db:
            where = f"{da:.0f} km za st. {a['name']}"
        else:
            where = f"{db:.0f} km przed st. {b['name']}"
        return {"lat": lat, "lon": lon, "km": k, "where": where}

    def dist_to_route(self, lat, lon):
        pts = [(s["lat"], s["lon"]) for s in self.stops]
        return min(seg_dist((lat, lon), a, b) for a, b in zip(pts, pts[1:]))
