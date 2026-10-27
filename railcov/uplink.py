"""Which operator carried each measurement, for trips on on-board Wi-Fi.

The PKP Intercity router (Passengera) multiplexes several cellular modems, so the
public IP of the Wi-Fi uplink changes from one request to the next. `uplink.sh`
samples that public IP every 30 s (offset from the ping bursts) into uplink.csv;
here we map each IP to the mobile operator that owns it and expose, for any moment,
which operator was carrying the link.

Operator lookup: a built-in table of Polish mobile ranges first (works offline),
then a one-off RDAP query per unknown IP, cached under cache/rdap/. Unknown and
offline both fall back to "inny".
"""
import csv
import ipaddress
import json
import os
import urllib.request
from bisect import bisect_left
from datetime import datetime

# Friendly name per RIPE netname / org fragment (matched case-insensitively as substring).
NETNAME_OP = [
    ("IDEA-MOBILE", "Orange"), ("ORANGE", "Orange"), ("PTK", "Orange"),
    ("ERANET", "T-Mobile"), ("T-MOBILE", "T-Mobile"), ("POLSKA-TELEFONIA", "T-Mobile"),
    ("P4", "Play"), ("PLAY", "Play"),
    ("POLKOMTEL", "Plus"), ("PLUS", "Plus"),
]

# Known ranges (best-effort; extend as new uplink IPs appear). Confirmed on the
# IC/EIC Passengera uplink: 37.47.224.0/19 Orange (PL-IDEA-MOBILE), 37.31.0.0/16 T-Mobile (ERANET).
RANGES = [
    ("37.47.224.0/19", "Orange"),
    ("37.31.0.0/16", "T-Mobile"),
]
_NETS = [(ipaddress.ip_network(c), op) for c, op in RANGES]

COLORS = {"Orange": "#f07b16", "T-Mobile": "#c2187a", "Play": "#7a3ff0", "Plus": "#1f9d55", "inny": "#8a9692"}


def _from_table(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return None
    for net, op in _NETS:
        if a in net:
            return op
    return None


def _from_rdap(ip, cache="cache/rdap"):
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, ip + ".txt")
    if os.path.exists(path):
        return open(path).read().strip() or None
    op = "inny"
    try:
        req = urllib.request.Request(f"https://rdap.db.ripe.net/ip/{ip}", headers={"User-Agent": "rail-coverage-pl"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
        hay = " ".join(str(d.get(k, "")) for k in ("name", "handle")).upper()
        hay += " " + json.dumps(d.get("entities", []), ensure_ascii=False).upper()
        op = next((o for frag, o in NETNAME_OP if frag in hay), "inny")
    except Exception:
        return None  # offline: do not cache, let the table/fallback decide
    open(path, "w").write(op)
    return op


def operator_of(ip):
    """-> 'Orange' | 'T-Mobile' | 'Play' | 'Plus' | 'inny'."""
    return _from_table(ip) or _from_rdap(ip) or "inny"


def load_uplink(trip_dir):
    """-> sorted list of (unix time, operator); [] if the trip has no uplink.csv.

    The resolved ip -> operator map is frozen into trips/<id>/uplink-ops.json so the
    published trip rebuilds deterministically, offline and without the RDAP cache.
    """
    path = os.path.join(trip_dir, "uplink.csv")
    if not os.path.exists(path):
        return []
    frozen_path = os.path.join(trip_dir, "uplink-ops.json")
    frozen = json.load(open(frozen_path)) if os.path.exists(frozen_path) else {}
    cache, out, new = dict(frozen), [], False
    for r in csv.DictReader(open(path)):
        ip = (r.get("ip") or "").strip()
        if not ip:
            continue
        if ip not in cache:
            cache[ip], new = operator_of(ip), True
        out.append((datetime.fromisoformat(r["czas_iso"]).timestamp(), cache[ip]))
    if new or cache != frozen:
        json.dump(dict(sorted(cache.items())), open(frozen_path, "w"), ensure_ascii=False, indent=0)
    return sorted(out)


def op_at(samples, t, max_gap=60):
    """Operator of the uplink sample nearest to time t, within max_gap seconds; else None."""
    if not samples:
        return None
    i = bisect_left(samples, (t,))
    cand = []
    if i < len(samples):
        cand.append(samples[i])
    if i:
        cand.append(samples[i - 1])
    best = min(cand, key=lambda s: abs(s[0] - t))
    return best[1] if abs(best[0] - t) <= max_gap else None
