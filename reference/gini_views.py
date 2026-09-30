# gini_views.py — three views of the relative pricing implied by gini_p across
# a reinsurance program: occurrence layers, then a quota share, to the final net.
# Inputs (same folder): "grid (1).csv" (gini by step x distortion),
# results.csv (point-estimate LR/ER/CR and premium/margin shares),
# msd.csv (margin to std dev, cost-of-capital metrics).
#
#   view 1  gini_view1_waterfall.png       net gini down the occurrence program and
#                                          back up through the QS, per distortion
#   view 2  gini_view2_tail_slope.png      layer price across the distortion spectrum
#   view 3  gini_view3_relative_price.png  price vs the gross book + point estimates
#
# Run:  uv run --with pandas --with matplotlib gini_views.py

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm, to_rgb

# no .resolve(): X: is a substed drive and resolving it unmasks the target path
HERE = Path(__file__).absolute().parent

# ---------------------------------------------------------------- palette ----
# Validated light-mode reference palette (dataviz skill); roles, not decoration.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"          # primary text
INK2 = "#52514e"         # secondary text
MUTED = "#898781"        # axis / tick labels
GRID = "#e1e0d9"         # hairline gridlines
BASELINE = "#c3c2b7"     # axis lines, connectors
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
BLUE_DEEP, BLUE_LIGHT = "#256abf", "#86b6ef"                   # sequential blue steps
DIV_LO, DIV_MID, DIV_HI = "#2a78d6", "#f0efec", "#e34948"      # diverging blue-gray-red

mpl.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": BASELINE,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.labelcolor": INK2,
    "text.color": INK,
    "font.size": 9,
})

# ------------------------------------------------------------------- data ----
df = pd.read_csv(HERE / "data" / "grid (1).csv")
gini = df.set_index(["Step", "distortion"])["gini_p"]
res = pd.read_csv(HERE / "data" / "results.csv").set_index("Step")
msd = pd.read_csv(HERE / "data" / "msd.csv").set_index("Step")

# (grid step, display label, results/msd step)
LAYERS = [("500x500 result", "500 xs 500", "500x500"),
          ("1x1 result", "1 xs 1", "1x1"),
          ("3x2 result", "3 xs 2", "3x2"),
          ("5x5 result", "5 xs 5", "5x5")]
NETS = ["net through 500x500", "net through 1x1", "net through 3x2", "net through 5x5"]
PACKAGE = "All occurrence result"   # the combined occurrence program
QS = "QS result"
NET_OCC = "net through 5x5"         # net of the occurrence program
FINAL = "net through QS"            # final net (= margin rows)

DNAME = {"ph": "Proportional hazard", "wang": "Wang", "dual": "Dual moment", "tvar": "TVaR"}
# order distortion families by the gini they assign the gross book (tail weight axis)
DIST = sorted(DNAME, key=lambda d: gini[("Gross result", d)])

# point-estimate CRs; net-of-occurrence CR is derived from the shares
# (gross premium 1; occurrence cessions carry no expense, gross expense stays)
_occ = res.loc["All occurrence"]
_prem_no = 1 + _occ["P_share"]
_loss_no = res.loc["Gross", "LR"] + _occ["LR"] * _occ["P_share"]
CR_NET_OCC = (_loss_no + res.loc["Gross", "ER"]) / _prem_no
CR = res["CR"].to_dict() | {"net occ": CR_NET_OCC}


def pct(x):
    return f"{100 * x:.1f}%"


Y_MAX = 1.08 * max(max(gini[(s, d)] for s, _, _ in LAYERS for d in DIST),
                   max(gini[(FINAL, d)] for d in DIST))


