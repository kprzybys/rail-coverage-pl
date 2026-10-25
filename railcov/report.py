"""Charts and a Markdown report for one trip.

Usage: python -m railcov.report trips/<trip-id>
Writes trips/<trip-id>/figures/*.png, summary.json and report.md.
"""
import json
import os
import statistics
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .data import GRADE_PL, GRADES, load  # noqa: E402

COL = {"good": "#1f9d55", "weak": "#d9a400", "bad": "#d4462f", "dead": "#18211f", "excluded": "#b8c2be"}
INK, MUTED, GRID = "#18211f", "#5d6a66", "#dfe5e2"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})


def section_of(trip, km):
    by = {s["name"]: s["km"] for s in trip.stops}
    for sec in trip.meta.get("sections", []):
        if by[sec["from"]] - 0.01 <= km <= by[sec["to"]] + 0.01:
            return sec["name"]
    return None


def zones(rows):
    """Consecutive runs of bad/dead measurements."""
    out, cur = [], None
    for r in rows:
        if r["grade"] in ("bad", "dead"):
            if cur is None:
                cur = {"from": r, "to": r, "worst": r, "n": 0}
                out.append(cur)
            cur["to"], cur["n"] = r, cur["n"] + 1
            if (r["loss"], r["avg"] or 0) > (cur["worst"]["loss"], cur["worst"]["avg"] or 0):
                cur["worst"] = r
        else:
            cur = None
    return out


def summarize(trip, rows):
    used = [r for r in rows if r["grade"] != "excluded"]
    def stats(rs):
        avgs = sorted(r["avg"] for r in rs if r["avg"] is not None)
        return {
            "n": len(rs),
            "share": {g: round(sum(r["grade"] == g for r in rs) / len(rs), 3) for g in GRADES} if rs else {},
            "median_ms": round(statistics.median(avgs)) if avgs else None,
            "p90_ms": round(avgs[int(len(avgs) * 0.9) - 1]) if len(avgs) >= 10 else None,
            "mean_loss": round(statistics.mean(r["loss"] for r in rs), 1) if rs else None,
        }
    secs = {}
    for r in used:
        secs.setdefault(section_of(trip, r["km"]) or "inne", []).append(r)
    return {"all": stats(used), "excluded_n": len(rows) - len(used),
            "sections": {k: stats(v) for k, v in secs.items()}, "zones": len(zones(used))}


