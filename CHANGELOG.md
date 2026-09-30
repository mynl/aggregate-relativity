# Changelog

## What this package promises

**Nothing, and deliberately.** `aggregate-relativity` registers into `aggregate.charts` and `aggregate.exhibits`, both provisional in the sense of [PEP 411](https://peps.python.org/pep-0411/) and outside the `aggregate` 1.0 API contract. Either may change in a minor release of the library with no deprecation period, and this package inherits that. The version starts at `0.1.0` for that reason: `1.0.0` would claim a stability that nothing underneath it offers.

The one thing that is stable in practice is `aggregate_relativity.derive`, which is pure pandas over the library's **public** frames, and those frames are in the stable core. The arithmetic is usable on its own, with no registration.

---

## 0.1.0

**[Reference-Plugin] first release: the `relativity` exhibit.** `derive.actuals_frame(pnl)` gives one row per position of an extended P&L's program, gross book first and final net last, with `gini <family>` for each of the four distortion families ordered by the gross book's own gini, then `CR`, `margin`, `MSD`, `SA CoC` and `Div CoC`. `derive.relativity_frame(pnl, base='gross'|'net')` scores each cell as a multiple of the base book's, dropping `CR` and `SA CoC`. `derive.classify_positions` reads the tier a cover belongs to off the gini panel's own step order, so a `bottom-up` and a `top-down` peel come out in their own orders rather than an imposed one. `register.register()` is the `aggregate.plugins` entry point, registering the exhibit for `PnL` with an availability gate that reports unavailable for a plain P&L (no `peel` clause means no positions to price).

Ported from `reference/gini_decl.py`, which drove the same page over HTTP against a running `aggregate-api` and rebuilt its numbers by parsing `greater_tables` IR documents. In process those two calls are two attributes, so `ir_to_df`, `_block_with`, `fetch_frames` and `_call` are gone. The five golden files in `reference/data/` are the approved output of that script and are the regression: `tests/test_derive.py` reproduces every number in them, so the rewrite moved nothing.

Requires `aggregate>=1.0.0a378`, for `aggregate.plugins` (a376) and `aggregate.exhibits.register_exhibit` (a378). The second exists because of this package: the relativity frame is computed from two P&L frames and is no attribute of `PnL`, which `register_simple_exhibit` cannot express.

The chart is not in this release. It needs a categorical matrix panel in the library's chart IR, which `aggregate` 1.0.0a379 adds.
