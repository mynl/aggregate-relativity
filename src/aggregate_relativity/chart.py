"""The relativity chart: the matrix, as a chart document.

The plugin renders **nothing**. It emits a
:class:`~aggregate.charts.ir.ChartDoc` and the existing renderers draw it, the
app's ECharts adapter in the browser and
:func:`aggregate.plots.plot_chartdoc` for a figure on disk. There is no
matplotlib here and it is not a dependency of this package: a plugin that drew
its own figures would be a second rendering pipeline beside the library's, and
the two would diverge within a month.

What survives from the original script's ``render_view45`` is its **semantic**
content, which is all that was ever worth keeping: which rows, which columns,
what the neutral band is, and which way each row is read. The palette, the
``rcParams`` block, the colormap construction and the figure assembly are gone.

Notes
-----
The panel kind this emits, ``'matrix'``, exists because of this chart. The
library's chart IR carried ``'heatmap'``, whose payload is a numeric lattice
with a bucket size and exact marginals, and none of that means anything over
named categories. Rather than bend one into the other, the gap was taken
upstream and ``aggregate`` 1.0.0a379 added the kind, which is the feedback loop
the provisional tier exists for. See the library's
``dev/done/plan-a376-plugins-and-extension-surface.md`` section 12.
"""

from aggregate.charts import (
    ChartAxis, ChartDoc, ChartSeries, Mark, MatrixData, Panel,
)

from . import derive

#: How wide a departure from the base has to be before it means anything, as a
#: fraction of the base. Within plus or minus this the cell is signal free.
#: Five percent is the original's judgment and the author accepted its output.
NEUTRAL_BAND = 0.05

#: Rows whose reading is **inverted**: for a book, pricing above the reference
#: is an improvement, while for something bought, paying above the reference is
#: not. Both books, and nothing else.
INVERTED_TIERS = frozenset({'book'})

#: How a cell's companion number is formatted, by column. The gini columns are
#: distortion parameters on their own scales and take three places; the rest
#: carry units the reader knows.
_POINT_FORMATS = {'margin': '{:.1%}', 'MSD': '{:.2f}', 'Div CoC': '{:.1%}'}


def _format_actual(column, value):
    """The second text in a cell: the row's own number, in its own units.

    Parameters
    ----------
    column : str
        The column's name, which is what decides the units.
    value : float
        The actual, not the multiple.

    Returns
    -------
    str

    Notes
    -----
    Formatted here rather than by the renderer, which is the rule the IR states
    for every pre-formatted string it carries: whether a number reads as a
    percentage, a ratio to three places or a multiple is domain knowledge, and a
    renderer has none. A renderer given the raw number and asked to choose would
    be guessing.
    """
    if value is None:
        return ''
    return _POINT_FORMATS.get(column, '{:.3f}').format(value)


def relativity_chart_doc(pnl, base='gross'):
    """Build the relativity matrix as a chart document.

    Parameters
    ----------
    pnl : aggregate.PnL
        An extended P&L.
    base : {'gross', 'net'}, default 'gross'
        Which book anchors every ratio. Gross by default because it is the one
        book the reinsurance choices cannot move, so no cover's verdict leans on
        another cover's.

    Returns
    -------
    aggregate.charts.ChartDoc
        One 'matrix' panel: each position against each reading, as a multiple of
        the base, with the position's own number beneath.
    """
    actuals = derive.actuals_frame(pnl)
    matrix = derive.relativity_frame(actuals, base=base)
    columns = list(matrix.columns)
    tiers = {row.label: row.tier
             for row in derive.position_rows(derive.source_frames(pnl)[0])}

    values = tuple(
        tuple(None if _is_missing(v) else float(v) for v in matrix.loc[label])
        for label in matrix.index)
    annotations = tuple(
        tuple(_format_actual(column, actuals.loc[label, column])
              for column in columns)
        for label in matrix.index)
    polarity = tuple(-1 if tiers.get(label) in INVERTED_TIERS else 1
                     for label in matrix.index)
    data = MatrixData(
        rows=tuple(matrix.index),
        columns=tuple(columns),
        values=values,
        annotations=annotations,
        center=1.0,
        neutral=NEUTRAL_BAND,
        row_polarity=polarity,
        row_groups=tuple(tiers.get(label, 'book') for label in matrix.index),
        # The four distortion families are one band and the three point
        # estimates another: they are read against each other within a band and
        # not across the break.
        column_groups=tuple('family' if c.startswith('gini ') else 'point'
                            for c in columns),
    )
    base_label = 'gross book' if base == 'gross' else 'final net'
    return ChartDoc(
        name='relativity',
        title=f'Relativity: {getattr(pnl, "name", "")}, {base} base',
        axes=(
            ChartAxis(id='reading', label='reading', kind='category'),
            # No label: the row names are position names and saying so
            # above them is a caption on a caption.
            ChartAxis(id='position', label='', kind='category'),
            ChartAxis(id='multiple', label=f'multiple of the {base_label}'),
        ),
        panels=(Panel(id='relativity', kind='matrix', x_axis='reading',
                      y_axis='position', z_axis='multiple',
                      title='Each cover priced against the book'),),
        series=(ChartSeries(name='relativity', role='identity',
                            panel_id='relativity', matrix=data),),
        meta={'base': base, 'neutral': NEUTRAL_BAND},
    )


