"""Images for sharing: route strip (PNG) and an animated replay (GIF).

Usage: python -m railcov.promo trips/<trip-id>   -> figures/strip.png, figures/replay.gif
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402

from .data import GRADE_PL, GRADES, load  # noqa: E402
from .report import COL, INK, MUTED  # noqa: E402

SHORT = {" Główny": "", " Wschodnia": " Wsch.", " Południe": " Pd.", " Północ": " Pn."}


def short(name):
    for a, b in SHORT.items():
        name = name.replace(a, b)
    return name


def named_stops(trip):
    return [s for s in trip.stops if (s["arr"] or s["dep"]) and not any(x in s["name"] for x in ("Zielone", "Centralna", "Zachodnia"))]


def strip(trip, rows, path):
    fig, ax = plt.subplots(figsize=(12, 1.6))
    ax.axhspan(0, 1, color="#e3e8e6")
    if rows and rows[0]["km"] > 10:
        ax.text(rows[0]["km"] / 2, 0.5, f"brak pomiarów\n(start {rows[0]['time'][:5]})", ha="center", va="center", fontsize=9, color=MUTED)
    for r in rows:
        ax.axvspan(r["km"] - 0.5, r["km"] + 0.7, ymin=0, ymax=1, color=COL[r["grade"]], lw=0)
    for s in named_stops(trip):
        ax.plot([s["km"], s["km"]], [-0.12, 0], color=INK, lw=1.5, clip_on=False)
        ax.text(s["km"], -0.32, short(s["name"]), ha="center", va="top", fontsize=10, color=INK)
    ax.set_xlim(-2, trip.length_km + 2)
    ax.set_ylim(0, 1)
    ax.axis("off")
    t = trip.meta["train"]
    ax.set_title(f"Internet w pociągu {t['number']} {trip.meta['from']} → {short(trip.meta['to'])}, km po km "
                 f"({trip.meta['network']['operator']}, {trip.meta['date']})", loc="left", fontsize=12, fontweight="bold", color=INK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COL[g], label=GRADE_PL[g]) for g in GRADES + ["excluded"]]
    fig.legend(handles=handles, loc="upper center", ncol=5, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.32))
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def replay(trip, rows, track, path, frames=110, fps=10):
    fig = plt.figure(figsize=(7.2, 8.4))
    ax = fig.add_axes([0.04, 0.30, 0.92, 0.64])
    ax2 = fig.add_axes([0.10, 0.06, 0.86, 0.18])
    lats = [s["lat"] for s in trip.stops]
    lons = [s["lon"] for s in trip.stops]
    if track:
        ax.plot([p[2] for p in track], [p[1] for p in track], color="#c9d1ce", lw=3, zorder=1)
    else:
        ax.plot(lons, lats, color="#c9d1ce", lw=3, zorder=1)
    for s in named_stops(trip):
        ax.plot(s["lon"], s["lat"], "o", ms=6, mfc="white", mec=INK, zorder=4)
        ax.text(s["lon"] + 0.06, s["lat"], short(s["name"]), fontsize=9, va="center", color=INK, zorder=5)
    ax.set_aspect(1 / 0.62)
    ax.axis("off")
    t = trip.meta["train"]
    title = ax.set_title(f"{t['number']} {trip.meta['from']} → {short(trip.meta['to'])}", loc="left", fontsize=13, fontweight="bold", color=INK)
    clock = ax.text(0.0, -0.02, "", transform=ax.transAxes, fontsize=10, color=MUTED, va="top")
    dots = ax.scatter([], [], s=[], c=[], zorder=3)
    train, = ax.plot([], [], "o", ms=13, mfc="white", mec="#0b5fff", mew=3, zorder=6)
    ts = [r["ts"] for r in rows]
    t0, t1 = ts[0], ts[-1]
    ax2.set_yscale("log")
    ax2.set_ylim(10, 6000)
    ax2.set_xlim(t0, t1)
    ax2.set_yticks([30, 100, 300, 1000, 3000])
    ax2.set_yticklabels(["30", "100", "300", "1000", "3000"], fontsize=8)
    ax2.set_xticks([])
    ax2.set_ylabel("ping [ms]", fontsize=9)
    for sp in ("top", "right"):
        ax2.spines[sp].set_visible(False)
    pts = ax2.scatter([], [], s=8, c=[])
    cursor = ax2.axvline(t0, color="#0b5fff", lw=1.5)
    from datetime import datetime

    def frame(i):
        now = t0 + (t1 - t0) * i / (frames - 1)
        shown = [r for r in rows if r["ts"] <= now]
        if shown:
            dots.set_offsets([[r["lon"], r["lat"]] for r in shown])
            dots.set_sizes([10 if r["grade"] == "good" else 34 for r in shown])
            dots.set_facecolor([COL[r["grade"]] for r in shown])
            dots.set_edgecolor("none")
            pts.set_offsets([[r["ts"], r["avg"] if r["avg"] is not None else 5000] for r in shown])
            pts.set_facecolor([COL[r["grade"]] for r in shown])
            pts.set_edgecolor("none")
            r = shown[-1]
            train.set_data([r["lon"]], [r["lat"]])
            train.set_markerfacecolor(COL[r["grade"]])
            clock.set_text(f"{datetime.fromtimestamp(now):%H:%M} · {r['where']} · {GRADE_PL[r['grade']]}")
        cursor.set_xdata([now, now])
        return dots, train, pts, cursor, clock, title

    anim = FuncAnimation(fig, frame, frames=frames, blit=False)
    anim.save(path, writer=PillowWriter(fps=fps), dpi=90)
    plt.close(fig)


def main():
    d = sys.argv[1]
    trip, rows, _, track = load(d)
    os.makedirs(os.path.join(d, "figures"), exist_ok=True)
    strip(trip, rows, os.path.join(d, "figures", "strip.png"))
    replay(trip, rows, track, os.path.join(d, "figures", "replay.gif"))
    print("ok")


if __name__ == "__main__":
    main()