def tidy(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(BASELINE)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(length=0)


# ------------------------------------------- view 1: program waterfall -------
def view1():
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.2), sharey=True)
    w = 0.55
    for ax, d in zip(axes.flat, DIST):
        g0 = gini[("Gross result", d)]
        nets = [gini[(s, d)] for s in NETS]
        net_final = gini[(FINAL, d)]
        levels = [g0] + nets

        def level_bar(x, top):
            ax.bar(x, top, w, color=BLUE_DEEP, zorder=3)
            ax.annotate(f"{top:.3f}", (x, top), xytext=(0, 4),
                        textcoords="offset points", ha="center", fontsize=8, color=INK2)

        def delta_bar(x, prev, cur):
            lo, hi = min(prev, cur), max(prev, cur)
            ax.bar(x, hi - lo, w, bottom=lo, color=BLUE_LIGHT, zorder=3)
            ax.annotate(f"{cur - prev:+.3f}".replace("-", "−"),
                        (x - w / 2, (prev + cur) / 2), xytext=(-3, 0),
                        textcoords="offset points", ha="right", va="center",
                        fontsize=7.5, color=INK2)
            ax.hlines(prev, x - 1 + w / 2, x + w / 2, color=BASELINE,
                      linewidth=0.9, linestyle=(0, (3, 2)), zorder=2)

        def buy_diamond(x, ref, buy):
            ax.vlines(x, ref, buy, color=CAT[1], linewidth=1.0,
                      linestyle=(0, (1, 2)), zorder=3)
            ax.plot([x], [buy], marker="D", ms=6.5, color=CAT[1], zorder=4)
            if buy > ref:
                off, ha = (0, 6), "center"
            elif buy > 0.05:
                off, ha = (0, -13), "center"
            else:                       # near the axis floor: label beside the mark
                off, ha = (7, -3), "left"
            ax.annotate(f"{buy:.3f}", (x, buy), xytext=off,
                        textcoords="offset points", ha=ha, fontsize=8, color=INK2)

        level_bar(0, g0)                                   # Gross
        for i, (s, _, _) in enumerate(LAYERS, start=1):    # occurrence cessions
            delta_bar(i, levels[i - 1], levels[i])
            buy_diamond(i, levels[i - 1], gini[(s, d)])
        ax.hlines(nets[-1], 4 + w / 2, 5 + w / 2, color=BASELINE,
                  linewidth=0.9, linestyle=(0, (3, 2)), zorder=2)
        level_bar(5, nets[-1])                             # net of occurrence
        delta_bar(6, nets[-1], net_final)                  # QS concentrates margin
        buy_diamond(6, nets[-1], gini[(QS, d)])
        ax.hlines(net_final, 6 + w / 2, 7 + w / 2, color=BASELINE,
                  linewidth=0.9, linestyle=(0, (3, 2)), zorder=2)
        level_bar(7, net_final)                            # final net

        # the occurrence package, priced as one purchase
        pkg = gini[(PACKAGE, d)]
        ax.hlines(pkg, 0.6, 4.4, color=CAT[1], linewidth=1.2,
                  linestyle=(0, (5, 3)), alpha=0.75, zorder=2)
        ax.annotate(f"package {pkg:.3f}", (0.62, pkg), xytext=(0, 3),
                    textcoords="offset points", fontsize=7.5, color=CAT[1])

        ax.set_title(f"{DNAME[d]} ({d})", fontsize=10.5, color=INK, pad=8)
        ticks = ([("Gross", "Gross")] + [(lab, r) for _, lab, r in LAYERS]
                 + [("Net occ", "net occ"), ("QS", "QS"), ("Net", "All")])
        ax.set_xticks(range(8), [f"{lab}\nCR {pct(CR[r])}" for lab, r in ticks],
                      fontsize=8)
        ax.set_ylim(0, Y_MAX)
        ax.margins(x=0.03)
        tidy(ax)
        if ax in axes[:, 0]:
            ax.set_ylabel("gini_p")

    fig.suptitle("Risk load ceded, then concentrated", fontsize=14, x=0.06,
                 ha="left", color=INK, y=0.985)
    fig.text(0.06, 0.905, "Blue bars: the net book's gini falls through the occurrence "
             "cessions, then jumps as the QS cedes 64% of premium at gini ≈ 0.01,\n"
             "concentrating the margin on the retained book. Orange diamonds: the gini "
             "at which each cover was bought. CR: point-estimate combined ratio.",
             fontsize=9.5, color=INK2)
    fig.tight_layout(rect=(0.02, 0.01, 0.99, 0.90))
    fig.savefig(HERE / "gini_view1_waterfall.png", dpi=200)
    plt.close(fig)


