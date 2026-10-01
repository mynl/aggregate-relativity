"""``aggregate_relativity.register``: the plugin contract, end to end.

Two things are being checked. That the packaging declares the entry point the
library looks for, so an installed copy is discovered with no configuration. And
that going through ``aggregate.plugins.load()`` lands a working exhibit, which is
the whole path the plugin mechanism exists to provide.

The tests load with an **empty environment**, so discovery runs through the
declared entry point, which is the route a real install uses and the one worth
covering here. Naming the module in ``AGGREGATE_PLUGINS`` as well would discover
the same code twice under two names, and the loader would rightly refuse the
second for reusing the first's exhibit name. The library's own
``tests/test_plugins.py`` covers the environment route.

Registration is **process global** and neither registry has a removal API, so
every test here registers inside a ``try`` and drops its key in the ``finally``,
the idiom the library's own tests use.
"""

from importlib.metadata import entry_points

import pytest
from aggregate import build, plugins
from aggregate.charts import CHARTS, available_charts
from aggregate.exhibits import (
    EXHIBITS, Perspective, available_exhibits, exhibit_frames,
)

from aggregate_relativity import derive, register as register_module

from .programs import CAPSTONE, PLAIN

MODULE_PATH = 'aggregate_relativity.register'
NAME = register_module.EXHIBIT_NAME


@pytest.fixture(autouse=True)
def _clean_loader():
    """Leave the loader unloaded on both sides of every test."""
    plugins.reset_plugins()
    yield
    plugins.reset_plugins()


def _load():
    """Discover through the declared entry point, with nothing in the environment."""
    return plugins.load(env={}, force=True)


def _forget():
    """Drop the plugin's registry keys. A test's privilege, not an API."""
    EXHIBITS.pop(NAME, None)
    CHARTS.pop(register_module.CHART_NAME, None)
    CHARTS.pop(register_module.SPECTRUM_NAME, None)


@pytest.fixture(scope='module')
def capstone_pnl():
    return build(CAPSTONE)


# --- packaging ---------------------------------------------------------------

def test_the_entry_point_is_declared():
    """An installed copy is discovered with no configuration at all."""
    found = {ep.name: ep.value
             for ep in entry_points(group=plugins.ENTRY_POINT_GROUP)}
    assert found.get('relativity') == f'{MODULE_PATH}:register'


def test_importing_the_package_registers_nothing():
    """Registration is the host's decision, not a side effect of import."""
    import aggregate_relativity  # noqa: F401
    assert NAME not in EXHIBITS
    assert plugins.loaded_plugins() == []


# --- through the loader ------------------------------------------------------

def test_load_registers_the_exhibit_and_attributes_it(capstone_pnl):
    """The whole path: discovery, registration, provenance, capability, service."""
    try:
        plugin, = _load()
        assert plugin.ok, plugin.error
        assert plugin.name == 'relativity' and plugin.source == 'entry_point'
        assert plugin.version == '0.1.0'
        assert plugin.exhibits == (NAME,)
        assert set(plugin.charts) == {register_module.CHART_NAME,
                                      register_module.SPECTRUM_NAME}

        table, grid, picture = plugin.leaves
        # Read off the constants, never off their current text. Pinning the
        # literals made this case fail the moment a label was reworded, which is
        # the one edit it ought to wave through: what is worth asserting is that
        # each leaf carries *its own* label, not what that label happens to say.
        assert (table.name, table.kind, table.label) == (
            NAME, 'exhibit', register_module.EXHIBIT_LABEL)
        assert (grid.name, grid.kind, grid.label) == (
            register_module.CHART_NAME, 'chart', register_module.CHART_LABEL)
        assert (picture.name, picture.kind, picture.label) == (
            register_module.SPECTRUM_NAME, 'chart', register_module.SPECTRUM_LABEL)
        # All three distinct, and the first one names the plugin: Lab holds
        # every installed plugin's leaves in one row, so the first pill is what
        # tells a reader whose leaves these are.
        labels = [leaf.label for leaf in plugin.leaves]
        assert len(set(labels)) == 3
        assert labels[0].startswith(register_module.TITLE)
        assert not any(label.startswith(register_module.TITLE)
                       for label in labels[1:])
        for leaf in plugin.leaves:
            assert leaf.why == register_module.WHY
            assert leaf.hint, 'every leaf says what it shows'
            # Lowercase fragments: the lede renders them as `**Label**: hint`.
            assert leaf.hint[0].islower(), leaf.hint

        names = [n for n, _ in available_exhibits(capstone_pnl)]
        assert NAME in names
        assert register_module.CHART_NAME in available_charts(capstone_pnl)
        assert register_module.SPECTRUM_NAME in available_charts(capstone_pnl)

        block, frame, kw = exhibit_frames(capstone_pnl, NAME)[0]
        assert block == NAME
        assert 'caption' in kw and 'formatters' in kw
        assert list(frame.index)[0] == 'gross book'
        assert list(frame.index)[-1] == 'final net'
        # the served frame is the derivation, not a copy of it
        assert frame.equals(derive.actuals_frame(capstone_pnl))
    finally:
        _forget()


def test_insurer_serves_the_same_table(capstone_pnl):
    """No insurer override is registered, so INSURER equals RAW."""
    try:
        assert _load()[0].ok
        raw = exhibit_frames(capstone_pnl, NAME, Perspective.RAW)[0][1]
        insurer = exhibit_frames(capstone_pnl, NAME, Perspective.INSURER)[0][1]
        assert raw.equals(insurer)
    finally:
        _forget()


def test_the_leaf_is_dark_on_a_plain_pnl():
    """A P&L with no peel clause has no positions, so the page cannot answer.

    Reported unavailable rather than served empty, which is what lets the app
    draw the leaf dark and show the plugin's own ``why``.
    """
    plain = build(PLAIN)
    try:
        assert _load()[0].ok
        assert NAME not in [n for n, _ in available_exhibits(plain)]
        assert register_module.CHART_NAME not in available_charts(plain)
        assert register_module._perspectives(plain) == []
    finally:
        _forget()


def test_the_leaf_is_dark_on_an_aggregate():
    """And on an object of the wrong type entirely, by dispatch."""
    dice = build('agg RelDice dfreq [3] dsev [1:6]')
    try:
        assert _load()[0].ok
        assert NAME not in [n for n, _ in available_exhibits(dice)]
        assert register_module.CHART_NAME not in available_charts(dice)
    finally:
        _forget()
