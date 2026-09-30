# TODO

> **Live items only.** What has landed is in `CHANGELOG.md` and the git log. The
> plan this package was created from is the library's
> `V:\worktrees\aggregate_REFACTOR\dev\plan-a376-plugins-and-extension-surface.md`,
> because the plugin mechanism is the library's and this repo is one of its
> stages. Work of its own gets a plan in this directory.
>
> **Labels, not codes.** Every item carries a descriptive `[Bracket-Label]`.

## Live

- **[Relativity-Chart]** the matrix and spectrum page as a chart. The exhibit
  landed at `0.1.0` and the chart needs the categorical matrix panel the library
  adds at `1.0.0a379`: named categorical rows against named categorical columns,
  two texts per cell (the multiple, and the actual beneath it), and a diverging
  scale with a hard neutral band at plus or minus five percent. The right-hand
  distortion spectrum is an ordinary `xy` panel and needs nothing new.

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