# --------------------------------- view 2: layers across the spectrum --------
def view2():
    fig, ax = plt.subplots(figsize=(10, 6.6))
    x = np.arange(len(DIST))
    series = [(f"{lab} · CR {pct(CR[r])}", [gini[(s, d)] for d in DIST], CAT[i])
              for i, (s, lab, r) in enumerate(LAYERS)]
    series.append((f"whole package · CR {pct(CR['All occurrence'])}",
                   [gini[(PACKAGE, d)] for d in DIST], CAT[4]))
    series.append((f"QS · CR {pct(CR['QS'])}",
                   [gini[(QS, d)] for d in DIST], CAT[5]))

    for lab, ys, c in series:
        ax.plot(x, ys, color=c, linewidth=2, marker="o", ms=6, zorder=3, label=lab)
    refs = [(f"gross book · CR {pct(CR['Gross'])}",
             [gini[("Gross result", d)] for d in DIST], INK2, (0, (5, 3))),
            (f"net of occ · CR {pct(CR['net occ'])}",
             [gini[(NET_OCC, d)] for d in DIST], MUTED, (0, (2, 2))),
            (f"final net · CR {pct(CR['All'])}",
             [gini[(FINAL, d)] for d in DIST], INK2, (0, (6, 2, 1, 2)))]
    for lab, ys, c, ls in refs:
        ax.plot(x, ys, color=c, linewidth=1.4, linestyle=ls, zorder=2, label=lab)
        series.append((lab, ys, c))

    # direct labels at the right edge, pushed apart where they collide
    labs = sorted([(ys[-1], lab) for lab, ys, c in series], key=lambda t: t[0])
    ypos, gap = [], 0.028
    for y, _ in labs:
        ypos.append(max(y, ypos[-1] + gap) if ypos else y)
    for yp, (y, lab) in zip(ypos, labs):
        ax.text(x[-1] + 0.12, yp, lab, fontsize=8.5, color=INK2, va="center",
                clip_on=False)
        if yp - y > 0.004:  # hairline leader where the label was pushed away
            ax.plot([x[-1] + 0.04, x[-1] + 0.10], [y, yp], color=BASELINE,
                    linewidth=0.7, clip_on=False, zorder=1)

    ax.set_xticks(x, [f"{DNAME[d]}\n({d})" for d in DIST])
    ax.set_ylabel("gini_p of the position")
    ax.set_ylim(0, Y_MAX)
    ax.margins(x=0.05)
    tidy(ax)
    ax.legend(loc="upper left", frameon=False, fontsize=8, labelcolor=INK2, ncols=2)

    ax.set_title("Where each cover lives in the tail", fontsize=14, loc="left",
                 color=INK, pad=42)
    ax.text(0, 1.03, "Families ordered by gross-book gini: tail-weighted (right) drive "
            "up the high layers; the QS is priced near\nrisk-free everywhere; the "
            "retained final net prices above gross.",
            transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")
    fig.tight_layout(rect=(0.01, 0.01, 0.76, 0.99))
    fig.savefig(HERE / "gini_view2_tail_slope.png", dpi=200)
    plt.close(fig)


# ------------------------------------- view 3: price tag vs the gross --------
def view3():
    rows = ([("gross book", "Gross result", "Gross")]
            + [(lab, s, r) for s, lab, r in LAYERS]
            + [("whole package", PACKAGE, "All occurrence"),
               ("QS", QS, "QS"), ("final net", FINAL, "All")])
    ratio = np.array([[gini[(s, d)] / gini[("Gross result", d)] for d in DIST]
                      for _, s, _ in rows])
    nfam, nrow = len(DIST), len(rows)

    cmap = LinearSegmentedColormap.from_list("div", [DIV_LO, DIV_MID, DIV_HI])
    norm = TwoSlopeNorm(vmin=0.0, vcenter=1.0, vmax=2.4)

    fig, ax = plt.subplots(figsize=(10.6, 6.2))
    ax.pcolormesh(np.arange(nfam + 1), np.arange(nrow + 1), ratio,
                  cmap=cmap, norm=norm, edgecolors=SURFACE, linewidth=2)
    for i in range(nrow):
        for j in range(nfam):
            r, g, b = to_rgb(cmap(norm(ratio[i, j])))
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            ax.text(j + 0.5, i + 0.5, f"{ratio[i, j]:.2f}×", ha="center",
                    va="center", fontsize=10, color=INK if lum > 0.45 else "#ffffff")

    # point-estimate pane: same rows, one column per metric (values, not colors)
    metrics = [("CR", lambda r: pct(res.loc[r, "CR"])),
               ("Margin / σ", lambda r: f"{msd.loc[r, 'MSD']:+.2f}")]
    ax.axvline(nfam + 0.15, color=GRID, linewidth=1)
    for k, (name, fmt) in enumerate(metrics):
        for i, (_, _, r) in enumerate(rows):
            ax.text(nfam + 0.85 + k, i + 0.5, fmt(r), ha="center", va="center",
                    fontsize=9, color=INK2)
    for i in range(1, nrow):
        ax.hlines(i, nfam + 0.3, nfam + len(metrics) + 0.4,
                  color=GRID, linewidth=0.8)

    ax.set_xlim(0, nfam + len(metrics) + 0.5)
    ax.set_xticks(list(np.arange(nfam) + 0.5)
                  + [nfam + 0.85 + k for k in range(len(metrics))],
                  [f"{DNAME[d]}\n({d})" for d in DIST] + [m for m, _ in metrics])
    ax.set_yticks(np.arange(nrow) + 0.5, [lab for lab, _, _ in rows])
    ax.set_ylim(0, nrow)
    ax.invert_yaxis()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)

    ax.set_title("Price relative to the gross book, with point estimates",
                 fontsize=14, loc="left", color=INK, pad=46)
    ax.text(0, 1.02, "Cells: position gini ÷ gross gini per family — red dearer than "
            "the gross book, blue cheaper. Right pane: point-estimate\ncombined ratio "
            "and margin per unit of std dev (− = ceded).",
            transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")
    fig.tight_layout(rect=(0.01, 0.01, 0.99, 0.97))
    fig.savefig(HERE / "gini_view3_relative_price.png", dpi=200)
    plt.close(fig)


# -------- views 4+5: everything relative to a base book, one page -----------
# The scale symmetrizes ratios about 1: t(r) = arctan(ln r), so 2x and 1/2x sit
# equidistant from the 1x midpoint and extremes (9x, 0.03x) stay on the page.
def _sym(r):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.arctan(np.log(r))


def view45(base):
    # base "gross": how does everything compare to the book we wrote?
    # base "net":   how does everything compare to the book we keep?
    base_grid, base_res = (("Gross result", "Gross") if base == "gross"
                           else (FINAL, "All"))
    positions = ([(lab, s, r) for s, lab, r in LAYERS]
                 + [("whole package", PACKAGE, "All occurrence"), ("QS", QS, "QS")])
    refs = [("gross book", "Gross result", "Gross"), ("final net", FINAL, "All")]
    cols = [f"{d}" for d in DIST] + ["margin", "M/σ", "Div CoC"]

    def msd_pos(r):
        # ceded rows carry a sign convention (margin spent < 0); flip so every
        # M/σ is margin per unit of std dev, positive
        v = msd.loc[r, "MSD"]
        return -v if msd.loc[r, "Margin spent"] < 0 else v

    def rel_row(s, r):
        return ([gini[(s, d)] / gini[(base_grid, d)] for d in DIST]
                + [(1 - res.loc[r, "CR"]) / (1 - res.loc[base_res, "CR"]),
                   msd_pos(r) / msd_pos(base_res),
                   msd.loc[r, "Div CoC"] / msd.loc[base_res, "Div CoC"]])

    rows = ([("gross book", rel_row("Gross result", "Gross"))]
            + [(lab, rel_row(s, r)) for lab, s, r in positions]
            + [("final net", rel_row(FINAL, "All"))])
    vals = np.array([v for _, v in rows])
    nrow, ncol = vals.shape

    fig, (axh, axs) = plt.subplots(
        1, 2, figsize=(15.5, 6.8), gridspec_kw={"width_ratios": [1.15, 1]})

    # -- left: the relative matrix, colored on the symmetrized scale ---------
    cmap = LinearSegmentedColormap.from_list("div", [DIV_LO, DIV_MID, DIV_HI])
    with np.errstate(invalid="ignore", divide="ignore"):
        T = np.ma.masked_invalid(_sym(vals))     # negatives fall out of the log
    amp = float(np.abs(T).max())
    norm = TwoSlopeNorm(vmin=-amp, vcenter=0.0, vmax=amp)
    axh.pcolormesh(np.arange(ncol + 1), np.arange(nrow + 1), T,
                   cmap=cmap, norm=norm, edgecolors=SURFACE, linewidth=2)
    for i in range(nrow):
        for j in range(ncol):
            v = vals[i, j]
            if T.mask[i, j]:
                ink = INK2                       # negative Div CoC: no color
            else:
                r, g, b = to_rgb(cmap(norm(T[i, j])))
                lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                ink = INK if lum > 0.45 else "#ffffff"
            axh.text(j + 0.5, i + 0.5, f"{v:.2f}×".replace("-", "−"),
                     ha="center", va="center", fontsize=9.5, color=ink)
    axh.axvline(len(DIST), color=SURFACE, linewidth=6)  # families | point pane
    axh.set_xticks(np.arange(ncol) + 0.5, cols)
    axh.set_yticks(np.arange(nrow) + 0.5, [lab for lab, _ in rows])
    axh.set_ylim(0, nrow)
    axh.invert_yaxis()
    axh.tick_params(length=0)
    for sp in axh.spines.values():
        sp.set_visible(False)

    # -- right: the distortion spectrum only, on the same symmetric scale ----
    nd = len(DIST)
    x = np.arange(nd)
    series = [(lab, rel_row(s, r)[:nd], CAT[i])
              for i, (lab, s, r) in enumerate(positions)]
    base_lab = "gross book" if base == "gross" else "final net"
    other = refs[1] if base == "gross" else refs[0]
    axs.axhline(1.0, color=INK2, linewidth=1.4, linestyle=(0, (5, 3)),
                zorder=2, label=f"{base_lab} = 1")
    olab, oys = other[0], rel_row(other[1], other[2])[:nd]
    axs.plot(x, oys, color=INK2, linewidth=1.6, linestyle=(0, (6, 2, 1, 2)),
             zorder=3, label=olab)
    for lab, ys, c in series:
        axs.plot(x, ys, color=c, linewidth=2, marker="o", ms=6, zorder=3,
                 label=lab)
    series += [(olab, oys, INK2), (base_lab, [1.0] * nd, INK2)]

    axs.set_yscale("function",
                   functions=(_sym, lambda t: np.exp(np.tan(t))))
    lo = min(min(ys) for _, ys, _ in series) / 1.35
    hi = max(max(ys) for _, ys, _ in series) * 1.35
    axs.set_ylim(lo, hi)
    ticks = [t for t in (0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 3) if lo <= t <= hi]
    axs.set_yticks(ticks, [f"{t:g}×" for t in ticks])

    # direct labels at the right edge, in series colors, spaced on the
    # transformed scale so the gaps are visually even
    labs = sorted([(ys[-1], lab, c) for lab, ys, c in series],
                  key=lambda t: _sym(t[0]))
    tpos, gap = [], 0.055 * (_sym(hi) - _sym(lo))
    for y, *_ in labs:
        t = _sym(y)
        tpos.append(max(t, tpos[-1] + gap) if tpos else t)
    for tp, (y, lab, c) in zip(tpos, labs):
        axs.text(x[-1] + 0.12, np.exp(np.tan(tp)), lab, fontsize=8.5,
                 color=c, va="center", clip_on=False)

    axs.set_xticks(x, cols[:nd])
    axs.set_ylabel(f"× {base_lab} (arctan-log scale)")
    axs.margins(x=0.05)
    tidy(axs)
    axs.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=INK2)

    fig.suptitle(f"Every position, every metric, as a multiple of the "
                 f"{'gross book' if base == 'gross' else 'retained net book'}",
                 fontsize=14, x=0.05, ha="left", color=INK, y=0.975)
    fig.text(0.05, 0.895, "Left: unitless ratios — gini by distortion family, "
             "then margin (1−CR), margin per unit of std dev (ceded sign "
             "flipped), diversified cost of capital.\nColor is symmetric about "
             "1× on an arctan-log scale; the negative 5 xs 5 Div CoC cell takes "
             "no color. Right: the distortion spectrum, same scale.",
             fontsize=9.5, color=INK2)
    fig.tight_layout(rect=(0.01, 0.02, 0.90, 0.86))
    fig.savefig(HERE / f"gini_view45_rel_{base}_fromcsv.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    view1()
    view2()
    view3()
    view45("gross")
    view45("net")
    print("wrote view1, view2, view3, view45_rel_gross, view45_rel_net")
