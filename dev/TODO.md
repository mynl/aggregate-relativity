# TODO

> **Live items only.** What has landed is in `CHANGELOG.md` and the git log. The
> plan this package was created from is the library's
> `V:\worktrees\aggregate_REFACTOR\dev\plan-a376-plugins-and-extension-surface.md`,
> because the plugin mechanism is the library's and this repo is one of its
> stages. Work of its own gets a plan in this directory.
>
> **Labels, not codes.** Every item carries a descriptive `[Bracket-Label]`.

## Live

- **[Relativity-Chart]** DONE (`0.2.0`): the matrix is a chart, on the library's
  new `matrix` panel kind (`aggregate` `1.0.0a379`, with the off-scale ratio fix
  at `a380`). **Still open: the right-hand distortion spectrum.** The original
  page is two panels side by side and only the left one is built. The spectrum
  is an ordinary `xy` panel over `g(s)` per family and needs no new IR at all,
  so it is a `ChartSeries` per family and a second `Panel` in the same document.

- **[Reference-Data-Duplicate]** `reference/data/grid (1).csv` is a
  browser-download sibling of `grid.csv` and the two **differ**, so one of them
  is from a different run. Neither is used by any test; the golden regression
  reads only `gini_view45_actuals*.csv`. Worth the author deciding which is
  canonical and deleting the other. Left alone for now because `reference/` is
  frozen material and nothing here should quietly delete from it.

## Ideas

- **[Relativity-Base-Choice]** `derive.relativity_frame` takes
  `base='gross'|'net'`, and the exhibit and chart currently only ever show
  gross. If the net base earns its keep, it wants a semantic option on the chart
  rather than a second registered name.

- **[Relativity-Neutral-Band]** the neutral band half-width is a rendering
  decision (5% in the original) and currently belongs to the chart document. If
  a reader wants to move it, that is a semantic option, not a renderer constant.
