# gini_decl.py — decl (an xpnl DecL program) -> the relative-pricing exhibit,
# driven live off the aggregate API (default http://127.0.0.1:19456/v1).
#
# Pipeline: POST /objects builds the P&L (and refuses anything that is not an
# extended P&L); POST /objects/{oid}/pricing/evaluate yields the gini grid
# (Step x distortion); GET /objects/{oid}/exhibit/economic_waterfall yields
# the ratio walk (CR, MSD, SA CoC, Div CoC). Responses carry greater_tables
# ir_version-1 documents; ``ir_to_df`` rebuilds DataFrames from the raw
# values riding beside the formatted text.
#
# One page per run: the relativities matrix (scaled value over the actual, in
# parens) beside the distortion spectrum. The actuals also land as a CSV in
# ./data for the exhibit framework.
#
# Run:  uv run --with pandas --with matplotlib gini_decl.py

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm, to_rgb
from matplotlib.patches import Rectangle

HERE = Path(__file__).absolute().parent
DATA_DIR = HERE / "data"
BASE_URL = "http://127.0.0.1:19456/v1"

# ---------------------------------------------------------------- palette ----
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
# the two cover families carry temperature, the members carry distinct hues,
# and the reference books stay neutral: cools = occurrence XOL, warms =
# aggregate tier, so the groups read at a glance and the members apart
XOL_COLORS = ["#2a78d6", "#1baf7a", "#4a3aa7", "#86b6ef"]  # blue aqua violet sky
PKG_OCC = "#0d366b"                                        # occ package, dashed
QS_COLORS = ["#eb6834", "#e87ba4", "#eda100"]              # orange magenta yellow
PKG_AGG = "#993c14"                                        # agg package, dashed
GROSS_COLOR, NET_COLOR = INK2, INK                         # neutral references
MK_XOL, MK_QS, MK_REF = "x", "s", "D"
# diverging cells: green = cheaper than base (good), red = dearer, grey = base
DIV_LO, DIV_MID, DIV_HI = "#008300", "#f0efec", "#e34948"

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

# ------------------------------------------------------------- API client ----
def _call(method: str, path: str, body: dict | None = None,
          base_url: str = BASE_URL, timeout: float = 600.0) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base_url + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ir_to_df(block: dict) -> pd.DataFrame:
    """A greater_tables ir_version-1 table document -> DataFrame of raw values.

    Stub cells are sparsified with rowspans (the elided cells are always the
    leading ones), so a row shorter than the column list inherits the still-
    open rowspan value for each missing level. Numeric cells carry ``raw``
    beside the formatted ``text``; strings ride as plain strings.
    """
    cols = block["columns"]
    names = [c["name"][-1] if isinstance(c["name"], list) else c["name"]
             for c in cols]
    n = len(cols)
    carry: dict[int, object] = {}
    rows = []
    for row in block["body"]:
        cells = row["cells"]
        missing = n - len(cells)
        vals = []
        for i in range(n):
            if i < missing:
                vals.append(carry[i])
                continue
            c = cells[i - missing]
            if isinstance(c, dict):
                v = c.get("raw", c.get("text"))
                if c.get("rowspan", 1) > 1:
                    carry[i] = v
            else:
                v = c
            vals.append(v)
        rows.append(vals)
    return pd.DataFrame(rows, columns=names)


def _block_with(env_blocks: list[dict], marker: str) -> dict:
    for blk in env_blocks:
        names = [c["name"][-1] if isinstance(c["name"], list) else c["name"]
                 for c in blk["columns"]]
        if marker in names:
            return blk
    raise ValueError(f"no block carries a {marker!r} column")