def fig_timeline(trip, rows, path):
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12, 5.2), sharex=True, gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08})
    for r in rows:
        y = r["avg"] if r["avg"] is not None else 5000
        ax.scatter(r["km"], y, s=18 if r["grade"] == "good" else 30, color=COL[r["grade"]], zorder=3,
                   marker="x" if r["avg"] is None else "o", linewidths=1.2)
        ax2.bar(r["km"], r["loss"], width=0.9, color=COL[r["grade"]])
    ax.set_yscale("log")
    ax.set_ylim(10, 6000)
    ax.set_yticks([20, 50, 100, 300, 1000, 3000])
    ax.set_yticklabels(["20", "50", "100", "300", "1000", "3000"])
    ax.axhline(100, color=GRID, lw=1, zorder=1)
    ax.axhline(300, color=GRID, lw=1, zorder=1)
    ax.set_ylabel("średni ping [ms]")
    ax2.set_ylabel("strata [%]")
    ax2.set_ylim(0, 100)
    major = {s["name"] for s in trip.stops if s["arr"] or s["dep"]}
    for s in trip.stops:
        for a in (ax, ax2):
            a.axvline(s["km"], color=GRID, lw=0.8, zorder=0)
        if s["name"] in major and s["name"] not in ("Białystok Zielone Wzgórza", "Warszawa Centralna", "Warszawa Zachodnia"):
            ax.text(s["km"], 7000, s["name"].replace(" Główny", "").replace(" Wschodnia", " Wsch."), rotation=30, ha="left",
                    va="bottom", fontsize=8.5, color=INK)
    ax2.set_xlabel("km trasy (pozycja wg rozkładu)")
    ax2.set_xlim(-3, trip.length_km + 3)
    t = trip.meta["train"]
    fig.suptitle(f"{t['number']} {t['name']} {trip.meta['from']} → {trip.meta['to']}, {trip.meta['date']}: ping przez hotspot {trip.meta['network']['operator']}",
                 x=0.01, y=1.06, ha="left", fontsize=12, color=INK, fontweight="bold")
    handles = [plt.Line2D([], [], marker="o", ls="", color=COL[g], label=GRADE_PL[g]) for g in GRADES + ["excluded"]]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.06))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_sections(summary, path):
    secs = [(k, v) for k, v in summary["sections"].items() if v["n"]]
    fig, ax = plt.subplots(figsize=(9, 0.7 * len(secs) + 1.2))
    for i, (name, v) in enumerate(reversed(secs)):
        left = 0
        for g in GRADES:
            w = v["share"][g] * 100
            ax.barh(i, w, left=left, color=COL[g], height=0.6)
            if w >= 6:
                ax.text(left + w / 2, i, f"{w:.0f}%", ha="center", va="center", fontsize=8.5, color="white")
            left += w
        ax.text(101, i, f"mediana {v['median_ms']} ms · n={v['n']}", va="center", fontsize=8.5, color=MUTED)
    ax.set_yticks(range(len(secs)))
    ax.set_yticklabels([n for n, _ in reversed(secs)])
    ax.set_xlim(0, 100)
    ax.set_xlabel("udział pomiarów [%]")
    ax.set_title("Jakość łącza według odcinka trasy", loc="left", fontweight="bold", color=INK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COL[g], label=GRADE_PL[g]) for g in GRADES]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.55 if len(secs) < 4 else -0.4), ncol=4, frameon=False, fontsize=8.5)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_bts(rows, path):
    bins = [(0, 0.5), (0.5, 1), (1, 2), (2, 3), (3, 5), (5, 99)]
    used = [r for r in rows if r["grade"] != "excluded" and r["site_km"] is not None]
    labels, bad, n = [], [], []
    for a, b in bins:
        rs = [r for r in used if a <= r["site_km"] < b]
        labels.append(f"{a}–{b} km" if b < 99 else f"≥{a} km")
        n.append(len(rs))
        bad.append(100 * sum(r["grade"] in ("bad", "dead") for r in rs) / len(rs) if rs else 0)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(labels, bad, color=COL["bad"], width=0.6)
    for i, (v, k) in enumerate(zip(bad, n)):
        ax.text(i, v + 1, f"{v:.0f}%\nn={k}", ha="center", va="bottom", fontsize=8.5, color=MUTED)
    ax.set_ylim(0, max(bad + [10]) * 1.35)
    ax.set_ylabel("pomiary słabe lub bez łącza [%]")
    ax.set_xlabel("odległość pozycji pociągu od najbliższej stacji bazowej Orange/T-Mobile (UKE)")
    ax.set_title("Czy bliskość BTS chroni przed martwymi strefami?", loc="left", fontweight="bold", color=INK)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def write_report(trip, rows, summary, path):
    m, t = trip.meta, trip.meta["train"]
    a = summary["all"]
    L = [f"# {t['number']} {t['name']}: {m['from']} → {m['to']}, {m['date']}", "",
         f"Pomiar jakości mobilnego internetu w pociągu: hotspot {m['network']['device']}, sieć {m['network']['operator']}. "
         f"{m['collector']['method']} do {m['collector']['target']}. Pozycja pociągu z rozkładu jazdy"
         f"{' i śladu GPS' if any(r['pos_src'] == 'gps' for r in rows) else ''}.", "",
         "![Ping wzdłuż trasy](figures/timeline.png)", "",
         "## Najważniejsze liczby", "",
         f"- pomiarów: **{a['n']}** (+{summary['excluded_n']} pominiętych jako zakłócone)",
         f"- dobre łącze: **{a['share']['good'] * 100:.0f}%** pomiarów, wahania {a['share']['weak'] * 100:.0f}%, słabe {a['share']['bad'] * 100:.0f}%, brak łącza {a['share']['dead'] * 100:.0f}%",
         f"- mediana średniego pingu: **{a['median_ms']} ms**, 90. percentyl: {a['p90_ms']} ms",
         f"- odcinków słabych lub bez łącza: **{summary['zones']}**", "",
         "## Odcinki trasy", "", "![Odcinki](figures/sections.png)", "",
         "| Odcinek | Pomiary | Dobre | Słabe + brak | Mediana pingu |", "|---|---:|---:|---:|---:|"]
    for k, v in summary["sections"].items():
        L.append(f"| {k} | {v['n']} | {v['share']['good'] * 100:.0f}% | {(v['share']['bad'] + v['share']['dead']) * 100:.0f}% | {v['median_ms']} ms |")
    L += ["", "## Martwe i słabe strefy", "", "| Czas | Gdzie (km) | Najgorszy pomiar | Najbliższy BTS |", "|---|---|---|---|"]
    for z in zones([r for r in rows if r["grade"] != "excluded"]):
        w = z["worst"]
        q = "100% strat" if w["avg"] is None else f"{w['avg']:.0f} ms, strata {w['loss']:.0f}%"
        a, b = z["from"]["time"][:5], z["to"]["time"][:5]
        span = a if a == b else f"{a}–{b}"
        L.append(f"| {span} | {z['from']['where']} (km {z['from']['km']:.0f}) | {q} | {w['site_op']} {w['site_km']} km ({w['site_place']}) |")
    L += ["", "## Stacje bazowe a jakość", "", "![BTS](figures/bts.png)", "",
          "Odległość liczona od szacowanej pozycji pociągu do najbliższej lokalizacji z pozwoleniem UKE (LTE 800/1800/2100/2600, 5G 2100). "
          "Pozwolenie nie oznacza, że stacja działa ani że świeci w stronę torów.", "",
          "## Zastrzeżenia", ""]
    for e in m.get("excluded", []):
        L.append(f"- Pominięto {e['from'][11:16]}–{e['to'][11:16]}: {e['reason']}.")
    for d in m.get("delays", []):
        L.append(f"- Od {d['since'][11:16]} przyjęto opóźnienie {d['seconds'] // 60} min {d['seconds'] % 60} s ({d['source']}).")
    L += [f"- {m['collector']['note'].capitalize()}.",
          "- Bez GPS pozycja jest liczona przy stałej prędkości między postojami, po prostej między stacjami; błąd sięga kilku km.",
          "- Jeden telefon, jedna sieć, jeden przejazd: to obserwacja, nie pomiar referencyjny.", ""]
    if m.get("observations"):
        L += ["## Dziennik podróży", ""] + [f"- {o['time'][11:16]}: {o['text']}" for o in m["observations"]] + [""]
    open(path, "w").write("\n".join(L))


def main():
    d = sys.argv[1]
    trip, rows, sites, _ = load(d)
    os.makedirs(os.path.join(d, "figures"), exist_ok=True)
    s = summarize(trip, rows)
    json.dump(s, open(os.path.join(d, "summary.json"), "w"), ensure_ascii=False, indent=1)
    fig_timeline(trip, rows, os.path.join(d, "figures", "timeline.png"))
    fig_sections(s, os.path.join(d, "figures", "sections.png"))
    fig_bts(rows, os.path.join(d, "figures", "bts.png"))
    write_report(trip, rows, s, os.path.join(d, "report.md"))
    print(json.dumps(s["all"], ensure_ascii=False))


if __name__ == "__main__":
    main()
