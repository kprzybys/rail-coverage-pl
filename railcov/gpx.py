"""Import a phone GPX track into a trip, clipped from the first to the last station.

Usage: python -m railcov.gpx trips/<trip-id> path/to/recording.gpx [--radius-km 0.4]
Writes trips/<trip-id>/track.gpx with only lat, lon and time: device name,
app metadata and any points before the departure station or after the arrival
station are dropped, so the published track does not show where the traveller
came from or went to.
"""
import argparse
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .data import load_gpx
from .model import Trip, hav

NS = "http://www.topografix.com/GPX/1/1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trip_dir")
    ap.add_argument("gpx")
    ap.add_argument("--radius-km", type=float, default=0.4, help="distance from a station that counts as 'at the station'")
    a = ap.parse_args()
    trip = Trip(a.trip_dir)
    first, last = trip.stops[0], trip.stops[-1]
    pts = load_gpx(a.gpx)
    # start: last time we are at the first station (departure); if the track starts later, from the beginning
    start = max((i for i, (_, la, lo) in enumerate(pts) if hav((la, lo), (first["lat"], first["lon"])) <= a.radius_km), default=0)
    # end: first time we reach the last station
    end = next((i for i, (_, la, lo) in enumerate(pts) if i > start and hav((la, lo), (last["lat"], last["lon"])) <= a.radius_km), len(pts) - 1)
    # the timetable route is straight lines between stations, so only drop gross GPS outliers
    kept = [p for p in pts[start:end + 1] if trip.dist_to_route(p[1], p[2]) <= 20]
    ET.register_namespace("", NS)
    gpx = ET.Element(f"{{{NS}}}gpx", version="1.1", creator="rail-coverage-pl")
    seg = ET.SubElement(ET.SubElement(gpx, f"{{{NS}}}trk"), f"{{{NS}}}trkseg")
    for ts, la, lo in kept:
        pt = ET.SubElement(seg, f"{{{NS}}}trkpt", lat=f"{la:.6f}", lon=f"{lo:.6f}")
        iso = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ET.SubElement(pt, f"{{{NS}}}time").text = iso
    ET.ElementTree(gpx).write(os.path.join(a.trip_dir, "track.gpx"), xml_declaration=True, encoding="utf-8")
    print(f"{len(pts)} points in, {len(kept)} kept ({start}..{end}), dropped {len(pts) - len(kept)}")


if __name__ == "__main__":
    main()
