"""The plugin entry point: what ``aggregate.plugins`` calls.

One zero-argument :func:`register`, named by ``pyproject.toml``'s
``[project.entry-points."aggregate.plugins"]`` and by ``AGGREGATE_PLUGINS`` for
the no-packaging route. It performs the registry calls and returns the
app-facing strings for what it registered: one exhibit and one chart, the same
page read as a table and as a picture.

Nothing here computes anything: the arithmetic is
:mod:`aggregate_relativity.derive`, and this module is the thin seam between it
and the library's registries.
"""

from functools import singledispatch

from aggregate import PnL
from aggregate.charts import register_chart
from aggregate.exhibits import Perspective, register_exhibit
from aggregate.plugins import PluginLeaf

from . import chart, derive

#: The registry key, the URL segment the api serves it under, and the name of
#: the document. Not ``evaluate``: the library already has a ``pricing.evaluate``
#: exhibit, a ``PnL.evaluate()`` method and an ``EvaluationResult``, and this
#: plugin consumes all three. A registry key names the *document*, not the
#: machinery it was computed from, and ``relativity`` says what the page shows.
EXHIBIT_NAME = 'relativity'

#: The matrix chart's registry key. The same word as the exhibit, and they do
#: not collide: charts and exhibits are separate registries, and the library
#: itself has a ``reins`` in both. One name for one document read two ways.
CHART_NAME = 'relativity'

#: The spectrum chart's key. Its own document rather than a second panel on the
#: matrix: the two answer different questions and a reader wants one at a time
#: at full width, which is also why they are two leaves rather than one.
SPECTRUM_NAME = 'relativity_spectrum'

TITLE = 'Relativity'

#: What each leaf's pill says. One word each: they sit in a row, and the group
#: is already called Lab and the plugin already called Relativity, so repeating
#: either on every pill says nothing. The three are what the reader is choosing
#: between: the numbers, the numbers laid out and colored, and the trend.
EXHIBIT_LABEL = 'Table'
CHART_LABEL = 'Grid'
SPECTRUM_LABEL = 'Chart'

CAPTION = (
    'Each cover priced against the gross book, under four distortion families '
    'and three point estimates. A position whose gini sits above the gross '
    "book's is priced above the holder's own acceptability, so buying it lowers "
    'the net; one below it raises the net. Reading four families at once is how '
    'a verdict that survives the choice of family is told from one that does '
    'not.'
)

WHY = 'needs an extended P&L, one built with a peel clause'

#: Percentage formats for the two ratio columns. The gini columns are distortion
#: parameters on their own scales and carry no unit, so they take the frame's
#: default; ``MSD`` is a margin per unit of standard deviation and likewise.
FORMATTERS = {'CR': '.1%', 'margin': '.1%', 'SA CoC': '.1%', 'Div CoC': '.1%'}


def _perspectives(pnl):
    """Availability: an extended P&L, and nothing else.

    Notes
    -----
    Gated on the public ratio walk having more than one row, which is what an
    extended P&L means in practice: a plain P&L's walk is empty, so there are no
    positions to price and the page would be the gross book scored against
    itself.

    Deliberately **not** gated by asking ``available_exhibits`` whether
    ``economic_waterfall`` is present, which is how the original script decided
    this. That call loops over every exhibit's own predicate, this predicate
    among them, so it would recurse without end.
    """
    walk = getattr(pnl, 'evaluation_df', None)
    if walk is None or len(walk) <= 1:
        return []
    return [Perspective.RAW, Perspective.INSURER]


@singledispatch
def chart_relativity(obj, **options):
    """The base of the chart emitter: a type this chart does not serve.

    Written out rather than taken from the library, whose ``_emitter_base`` is
    underscore prefixed and therefore outside the extension surface. Five lines
    is the price of not reaching for a private name.
    """
    raise NotImplementedError(
        f'chart {CHART_NAME!r} is not implemented for {type(obj).__name__}')


@chart_relativity.register(PnL)
def _chart_relativity(pnl, base='gross', **options):
    """The relativity matrix for an extended P&L."""
    return chart.relativity_chart_doc(pnl, base=base)


@singledispatch
def chart_relativity_spectrum(obj, **options):
    """The base of the spectrum emitter: a type this chart does not serve."""
    raise NotImplementedError(
        f'chart {SPECTRUM_NAME!r} is not implemented for {type(obj).__name__}')


@chart_relativity_spectrum.register(PnL)
def _chart_relativity_spectrum(pnl, base='gross', **options):
    """Every position's relativity across the four distortion families."""
    return chart.spectrum_chart_doc(pnl, base=base)


def _can_chart(obj):
    """The chart's availability gate: the same question the exhibit asks.

    A plain bool rather than a perspective list, since that is what
    ``register_chart`` takes. The two gates are written as one test so a P&L
    cannot light the table and not the picture.
    """
    return bool(_perspectives(obj))


def _relativity_frames(pnl):
    """Serve the actuals frame, the numbers behind the page.

    The exhibit shows the actuals rather than the multiples: a table reader can
    divide, and the multiples are what the *chart* exists to show, where the
    diverging color does the comparing.
    """
    return [(EXHIBIT_NAME, derive.actuals_frame(pnl),
             {'caption': CAPTION, 'formatters': dict(FORMATTERS)})]


def register():
    """Register this plugin's documents and declare its leaves.

    Returns
    -------
    list of aggregate.plugins.PluginLeaf
        One leaf per registered document, each carrying the label, hint and
        ``why`` this plugin wants a client to show. The loader checks every
        returned leaf against the registry keys its own before-and-after
        snapshot says this plugin added, so a leaf naming something unregistered
        is refused.
    """
    register_exhibit(EXHIBIT_NAME, TITLE, _relativity_frames, [PnL],
                     predicate=_perspectives)
    register_chart(CHART_NAME, chart_relativity, predicate=_can_chart)
    register_chart(SPECTRUM_NAME, chart_relativity_spectrum,
                   predicate=_can_chart)
    return [
        PluginLeaf(name=EXHIBIT_NAME, kind='exhibit', label=EXHIBIT_LABEL,
                   hint='each position with its own numbers, which is what '
                        'the grid is built from',
                   why=WHY),
        PluginLeaf(name=CHART_NAME, kind='chart', label=CHART_LABEL,
                   hint='each cover against the book, on a diverging scale',
                   why=WHY),
        PluginLeaf(name=SPECTRUM_NAME, kind='chart', label=SPECTRUM_LABEL,
                   hint='does the verdict survive the choice of family?',
                   why=WHY),
    ]