def fetch_frames(decl: str, base_url: str = BASE_URL,
                 log2: int | None = None, bs: float | None = None,
                 ) -> tuple[str, pd.Series, pd.DataFrame]:
    """Build the decl and return (object name, gini series, ratio walk).

    gini is indexed (Step, distortion); the walk is indexed by Step and
    carries CR, MSD, SA CoC, Div CoC, Premium spent, Margin spent.
    """
    body: dict = {"decl": decl}
    if log2 is not None:
        body["log2"] = log2
    if bs is not None:
        body["bs"] = bs
    built = _call("POST", "/objects", body, base_url)
    oid, name = built["id"], built.get("name", "")

    # interrogate the build: only an extended P&L (xpnl, with a peel clause)
    # registers the economic_waterfall exhibit this pipeline consumes
    kind = built.get("kind")
    exhibits = {e["name"] for e in built.get("capability", {})
                                        .get("exhibits", [])}
    if kind != "pnl":
        raise ValueError(
            f"decl must be an xpnl (extended P&L); {name!r} builds as "
            f"kind={kind!r}")
    if "economic_waterfall" not in exhibits:
        raise ValueError(
            f"decl must be an xpnl (extended P&L) with a peel clause; "
            f"{name!r} is a plain pnl without the economic_waterfall exhibit")

    ev = _call("POST", f"/objects/{oid}/pricing/evaluate", {}, base_url)
    grid = ir_to_df(_block_with(
        ev["exhibits"]["pricing.evaluate"]["raw"]["blocks"], "gini_p"))
    gini = grid.set_index(["Step", "distortion"])["gini_p"].astype(float)

    wf = _call("GET", f"/objects/{oid}/exhibit/economic_waterfall",
               None, base_url)
    walk = ir_to_df(_block_with(wf["blocks"], "MSD")).set_index("Step")
    return name, gini, walk


# ------------------------------------------------------- program structure ----
OCC_PKG, AGG_PKG = "All occurrence result", "All aggregate result"
FINAL_GRID, FINAL_WALK = "margin", "All"   # margin rows ARE the final net


def classify_positions(gini: pd.Series) -> list[tuple]:
    """(label, grid step, walk step, color, marker, linestyle) per position.

    Read off the grid's own step sequence, which follows the peel order: buy
    steps before ``All occurrence result`` are occurrence XOL layers (blue
    ramp), buy steps after it are aggregate-tier covers (QS oranges), and the
    two ``All ...`` steps are their packages (dashed). A program with only an
    aggregate tier has no occurrence marker: its covers are all QS oranges.
    """
    steps = list(dict.fromkeys(gini.index.get_level_values("Step")))
    xol, qs = [], []
    tier = xol if OCC_PKG in steps else qs
    for s in steps:
        if s == OCC_PKG:
            tier = qs
        elif (s.endswith(" result") and s not in ("Gross result", AGG_PKG)):
            tier.append(s[:-len(" result")])
    out = []
    for i, nm in enumerate(xol):
        c = XOL_COLORS[min(i, len(XOL_COLORS) - 1)]
        out.append((nm, f"{nm} result", nm, c, MK_XOL, "solid"))
    if OCC_PKG in steps:
        out.append(("occ package", OCC_PKG, "All occurrence",
                    PKG_OCC, MK_XOL, (0, (5, 3))))
    for i, nm in enumerate(qs):
        c = QS_COLORS[min(i, len(QS_COLORS) - 1)]
        out.append((nm, f"{nm} result", nm, c, MK_QS, "solid"))
    if AGG_PKG in steps:
        out.append(("agg package", AGG_PKG, "All aggregate",
                    PKG_AGG, MK_QS, (0, (5, 3))))
    return out


# ---------------------------------------------------------------- the page ----
DNAME = {"ph": "Proportional hazard", "wang": "Wang",
         "dual": "Dual moment", "tvar": "TVaR"}


def _sym(r):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.arctan(np.log(r))


