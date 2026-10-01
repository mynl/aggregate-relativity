# aggregate-relativity

Relative pricing of a reinsurance program, as an [`aggregate`](https://github.com/mynl/aggregate) plugin.

Is each cover in an extended P&L's program priced above or below the book's own implied gross leve (acceptability)? A position's `gini_p` is the distortion parameter at which that position breaks even on a stand-alone basis, so a layer whose `gini_p` sits above the gross book's is priced above what the holder would itself charge, and buying it lowers the net. Each position is priced under four or five distortion families (CoC, PH, Wang, dual, TVaR) interpreted as different risk appetites, and three point estimate of profitability (margin, margin-to-standard deviation, and vs a natural capital allocation).

The plugin contributes documents to `aggregate` and nothing else: one exhibit (`Relativity: Table`) and two charts (`Grid`, the matrix, and `Chart`, the distortion spectrum). The first pill carries the plugin's name because Lab holds every installed plugin's leaves in one row. They appear in the `aggregate-api` app under its Lab tab with no change to either project. Installing this package adds the leaves; uninstalling removes them.

## Install

`aggregate`'s `1.0.0a` line is not on PyPI, so it is an editable path source during co-development. A clone needs `aggregate_REFACTOR` checked out at the place `[tool.uv.sources]` in `pyproject.toml` names, then:

```
uv sync --extra dev
```

## Use

Nothing loads on `import aggregate`. The host calls the loader, which discovers this package through its entry point:

```python
import aggregate
from aggregate import build
from aggregate.exhibits import available_exhibits, build_exhibit

aggregate.plugins.load()
pnl = build(open('my_program.agg').read())     # an xpnl, with a peel clause
[name for name, _ in available_exhibits(pnl)]  # includes 'relativity'
build_exhibit(pnl, 'relativity')
```

Or reach the arithmetic directly, with no registration at all:

```python
from aggregate_relativity import derive
derive.actuals_frame(pnl)        # each position's own numbers
derive.relativity_frame(pnl)     # each cell as a multiple of the gross book's
```

The exhibit reports itself **unavailable** for a plain P&L: without a `peel` clause there are no positions to price, so the app draws the leaf dark and shows why.

## Versioning and promises

This package registers into `aggregate.charts` and `aggregate.exhibits`, both provisional in the sense of [PEP 411](https://peps.python.org/pep-0411/), so it inherits their freedom to break at any minor release of the library. No promises.

Release notes are in `CHANGELOG.md`.

## Layout

| Path | What it is |
|---|---|
| `src/aggregate_relativity/derive.py` | The arithmetic. Pure pandas over public `aggregate` frames, no HTTP, no matplotlib |
| `src/aggregate_relativity/register.py` | The entry point: the registry calls and the leaf declarations |
| `tests/programs.py` | The two synthetic DecL programs the golden data came from |
| `reference/` | The approved original script and its output, the porting spec and the golden data. Not packaged, not imported |
