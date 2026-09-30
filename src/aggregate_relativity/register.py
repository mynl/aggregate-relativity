"""The plugin entry point: what ``aggregate.plugins`` calls.

One zero-argument :func:`register`, named by ``pyproject.toml``'s
``[project.entry-points."aggregate.plugins"]`` and by ``AGGREGATE_PLUGINS`` for
the no-packaging route. It performs the registry calls and returns the
app-facing strings for what it registered.

Nothing here computes anything: the arithmetic is
:mod:`aggregate_relativity.derive`, and this module is the thin seam between it
and the library's registries.
"""

from aggregate import PnL
from aggregate.exhibits import Perspective, register_exhibit
from aggregate.plugins import PluginLeaf

from . import derive

#: The registry key, the URL segment the api serves it under, and the name of
#: the document. Not ``evaluate``: the library already has a ``pricing.evaluate``
#: exhibit, a ``PnL.evaluate()`` method and an ``EvaluationResult``, and this
#: plugin consumes all three. A registry key names the *document*, not the
#: machinery it was computed from, and ``relativity`` says what the page shows.
EXHIBIT_NAME = 'relativity'

TITLE = 'Relativity'

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
    return [
        PluginLeaf(name=EXHIBIT_NAME, kind='exhibit', label=TITLE,
                   hint='each cover priced against the gross book',
                   why=WHY),
    ]
