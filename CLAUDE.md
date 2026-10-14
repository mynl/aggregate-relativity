# CLAUDE.md

Guidance for Claude Code in this repository. It adds to `V:\dev\CLAUDE.md` and the house rules above it; anything not stated here is governed by those.

## Project Overview

`aggregate-relativity` is an **`aggregate` plugin**: a separate distribution that contributes charts and exhibits to the library through `aggregate.plugins`, and appears in the `aggregate-api` app under its Lab tab. It is the first such plugin, so it is also the worked example other plugins are written from. Author: Stephen J. Mildenhall.

The document it contributes: for each cover an extended P&L's program buys, is it priced above or below the book's own acceptability? See `README.md` for the reading and `CHANGELOG.md` for what has landed.

## The one rule that matters most

**This package lives in its own distribution, and that is not negotiable.** The library deleted an `extensions/` subpackage at `1.0.0a12` for exactly this material, because experimental code inside the library becomes the library's dependency surface, its test burden and its stability question. Nothing here ever moves into `aggregate`.

**The corollary: no underscore-prefixed name from `aggregate`, ever.** The extension surface is named in `docs/3_reference/3_x_API_Stability.rst` in the library and covers no private name. If something needed is not on the public surface, that is an **upstream request against `aggregate`**, not a reach into `_pnl` and not a local reimplementation. That route has been taken once already and it worked: `aggregate.exhibits.register_exhibit` exists at library `a378` because `register_simple_exhibit` could not express an exhibit over a computed frame.

Two consequences worth remembering, both already paid for:

- The availability gate reads `len(pnl.waterfall_df) > 1`, **not** the library's private `_tower` flag and **not** `available_exhibits(pnl)`. The second would recurse: `available_exhibits` calls every exhibit's predicate, this one among them. It read `pnl.evaluation_df` until 0.8.0, behind a `getattr` default that turned the library's removal of that property into a silently dark Lab tab; the gate now type-tests first and reads the walk undefended, so the next removal is loud.
- A chart emitter hand-rolls its `singledispatch` base rather than calling the library's private `charts._emitter_base`.

## Commands

Use `uv`. The environment lives on the dev drive and is reached by `UV_PROJECT_ENVIRONMENT`, so nothing about it sits in the tree:

```
UV_PROJECT_ENVIRONMENT=V:/dev/venvs/aggregate_relativity uv sync --extra dev
UV_PROJECT_ENVIRONMENT=V:/dev/venvs/aggregate_relativity uv run --no-sync pytest -q
```

`UV_LINK_MODE=copy` is needed when invoking `uv` from a plain shell here, as in the library.

`aggregate` is an **editable path source** (`[tool.uv.sources]`), because the `1.0.0a` line is not on PyPI. It points at `../../worktrees/aggregate_REFACTOR` relatively: never write a drive letter into the tree. After the library bumps, re-sync so this package's floor resolves.

## Testing

`uv run pytest` is the whole gate; the suite is about 9 seconds, so there are no tiers here.

**`tests/test_derive.py` is a golden regression and it is the point of the repo.** The page was already correct and its answers were accepted before the port, so the rewrite off the original's HTTP-and-parse route onto the library's public frames must move **no number**. `reference/data/gini_view45_actuals*.csv` are the approved outputs of the two synthetic programs in `tests/programs.py`. A number that moves is a porting bug, never a design choice. If one moves because the *library* changed a definition, say so explicitly and get it ruled on before recapturing a golden file.

**Registration is process global.** Neither `CHARTS` nor `EXHIBITS` has a removal API, so every test registers inside a `try` and drops its key in the `finally`. That is the library's own idiom.

**Load with an empty environment** (`plugins.load(env={}, force=True)`), so discovery runs through the declared entry point. Naming the module in `AGGREGATE_PLUGINS` as well discovers the same code twice under two names, and the loader rightly refuses the second for reusing the first's exhibit name.

## `reference/` is frozen

It holds the approved original (`gini_decl.py`, `gini_views.py`), its PNG output and the golden CSVs. It is the porting spec and the regression data. **Not packaged, not imported, not edited.** The two DecL programs are transcribed into `tests/programs.py` rather than imported from it, so the spec is not a dependency of the thing it specifies.

The material was authored on `X:`, which is wiped nightly, and this copy is the only one.

`.gitignore` blocks `*.csv` and then exempts `reference/data/*.csv`. That exemption is deliberate and must stay: those files are outputs of synthetic programs, so they are fixtures rather than data, and the firewall is satisfied.

## Versioning

SemVer from `0.1.0`, **a declared departure** from the house rule's "starting at 1.0.0". The reason is in `CHANGELOG.md`: this package registers into two PEP 411 provisional modules and inherits their freedom to break, so `1.0.0` would claim a stability nothing underneath it offers. The house rule exists to stop version numbers crawling, not to force a stability claim.

Every capability change bumps the minor. `CHANGELOG.md` gets its section at the bump, never deferred. The version is written in **one** place, the literal `__version__` in `src/aggregate_relativity/__init__.py`. `pyproject.toml` reads it from there (`dynamic = ["version"]`) and carries no version line. A bump edits that line and needs no sync: `aggregate.plugins` reports the live attribute, so an editable install is never stale.

## Commits

Claude commits version bumps, one bump per commit, as in the library. Subject is one line, no body and no trailers:

```
[Descriptive-Label] 0.2.0: terse summary of what landed
```

**Never push.** Anything that does not bump is left uncommitted for the author.

## Plans

The canonical plan for this package's creation is in the **library**, `V:\worktrees\aggregate_REFACTOR\dev\plan-a376-plugins-and-extension-surface.md`, because the plugin mechanism is the library's and this repo is one of its stages. Later work of its own gets a plan in `dev/` here.
