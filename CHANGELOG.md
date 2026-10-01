# Changelog

## What this package promises

**Nothing, and deliberately.** `aggregate-relativity` registers into `aggregate.charts` and `aggregate.exhibits`, both provisional in the sense of [PEP 411](https://peps.python.org/pep-0411/) and outside the `aggregate` 1.0 API contract. Either may change in a minor release of the library with no deprecation period, and this package inherits that. The version starts at `0.1.0` for that reason: `1.0.0` would claim a stability that nothing underneath it offers.

The one thing that is stable in practice is `aggregate_relativity.derive`, which is pure pandas over the library's **public** frames, and those frames are in the stable core. The arithmetic is usable on its own, with no registration.

---

## 0.3.0

**[Relativity-Spectrum] the second half of the original page: the distortion spectrum.** `chart.spectrum_chart_doc(pnl, base='gross'|'net')` emits an `xy` panel with the four families on a named category axis in the gross book's own order, the multiple on a log axis, one curve per position and a faint mark at 1.0. Registered as the `relativity_spectrum` chart. Where the grid answers "what is this cover's verdict", this answers "does the verdict survive the choice of family": a line that stays on one side of the base does, and one that crosses does not. On `Capstone.PnL` the `3x2` and `5x5` layers cross between `wang` and `dual`, so theirs do not.

Needed **no new panel kind**: the families are an ordered category axis and the multiples are a quantity on a log scale, both of which the chart IR has carried since 1.0. It did want `ChartAxis.categories` (`aggregate` `1.0.0a381`) to name the ticks, without which they read 0, 1, 2, 3.

**The three leaves are now `Table`, `Grid` and `Chart`**, which were all called `Relativity`, so the Lab sub-tab row said one word three times. The y axis of the grid carries no name: the row names are position names and saying so above them is a caption on a caption.

## 0.2.0

**[Relativity-Chart] the page is now a chart as well as a table.** `chart.relativity_chart_doc(pnl, base='gross'|'net')` emits a one-panel `ChartDoc` of kind `matrix`: each position against each reading as a multiple of the base, with the position's own number beneath it, on a diverging scale neutral within five percent of the base. `register()` registers it as the `relativity` chart beside the `relativity` exhibit, which do not collide because charts and exhibits are separate registries, and returns both leaves. The chart's availability gate is the exhibit's, written once, so a P&L cannot light the table and not the picture.

The plugin still **renders nothing**: no matplotlib, and it is not a dependency. What survives from the original script's `render_view45` is its semantic content, which is which rows, which columns, what the neutral band is, and which way each row is read. The palette, the `rcParams` block, the colormap construction and the figure assembly are gone.

Requires `aggregate>=1.0.0a380`, for the `matrix` panel kind and `MatrixData` (a379) and the off-scale ratio fix (a380). That panel kind exists **because of this chart**: the library carried `heatmap`, whose payload is a numeric lattice with a bucket size and exact marginals, none of which means anything over named categories. The gap went upstream rather than into a private escape hatch here, which is the feedback loop the library's provisional tier exists for.

Two rows are read in the opposite direction from the rest, which the document says with `row_polarity`: for a book, pricing above the reference is an improvement, and for a cover bought, paying above the reference is not. A renderer that ignored it would draw a scale that is simply backwards for the gross book and the final net.

## 0.1.0

**[Reference-Plugin] first release: the `relativity` exhibit.** `derive.actuals_frame(pnl)` gives one row per position of an extended P&L's program, gross book first and final net last, with `gini <family>` for each of the four distortion families ordered by the gross book's own gini, then `CR`, `margin`, `MSD`, `SA CoC` and `Div CoC`. `derive.relativity_frame(pnl, base='gross'|'net')` scores each cell as a multiple of the base book's, dropping `CR` and `SA CoC`. `derive.classify_positions` reads the tier a cover belongs to off the gini panel's own step order, so a `bottom-up` and a `top-down` peel come out in their own orders rather than an imposed one. `register.register()` is the `aggregate.plugins` entry point, registering the exhibit for `PnL` with an availability gate that reports unavailable for a plain P&L (no `peel` clause means no positions to price).

Ported from `reference/gini_decl.py`, which drove the same page over HTTP against a running `aggregate-api` and rebuilt its numbers by parsing `greater_tables` IR documents. In process those two calls are two attributes, so `ir_to_df`, `_block_with`, `fetch_frames` and `_call` are gone. The five golden files in `reference/data/` are the approved output of that script and are the regression: `tests/test_derive.py` reproduces every number in them, so the rewrite moved nothing.

Requires `aggregate>=1.0.0a378`, for `aggregate.plugins` (a376) and `aggregate.exhibits.register_exhibit` (a378). The second exists because of this package: the relativity frame is computed from two P&L frames and is no attribute of `PnL`, which `register_simple_exhibit` cannot express.

The chart is not in this release. It needs a categorical matrix panel in the library's chart IR, which `aggregate` 1.0.0a379 adds.
