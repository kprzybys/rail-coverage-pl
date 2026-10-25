"""Static Leaflet map of all trips for GitHub Pages.

Usage: python -m railcov.site  (reads trips/*/, writes site/index.html and site/trips.js)
"""
import glob
import json
import os

from .data import load

PAGE = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>rail-coverage-pl</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  :root { --bg:#f3f5f4; --fg:#18211f; --muted:#5d6a66; --good:#1f9d55; --weak:#d9a400; --bad:#d4462f; --dead:#18211f; --excluded:#b8c2be; }
  html, body { height: 100%; margin: 0; font: 14px/1.4 system-ui, sans-serif; color: var(--fg); background: var(--bg); }
  #map { position: absolute; inset: 0; }
  .panel { position: absolute; z-index: 1000; top: 12px; left: 56px; max-width: min(360px, calc(100% - 80px)); background: #fff;
           border-radius: 6px; padding: 10px 14px; box-shadow: 0 2px 10px rgba(0,0,0,.18); }
  .panel h1 { font-size: 16px; margin: 0 0 4px; }
  .panel p { margin: 4px 0; color: var(--muted); font-size: 12.5px; }
  .lg { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 12px; margin-top: 6px; }
  .lg i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; vertical-align: -1px; }
  select { margin-top: 6px; max-width: 100%; }
</style>
</head>
<body>
<div id="map"></div>
<div class="panel">
  <h1>Zasięg internetu w pociągach</h1>
  <p>Ping co 30 s przez hotspot w telefonie, pozycja z GPS lub rozkładu jazdy. <a href="https://github.com/kprzybys/rail-coverage-pl">Dane i kod na GitHubie</a>.</p>
  <select id="trip"></select>
  <div class="lg"><span><i style="background:var(--good)"></i>dobre</span><span><i style="background:var(--weak)"></i>wahania</span>
  <span><i style="background:var(--bad)"></i>słabe</span><span><i style="background:var(--dead)"></i>brak łącza</span>
  <span><i style="background:#f07b16;opacity:.6"></i>BTS Orange</span><span><i style="background:#c2187a;opacity:.6"></i>BTS T-Mobile</span></div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="trips.js"></script>
<script>
const map = L.map("map", { preferCanvas: true });
const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(map);
const rail = L.tileLayer("https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png", { maxZoom: 18, opacity: .55,
  attribution: '<a href="https://www.openrailwaymap.org/">OpenRailwayMap</a> (CC-BY-SA)' }).addTo(map);
const css = n => getComputedStyle(document.documentElement).getPropertyValue("--" + n).trim();
const PL = { good: "dobre", weak: "wahania", bad: "słabe", dead: "brak łącza", excluded: "pominięty (zakłócony)" };
let layer = null, bts = null, ctl = null;
function show(t) {
  if (layer) layer.remove();
  if (bts) bts.remove();
  if (ctl) ctl.remove();
  layer = L.layerGroup().addTo(map);
  bts = L.layerGroup();
  for (const s of t.sites) L.circleMarker([s.lat, s.lon], { radius: 2.5, stroke: false, fillOpacity: .35,
    fillColor: s.op === "Orange" ? "#f07b16" : "#c2187a" }).bindTooltip(`${s.op} · ${s.place}<br>${s.bands.join(", ")}<br>pozwolenie UKE`).addTo(bts);
  ctl = L.control.layers(null, { "Stacje bazowe (pozwolenia UKE)": bts, "OpenRailwayMap": rail }, { position: "topright" }).addTo(map);
  L.polyline(t.stations.map(s => [s.lat, s.lon]), { color: "#8a9692", weight: 3, dashArray: "6 6" }).addTo(layer);
  for (const s of t.stations) if (s.arr || s.dep) L.circleMarker([s.lat, s.lon], { radius: 5, color: "#18211f", weight: 2, fillColor: "#fff", fillOpacity: 1 })
    .bindTooltip(`${s.name} ${s.arr || ""}${s.arr && s.dep ? "–" : ""}${s.dep || ""}`).addTo(layer);
  for (const r of t.rows) {
    const q = r.avg == null ? `strata ${r.loss}%` : `strata ${r.loss}% · ${Math.round(r.min)}/${Math.round(r.avg)}/${Math.round(r.max)} ms`;
    L.circleMarker([r.lat, r.lon], { radius: r.grade === "good" ? 4 : 6, color: "#fff", weight: 1, fillColor: css(r.grade), fillOpacity: .95 })
      .bindTooltip(`<b>${r.time}</b> · ${PL[r.grade]}<br>${q}<br>${r.where} · pozycja: ${r.pos_src}` + (r.excluded ? `<br><i>${r.excluded}</i>` : "")).addTo(layer);
  }
  map.fitBounds(L.latLngBounds(t.stations.map(s => [s.lat, s.lon])).pad(.05));
}
const sel = document.getElementById("trip");
TRIPS.forEach((t, i) => sel.add(new Option(t.title, i)));
sel.onchange = () => show(TRIPS[sel.value]);
show(TRIPS[0]);
</script>
</body>
</html>
"""


def main():
    trips = []
    for d in sorted(glob.glob("trips/*/"), reverse=True):
        if not os.path.exists(os.path.join(d, "ping.csv")):
            continue
        trip, rows, sites, _ = load(d)
        m = trip.meta
        keep = ("time", "loss", "min", "avg", "max", "lat", "lon", "where", "grade", "pos_src", "excluded")
        trips.append({
            "title": f"{m['date']} · {m['train']['number']} {m['from']} → {m['to']} · {m['network']['operator']}",
            "stations": [{k: s[k] for k in ("name", "lat", "lon", "arr", "dep")} for s in trip.stops],
            "rows": [{k: r[k] for k in keep} for r in rows],
            "sites": [{k: s[k] for k in ("lat", "lon", "op", "place", "bands")} for s in sites],
        })
    os.makedirs("site", exist_ok=True)
    open("site/trips.js", "w").write("const TRIPS=" + json.dumps(trips, ensure_ascii=False, separators=(",", ":")) + ";")
    open("site/index.html", "w").write(PAGE)
    print(len(trips), "trips")


if __name__ == "__main__":
    main()
