# Execution notes, [relativity-plugin] step of plan-0.10.0-version-source

Executed 2026-10-14 as 0.10.0, after the [library] step landed as aggregate 1.2.1. The plan text is shared byte identical with aggregate-api (canonical), aggregate and aggregate-ntt; these notes are this repository's alone.

## Divergences

- **`uv.lock` was already stale** before this step: it recorded `aggregate` 1.0.0a395, this package at 0.8.0, and the library's since removed `pytest-testmon` extra. The relock clears all three, and both editable packages now appear without a `version`, as uv writes a dynamic one.
- **The `[tool.uv.sources]` note in `CLAUDE.md`** ("after the library bumps, re-sync so this package's floor resolves") is left as it is. It concerns resolving a raised dependency floor, which is a dependency change, not a bump.
- **No `dev/TODO.md` item existed** for this plan, so none was ticked.
- **`dev/done/` is new.** This repository had never kept a plan, so retiring this one created the directory.
- **The author's uncommitted `src/aggregate_relativity/chart.py`** was in the tree when the suite ran and is left out of the commit.

## Checks

- `UV_PROJECT_ENVIRONMENT=V:/dev/venvs/aggregate_relativity uv run --no-sync pytest -q`: 58 passed, `test_register.py` included. The environment's distribution metadata still read `0.8.0` at the time, so the green `plugin.version == __version__` is the library reading the attribute live, with no sync.
- `uv build --wheel` produced `aggregate_relativity-0.10.0-py3-none-any.whl`.