def _tidy(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(BASELINE)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(length=0)


def _save(fig, out_png):
    # overwriting an existing PNG on this drive intermittently fails with
    # EINVAL; a fresh create never does, so clear the target first
    Path(out_png).unlink(missing_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def render_view45(gini: pd.Series, walk: pd.DataFrame, out_png: Path,
                  base: str = "gross", label: str = "",
                  neutral: float = 0.05) -> None:
    """One page: relativities matrix (with actuals) + distortion spectrum.

    ``base`` anchors every ratio; gross is the default because it is the one
    book the reinsurance choices cannot move. ``neutral`` is the signal-free
    band half-width: within base*(1 +/- neutral) a cell stays grey.
    """
    if base not in ("gross", "net"):
        raise ValueError("base is 'gross' or 'net'")
    dist = sorted(DNAME, key=lambda d: gini[("Gross result", d)])
    nd = len(dist)
    base_grid, base_walk = (("Gross result", "Gross") if base == "gross"
                            else (FINAL_GRID, FINAL_WALK))
    base_lab = "gross book" if base == "gross" else "final net"
    positions = classify_positions(gini)
    cols = list(dist) + ["margin", "MSD", "Div CoC"]

    def msd_pos(r):
        v = float(walk.loc[r, "MSD"])
        return -v if float(walk.loc[r, "Margin spent"]) < 0 else v

    def rel_row(s, r):
        return ([gini[(s, d)] / gini[(base_grid, d)] for d in dist]
                + [(1 - float(walk.loc[r, "CR"]))
                   / (1 - float(walk.loc[base_walk, "CR"])),
                   msd_pos(r) / msd_pos(base_walk),
                   float(walk.loc[r, "Div CoC"])
                   / float(walk.loc[base_walk, "Div CoC"])])

    def act_row(s, r):
        return ([gini[(s, d)] for d in dist]
                + [1 - float(walk.loc[r, "CR"]), msd_pos(r),
                   float(walk.loc[r, "Div CoC"])])

    rows = ([("gross book", "Gross result", "Gross", GROSS_COLOR)]
            + [(lab, s, r, c) for lab, s, r, c, *_ in positions]
            + [("final net", FINAL_GRID, FINAL_WALK, NET_COLOR)])
    vals = np.array([rel_row(s, r) for _, s, r, _ in rows])
    acts = np.array([act_row(s, r) for _, s, r, _ in rows])
    nrow, ncol = vals.shape
    n_occ = sum(1 for _, _, _, _, mk, _ in positions if mk == MK_XOL)

    def act_fmt(j, v):
        if j < nd:
            return f"{v:.3f}"
        if cols[j] == "MSD":
            return f"{v:.2f}"
        return f"{100 * v:.1f}%"

    fig, (axh, axs) = plt.subplots(
        1, 2, figsize=(15.5, 7.6),
        gridspec_kw={"width_ratios": [1.18, 1], "wspace": 0.28})

    # -- left: the relative matrix, scaled value over the actual -------------
    # a hard neutral band: within 5% of the base is signal-free grey, and the
    # first step outside it is unmistakably green or red, deepening outward
    T = np.ma.masked_invalid(_sym(vals))         # negatives fall out of the log
    amp = float(np.abs(T).max())
    p95 = float(np.clip(0.5 + _sym(1 - neutral) / (2 * amp), 0.02, 0.49))
    p105 = float(np.clip(0.5 + _sym(1 + neutral) / (2 * amp), 0.51, 0.98))
    cmap = LinearSegmentedColormap.from_list("div", [
        (0.0, DIV_LO), (p95, "#8fca8f"), (p95, DIV_MID),
        (p105, DIV_MID), (p105, "#f0a09f"), (1.0, DIV_HI)])
    norm = TwoSlopeNorm(vmin=-amp, vcenter=0.0, vmax=amp)
    # book rows (gross book, final net) score with kept polarity: pricing
    # above the base is an improvement, so their color scale is mirrored;
    # cession rows keep buy polarity (above the base = paid more = red)
    Tcol = T.copy()
    Tcol[0] = -T[0]
    Tcol[-1] = -T[-1]
    mask = np.ma.getmaskarray(T)
    PG = 0.35                       # families | point pane gap, in cell units
    xoff = np.where(np.arange(ncol) < nd, 0.0, PG)
    axh.pcolormesh(np.arange(nd + 1), np.arange(nrow + 1), Tcol[:, :nd],
                   cmap=cmap, norm=norm, edgecolors=SURFACE, linewidth=2)
    axh.pcolormesh(np.arange(nd, ncol + 1) + PG, np.arange(nrow + 1),
                   Tcol[:, nd:], cmap=cmap, norm=norm, edgecolors=SURFACE,
                   linewidth=2)
    for i in range(nrow):
        for j in range(ncol):
            if mask[i, j]:
                ink, ink2 = INK2, MUTED           # negative Div CoC: no color
            else:
                r, g, b = to_rgb(cmap(norm(Tcol[i, j])))
                lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                dark = lum <= 0.45
                ink = "#ffffff" if dark else INK
                ink2 = "#ffffffd0" if dark else INK2
            axh.text(j + 0.5 + xoff[j], i + 0.36,
                     f"{vals[i, j]:.2f}×".replace("-", "−"),
                     ha="center", va="center", fontsize=9.5, color=ink)
            axh.text(j + 0.5 + xoff[j], i + 0.72,
                     f"({act_fmt(j, acts[i, j]).replace('-', '−')})",
                     ha="center", va="center", fontsize=6.8, color=ink2)
    for y in {1, 1 + n_occ, nrow - 1}:    # the program's tiers
        if 0 < y < nrow:
            axh.hlines(y, 0, ncol + PG, color=SURFACE, linewidth=5, zorder=4)
    axh.set_xlim(0, ncol + PG)
    axh.set_yticks([])   # the key is drawn in figure coords after layout
    axh.set_xticks(np.arange(ncol) + 0.5 + xoff, cols)
    for j, tick in enumerate(axh.get_xticklabels()):
        tick.set_color(INK if j < nd else MUTED)
    axh.text(nd / 2, -0.28, "distortion normalized risk parameter",
             ha="center", va="bottom", fontsize=8, color=MUTED)
    axh.text(nd + PG + (ncol - nd) / 2, -0.28, "point estimates", ha="center",
             va="bottom", fontsize=8, color=MUTED)
    axh.set_ylim(0, nrow)
    axh.invert_yaxis()
    axh.tick_params(length=0)
    for sp in axh.spines.values():
        sp.set_visible(False)

    # -- right: the distortion spectrum --------------------------------------
    x = np.arange(nd)
    series = []
    for lab, s, r, c, mk, ls in positions:
        ys = rel_row(s, r)[:nd]
        lw = 2.4 if ls != "solid" else 2
        # an "x" marker is strokes only, so the surface ring would erase it
        mkw = dict(ms=7, mew=1.8) if mk == "x" else \
            dict(ms=6, mec=SURFACE, mew=0.8)
        axs.plot(x, ys, color=c, linewidth=lw, marker=mk, zorder=3,
                 linestyle=ls, **mkw)
        series.append((lab, ys, c))
    for lab, ys, c, ls in (
            ("gross book", rel_row("Gross result", "Gross")[:nd],
             GROSS_COLOR, "solid"),
            ("final net", rel_row(FINAL_GRID, FINAL_WALK)[:nd],
             NET_COLOR, (0, (5, 3)))):
        if lab == base_lab:
            lab += " = 1"
        axs.plot(x, ys, color=c, linewidth=1.8, linestyle=ls, marker=MK_REF,
                 ms=5.5, zorder=3, mec=SURFACE, mew=0.8)
        series.append((lab, ys, c))

    axs.set_yscale("function", functions=(_sym, lambda t: np.exp(np.tan(t))))
    lo = min(min(ys) for _, ys, _ in series) / 1.35
    hi = max(max(ys) for _, ys, _ in series) * 1.35
    axs.set_ylim(lo, hi)
    # the verdict wash: dearer than the base book above 1x, cheaper below
    axs.axhspan(1.0, hi, color=DIV_HI, alpha=0.05, zorder=0, linewidth=0)
    axs.axhspan(lo, 1.0, color=DIV_LO, alpha=0.05, zorder=0, linewidth=0)
    axs.text(0.015, 0.985, f"dearer than {base_lab}", transform=axs.transAxes,
             fontsize=8, color="#b23a39", va="top")
    axs.text(0.015, 0.015, f"cheaper than {base_lab}", transform=axs.transAxes,
             fontsize=8, color="#006300", va="bottom")
    ticks = [t for t in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5,
                         1, 2, 3, 5, 10, 20, 50) if lo <= t <= hi]
    axs.set_yticks(ticks, [f"{t:g}×" for t in ticks])

    # direct line labels. The end column is solved as an ORDER-PRESERVING
    # 1-D packing, so the vertical order of labels always matches the
    # vertical order of the line endpoints; a label the solve would push far
    # from its endpoint is relocated to open whitespace along its own line
    # and the column re-solved. All geometry runs in (x, t) space,
    # t = arctan(log y), where vertical distance is what the eye sees.
    axs.set_xlim(-0.25, nd - 1 + 1.05)
    x_end = nd - 1
    t_lo, t_hi = _sym(lo), _sym(hi)
    # one 8.5pt label is ~2.5% of the axis height; 3.5% keeps a thin breath
    # of space between stacked labels
    gap = 0.035 * (t_hi - t_lo)
    ts_of = {lab: _sym(np.asarray(ys, dtype=float)) for lab, ys, _ in series}

    def half_w(lab):                    # crude text half-width in x units
        return 0.031 * len(lab) + 0.05

    def solve_stack(wants):
        # top-down pass packs each label at its endpoint or just under its
        # neighbour; bottom-up pass lifts anything pushed below the floor
        pos = []
        top = t_hi - gap / 2
        for t in wants:
            top = min(t, top)
            pos.append(top)
            top -= gap
        floor = t_lo + gap / 2
        for i in range(len(pos) - 1, -1, -1):
            pos[i] = max(pos[i], floor)
            floor = pos[i] + gap
        return pos

    def clear_of_lines(xc, t, hw, own):
        for lab2, _, _ in series:
            if lab2 == own:
                continue
            for xs_ in np.linspace(max(0, xc - hw), min(x_end, xc + hw), 5):
                if abs(float(np.interp(xs_, x, ts_of[lab2])) - t) < 0.7 * gap:
                    return False
        return True

    column = sorted([(float(ts_of[lab][-1]), lab, c) for lab, _, c in series],
                    key=lambda e: -e[0])
    floated = []                        # (xa, t, lab, c, hw)

    def try_float(lab, c):
        hw = half_w(lab)
        for xa in np.arange(x_end - 0.45, 0.27, -0.5):
            t_line = float(np.interp(xa, x, ts_of[lab]))
            for dt in (0.85 * gap, -0.85 * gap):
                t2 = t_line + dt
                if not (t_lo + gap / 2 < t2 < t_hi - gap / 2):
                    continue
                if any(abs(xa - fx) < hw + fw and abs(t2 - ft) < gap
                       for fx, ft, _, _, fw in floated):
                    continue
                if not clear_of_lines(xa, t2, hw, lab):
                    continue
                floated.append((xa, t2, lab, c, hw))
                return True
        return False

    for _ in range(len(column)):
        pos = solve_stack([t for t, _, _ in column])
        disp = [abs(p - t) for p, (t, _, _) in zip(pos, column)]
        worst = int(np.argmax(disp))
        if disp[worst] <= 2.2 * gap:
            break
        _, lab, c = column[worst]
        if not try_float(lab, c):
            break
        column.pop(worst)
    for xa, t2, lab, c, hw in floated:
        axs.text(xa, np.exp(np.tan(t2)), lab, fontsize=8.5, color=c,
                 ha="center", va="center")
    for p, (t_end, lab, c) in zip(pos, column):
        axs.text(x_end + 0.12, np.exp(np.tan(p)), lab, fontsize=8.5,
                 color=c, va="center")
        if abs(p - t_end) > 1.2 * gap:      # visibly displaced: tie it back
            axs.plot([x_end + 0.02, x_end + 0.10],
                     [np.exp(np.tan(t_end)), np.exp(np.tan(p))],
                     color=c, linewidth=0.7, alpha=0.7, clip_on=False,
                     zorder=2)

    axs.set_xticks(x, cols[:nd])
    for tick in axs.get_xticklabels():
        tick.set_color(INK)
    axs.set_xlabel("distortion family: tail aversion increases →",
                   fontsize=9, color=INK2)
    # scale on the right, away from the shared key between the panels
    axs.yaxis.tick_right()
    axs.yaxis.set_label_position("right")
    axs.set_ylabel(f"× {'net' if base == 'net' else 'gross'}")
    _tidy(axs)
    axs.spines["left"].set_visible(False)
    axs.spines["right"].set_visible(True)
    axs.spines["right"].set_color(BASELINE)

    fig.suptitle(label, fontsize=14, x=0.05, ha="left", color=INK, y=0.975)
    pc = f"{100 * neutral:g}%"
    fig.text(0.05, 0.90, "Cells show the multiple of the "
             f"{base_lab} over the actual value in parens. Green: at least "
             f"{pc} cheaper than the {base_lab}'s price of risk (good). Red: "
             f"at least {pc} dearer. Grey: within {pc}.\nBook rows (gross "
             "book, final net) score the other way round: above the base is "
             "an improvement, green. Cools: occurrence XOL. Warms: aggregate "
             "tier. Dashed: packages.",
             fontsize=9.5, color=INK2)
    # explicit geometry: tight_layout refuses axes with off-plot artists
    fig.subplots_adjust(left=0.035, right=0.945, top=0.775, bottom=0.10,
                        wspace=0.30)
    # the key, name | swatch, the swatch hugging the chart's left edge with
    # the same breath of space as sits between name and swatch
    ph_, ps_ = axh.get_position(), axs.get_position()
    row_h = ph_.height / nrow
    chip_w, chip_h = 0.010, row_h * 0.42
    chip_x = ps_.x0 - chip_w - 0.005
    for i, (lab, _, _, c) in enumerate(rows):
        yc = ph_.y1 - (i + 0.5) * row_h
        fig.add_artist(Rectangle((chip_x, yc - chip_h / 2), chip_w, chip_h,
                                 transform=fig.transFigure, color=c, lw=0))
        fig.text((ph_.x1 + chip_x) / 2, yc, lab, ha="center", va="center",
                 fontsize=9.5, color=INK)
    _save(fig, out_png)


# --------------------------------------------------------- actuals frame ----
def actuals_frame(gini: pd.Series, walk: pd.DataFrame) -> pd.DataFrame:
    """The page's rows with their actual numbers, for the exhibit framework:
    gini by family, CR, margin = 1 − CR, M/σ (ceded sign flipped), CoCs."""
    dist = sorted(DNAME, key=lambda d: gini[("Gross result", d)])
    rows = ([("gross book", "Gross result", "Gross")]
            + [(lab, s, r) for lab, s, r, *_ in classify_positions(gini)]
            + [("final net", FINAL_GRID, FINAL_WALK)])
    recs = {}
    for lab, s, r in rows:
        msd = float(walk.loc[r, "MSD"])
        if float(walk.loc[r, "Margin spent"]) < 0:
            msd = -msd
        cr = float(walk.loc[r, "CR"])
        recs[lab] = ([float(gini[(s, d)]) for d in dist]
                     + [cr, 1 - cr, msd,
                        float(walk.loc[r, "SA CoC"]),
                        float(walk.loc[r, "Div CoC"])])
    cols = [f"gini {d}" for d in dist] + ["CR", "margin", "MSD",
                                          "SA CoC", "Div CoC"]
    return pd.DataFrame.from_dict(recs, orient="index", columns=cols)


# ------------------------------------------------------------ deliverable ----
def gini_view45(decl: str, out_png: str | Path, label: str = "",
                base: str = "gross", neutral: float = 0.05,
                base_url: str = BASE_URL, log2: int | None = None,
                bs: float | None = None) -> Path:
    """decl (an xpnl DecL program) -> the one-page relativities PNG."""
    name, gini, walk = fetch_frames(decl, base_url, log2, bs)
    out = Path(out_png)
    render_view45(gini, walk, out, base=base, label=label or name,
                  neutral=neutral)
    return out


def gini_view45_rel_net(decl: str, out_png: str | Path, **kw) -> Path:
    """Back-compat wrapper: the same page on the net base."""
    return gini_view45(decl, out_png, base="net", **kw)


# --------------------------------------------------------------- programs ----
CAPSTONE = """xpnl Capstone.PnL
  derive premium
  less
    agg Capstone.FullProgram
      [2000 5000 10000 3000 1000] premium as GWP at [0.95 0.95 0.9 0.85 0.75] lr
      [500 1000 5000 10000 5000] xs [0 0 0 0 1000]
      sev 151.63266492815836 * lognorm 1
        picks [500 1000 2000 5000 10000] [14900 2250 1250 500 50]
      occurrence net of
        50% po 500 xs 500 deposit 3000 as "500x500" and
        90% po 1000 xs 1000 deposit 1750 as "1x1" and
        95% po 3000 xs 2000 rol 0.25 as "3x2" and
        5000 xs 5000 rol 0.03 as "5x5"
      mixed gamma 0.125
      aggregate net of
        75% po inf xs 0 rate 1 cede 0.325 as QS
  less
    0.25 premium expenses as "G&A"
  peel bottom-up
"""

PNL_LOSS_RATIO = """xpnl PnLLossRatio
  1000 premium
  less
    agg PnL.D
      1000 premium at 0.5 lr
      2000 xs 0
      sev 90 *  lognorm 2
      occurrence net of 75% po 500 xs 500 rol 35% as "Occ 1" and
      95% po 500 xs 1000 rol 17.5% as "Occ 2" and
      100% po 500 xs 1500 rol 15% as "Occ 3"
      mixed gamma 0.25
    aggregate net of
      75% po 500 xs 0 rate .85 cede 42.5% as "Ltd QS" and
      100% po 1400 xs 600 rol 0.07 as "Agg Stop"
  less
    25% premium expense as "G&A"
  peel top-down
"""


def _run(decl: str, suffix: str, label_extra: str = "") -> None:
    name, gini, walk = fetch_frames(decl)
    label = f"{name}{', ' + label_extra if label_extra else ''}"
    # gross base only: gross is the one book the reinsurance choices cannot
    # move, so cover verdicts do not lean on each other (net stays plumbed)
    render_view45(gini, walk, HERE / f"gini_view45_rel_gross{suffix}.png",
                  base="gross", label=label)
    DATA_DIR.mkdir(exist_ok=True)
    csv = DATA_DIR / f"gini_view45_actuals{suffix}.csv"
    csv.unlink(missing_ok=True)
    actuals_frame(gini, walk).to_csv(csv)
    print(f"wrote gini_view45_rel_gross{suffix}.png "
          f"(+ data/{csv.name}); net CR {float(walk.loc[FINAL_WALK, 'CR']):.3f}")


if __name__ == "__main__":
    for cede, suffix in ((0.325, ""), (0.31, "_qs31"), (0.30, "_qs30"),
                         (0.29, "_qs29")):
        _run(CAPSTONE.replace("cede 0.325", f"cede {cede}"), suffix,
             f"QS cede {100 * cede:g}%")
    _run(PNL_LOSS_RATIO, "_PnLLossRatio")
