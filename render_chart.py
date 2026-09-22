#!/usr/bin/env python3
"""
Dashboard renderer for the NRR Leak Diagnostic.
Obludzyner & Co. | https://obludzyner.com

OPTIONAL. The diagnostic itself (diagnostic.py) has zero dependencies and
computes the real numbers. This script turns that JSON output into the
polished dashboard PNG shown in the README. It requires matplotlib:

    pip install matplotlib
    python3 diagnostic.py --arr 5000000 --churn 15 --expansion 8 \
        --q1 1 --q2 1 --q3 1 --q4 2 --q5 2 --q6 1 --json > result.json
    python3 render_chart.py result.json examples/sample_dashboard.png
"""

import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch

# -- design tokens (obludzyner.com / dataviz skill reference palette) --------
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
SURFACE = "#fcfcfb"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

BLUE = "#2a78d6"      # "you" / primary series
GRAY = "#c3c2b7"      # peer / reference bars
GOOD = "#0ca30c"
WARNING = "#fab219"
SERIOUS = "#ec835a"
CRITICAL = "#d03b3b"

TIER_COLOR = {"Strong": GOOD, "Partial": WARNING, "Weak": SERIOUS, "Critical": CRITICAL}

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["text.color"] = INK
plt.rcParams["axes.edgecolor"] = GRIDLINE


def rounded_hbar(ax, y, value, max_value, color, height=0.52, x0=0):
    """A thin, fully-rounded horizontal bar (pill), never a raw rectangle."""
    length = max(value - x0, max_value * 0.006)
    ax.add_patch(FancyBboxPatch(
        (x0, y - height / 2), length, height,
        boxstyle=f"round,pad=0,rounding_size={height/2}",
        linewidth=0, facecolor=color, mutation_aspect=1,
    ))


def fmt_money(v):
    return f"${v:,.0f}"


def bar_panel(ax, title, rows, unit="pct", value_fmt=None):
    """rows: list of (label, value, color)"""
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK, pad=14)
    max_value = max(v for _, v, _ in rows) * 1.28
    left_pad = max_value * 0.72  # reserve real room for row labels, never crowd them off-canvas
    ys = list(range(len(rows)))[::-1]
    for y, (label, value, color) in zip(ys, rows):
        rounded_hbar(ax, y, value, max_value, color)
        ax.text(-max_value * 0.04, y, label, ha="right", va="center",
                 fontsize=11, color=INK_SECONDARY)
        vtxt = f"{value:.0f}%" if unit == "pct" else (value_fmt(value) if value_fmt else str(value))
        ax.text(value + max_value * 0.02, y, vtxt, ha="left", va="center",
                 fontsize=11, fontweight="bold", color=INK)
    ax.set_xlim(-left_pad, max_value)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.axvline(0, color=BASELINE, linewidth=1)


def dimension_row(ax, y, label, tier, answer):
    color = TIER_COLOR[tier]
    filled = {"Strong": 3, "Partial": 2, "Weak": 1, "Critical": 0}[tier]
    for i in range(3):
        c = color if i < filled else GRIDLINE
        ax.add_patch(FancyBboxPatch(
            (i * 1.15, y - 0.3), 1.0, 0.6,
            boxstyle="round,pad=0,rounding_size=0.14",
            linewidth=0, facecolor=c,
        ))
    ax.text(-0.25, y, label, ha="right", va="center", fontsize=10.5, color=INK_SECONDARY)
    ax.text(3.8, y, tier, ha="left", va="center", fontsize=10.5, fontweight="bold", color=color)


