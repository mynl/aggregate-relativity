"""``aggregate_relativity``: the relative-pricing page, as an ``aggregate`` plugin.

Contributes one exhibit and one chart to :mod:`aggregate` through
:mod:`aggregate.plugins`, so they appear in the ``aggregate-api`` app under its
Lab tab with no change to either project.

The document: each cover an extended P&L's program buys, priced against the gross
book, under four distortion families and three point estimates. A cover whose
``gini_p`` sits above the gross book's is priced above what the holder would
itself charge.

Nothing is imported here. The entry point is
``aggregate_relativity.register:register``, and importing this package must not
register anything: the host decides when registration happens, by calling
:func:`aggregate.plugins.load`. Reach the pieces by submodule import::

    from aggregate_relativity import derive
    derive.actuals_frame(pnl)

This package registers into :mod:`aggregate.charts` and
:mod:`aggregate.exhibits`, both **provisional in the sense of PEP 411**, so it
inherits their freedom to break at any minor release of the library. That is
what the version below says, and why it does not start at 1.0.
"""

# The one place the version is written. A plain literal on purpose: setuptools
# reads it statically for the wheel, and aggregate.plugins reports it live, so
# an editable install never reports a stale number after a bump.
__version__ = "0.10.0"
__author__ = 'Stephen J. Mildenhall'