def _is_missing(value):
    """True for a value the matrix has no number for."""
    return value is None or value != value


#: How the two reference books are drawn, against the covers between them. The
#: roles are the library's own series vocabulary, so a renderer that knows
#: nothing about this plugin still knows which curve is the book and which is a
#: cession.
_TIER_ROLES = {
    'book': None,                       # resolved per label, below
    'occurrence': 'ceded',
    'occurrence_package': 'ceded',
    'aggregate': 'ceded',
    'aggregate_package': 'ceded',
}


#: Which **family** each tier belongs to, for the chart's grouping. The two
#: packages ride with the covers they summarize, since a reader comparing the
#: occurrence program wants its subtotal in the same family as its layers.
_TIER_FAMILIES = {
    'book': 'reference books',
    'occurrence': 'occurrence',
    'occurrence_package': 'occurrence',
    'aggregate': 'aggregate',
    'aggregate_package': 'aggregate',
}


def _series_role(label, tier):
    """The library series role for one position's curve."""
    if tier != 'book':
        return _TIER_ROLES[tier]
    return 'gross' if label == 'gross book' else 'net'


def spectrum_chart_doc(pnl, base='gross'):
    """The distortion spectrum: every position's relativity across the families.

    The companion to :func:`relativity_chart_doc`, and the right-hand panel of
    the original page. Where the matrix answers "what is this cover's verdict",
    this answers "does the verdict survive the choice of distortion family", by
    putting all four families on one axis and drawing each position's line
    across them. A line that stays on one side of the base is a verdict that
    does not depend on the family; one that crosses is a verdict that does.

    Parameters
    ----------
    pnl : aggregate.PnL
        An extended P&L.
    base : {'gross', 'net'}, default 'gross'
        Which book anchors the ratios, and therefore where the reference line
        at 1.0 sits.

    Returns
    -------
    aggregate.charts.ChartDoc
        One ``xy`` panel: the families on a category axis in the order the gross
        book ranks them, the multiple on a log axis, one curve per position, and
        a mark at 1.0.

    Notes
    -----
    Needs **no new panel kind**. The families are an ordered category axis and
    the multiples are a quantity on a log scale, both of which the chart IR has
    carried since 1.0. That is the whole reason this panel is cheap and the
    matrix was not.

    The y axis is read on **log** by default, because these are ratios: a cover
    at 2x and one at 0.5x are equally far from the base in opposite directions,
    and only a log scale draws them that way. The original page used
    ``arctan(log(y))``, which compresses the far tails further still; log is the
    honest part of that and the compression was a fitting device.

    The ordering of the families is the gross book's own, cheapest first, so the
    x axis is a genuine severity ordering rather than an alphabet. Nothing lives
    *between* two families, which is what ``support='atomic'`` says; the line a
    renderer draws across them is a trend, and the points are the readings.
    """
    gini, _ = derive.source_frames(pnl)
    order = derive.distortion_order(gini)
    actuals = derive.actuals_frame(pnl)
    matrix = derive.relativity_frame(actuals, base=base)
    families = [f'gini {d}' for d in order]
    tiers = {row.label: row.tier for row in derive.position_rows(gini)}
    x = tuple(float(i) for i in range(len(order)))

    series = tuple(
        ChartSeries(
            name=label,
            role=_series_role(label, tiers.get(label, 'book')),
            # The family a renderer gives one color ramp and one marker run to.
            # Semantic: that a cover is an occurrence cover is a fact about the
            # program, not a decision about color, and the renderer picks the
            # ramp without needing to know what 'occurrence' means.
            group=_TIER_FAMILIES[tiers.get(label, 'book')],
            panel_id='spectrum',
            x=x,
            y=tuple(float(matrix.loc[label, f]) for f in families),
        )
        for label in matrix.index)

    base_label = 'gross book' if base == 'gross' else 'final net'
    return ChartDoc(
        name='relativity_spectrum',
        title=f'Distortion spectrum: {getattr(pnl, "name", "")}, {base} base',
        axes=(
            # The families named on the axis, in the gross book's own order.
            # Without them the ticks read 0, 1, 2, 3.
            ChartAxis(id='family', label='distortion family', kind='category',
                      categories=tuple(order)),
            ChartAxis(id='multiple', label=f'multiple of the {base_label}',
                      scale='log', scales=('log', 'linear')),
        ),
        panels=(Panel(id='spectrum', kind='xy', x_axis='family',
                      y_axis='multiple', read_axis='x',
                      title='Does the verdict survive the family?'),),
        series=series,
        # ``role='base'`` is the declaration that this line divides the panel
        # into dearer above and cheaper below. A renderer that knows the role
        # washes the two halves; one that does not draws a plain rule and is
        # still correct. Deliberately a **price** statement and not a verdict:
        # above the base is dearer for everyone, where whether dearer is *good*
        # depends on which side of the trade the row sits, which is the same
        # trap ``MatrixData.row_polarity`` exists for on the grid.
        marks=(Mark(panel_id='spectrum', orient='h', at=1.0,
                    label=base_label, role='base', faint=True),),
        meta={'base': base},
    )