def render(result, out_path):
    fc = result["financial_case"]
    nrr = result["nrr"]
    op = result["operating_profile"]
    b = result["benchmarks"]
    inputs = result["inputs"]

    fig = plt.figure(figsize=(8.6, 12.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)

    gs = fig.add_gridspec(
        5, 1, left=0.08, right=0.94, top=0.955, bottom=0.035,
        height_ratios=[1.55, 1.35, 1.35, 1.9, 0.35], hspace=0.55,
    )

    # -- eyebrow -------------------------------------------------------------
    fig.text(0.08, 0.985, "OBLUDZYNER & CO.  -  OPEN-SOURCE NRR LEAK DIAGNOSTIC",
              fontsize=9.5, color=INK_MUTED, fontweight="bold", ha="left")

    # -- hero panel ------------------------------------------------------
    ax_hero = fig.add_subplot(gs[0])
    ax_hero.axis("off")
    ax_hero.text(0, 0.86, "ESTIMATED ARR LEAK PER YEAR", fontsize=11, color=INK_MUTED,
                  fontweight="bold", transform=ax_hero.transAxes)
    ax_hero.text(0, 0.42, fmt_money(fc["total_annual_leak"]), fontsize=52, color=INK,
                  fontweight="bold", transform=ax_hero.transAxes, va="center")

    ax_hero.add_patch(FancyBboxPatch((0, 0.02), 0.46, 0.22, boxstyle="round,pad=0.015,rounding_size=0.04",
                                       linewidth=0, facecolor="#eef4fc", transform=ax_hero.transAxes))
    ax_hero.text(0.02, 0.19, "RECOVERABLE CHURN", fontsize=8.5, color=INK_MUTED, fontweight="bold",
                  transform=ax_hero.transAxes)
    ax_hero.text(0.02, 0.08, fmt_money(fc["arr_retained"]), fontsize=17, color=BLUE, fontweight="bold",
                  transform=ax_hero.transAxes)
    ax_hero.text(0.02, 0.005, f"{inputs['churn_pct']:.0f}% vs 5% baseline", fontsize=8.5, color=INK_SECONDARY,
                  transform=ax_hero.transAxes)

    ax_hero.add_patch(FancyBboxPatch((0.50, 0.02), 0.46, 0.22, boxstyle="round,pad=0.015,rounding_size=0.04",
                                       linewidth=0, facecolor="#fdf1e9", transform=ax_hero.transAxes))
    ax_hero.text(0.52, 0.19, "EXPANSION NOT GENERATED", fontsize=8.5, color=INK_MUTED, fontweight="bold",
                  transform=ax_hero.transAxes)
    ax_hero.text(0.52, 0.08, fmt_money(fc["expansion_generated"]), fontsize=17, color="#c9581f", fontweight="bold",
                  transform=ax_hero.transAxes)
    ax_hero.text(0.52, 0.005, f"{inputs['expansion_pct']:.0f}% vs 20% potential", fontsize=8.5, color=INK_SECONDARY,
                  transform=ax_hero.transAxes)

    # -- churn panel -----------------------------------------------------
    ax1 = fig.add_subplot(gs[1])
    bar_panel(ax1, "Annual gross revenue churn  -  lower is better", [
        ("You", inputs["churn_pct"], BLUE),
        ("Peer median", b["churn_peer_median"] * 100, GRAY),
        ("Horizontal SaaS median", b["churn_horizontal_median"] * 100, GRAY),
        ("System baseline", 5, GOOD),
    ])

    # -- NRR panel ---------------------------------------------------------
    ax2 = fig.add_subplot(gs[2])
    bar_panel(ax2, "Net revenue retention (NRR)  -  higher is better", [
        ("You", nrr["today_pct"], BLUE),
        ("Peer median", b["nrr_peer_median"] * 100, GRAY),
        ("Peer top quartile", b["nrr_peer_top_quartile"] * 100, GRAY),
    ])

    # -- operating profile ---------------------------------------------------
    ax3 = fig.add_subplot(gs[3])
    ax3.set_title(f"Operating profile: {op['band']}  ({op['score']} of {op['max_score']})",
                    loc="left", fontsize=13, fontweight="bold", color=INK, pad=14)
    dims = op["dimensions"]
    for i, d in enumerate(dims):
        dimension_row(ax3, len(dims) - 1 - i, d["label"], d["tier"], d["answer"])
    ax3.set_xlim(-2.6, 6)
    ax3.set_ylim(-0.7, len(dims) - 0.3)
    ax3.axis("off")

    # -- footer ---------------------------------------------------------------
    ax_footer = fig.add_subplot(gs[4])
    ax_footer.axis("off")
    ax_footer.axhline(0.9, color=GRIDLINE, linewidth=1, xmin=0, xmax=1)
    ax_footer.text(0, 0.15, "Open-source, directional version. obludzyner.com  -  Book a Revenue Audit for your real numbers.",
                     fontsize=9, color=INK_MUTED, transform=ax_footer.transAxes)

    fig.savefig(out_path, facecolor=SURFACE)
    print(f"Wrote {out_path}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 render_chart.py result.json out.png", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1]) as f:
        result = json.load(f)
    render(result, sys.argv[2])


if __name__ == "__main__":
    main()
