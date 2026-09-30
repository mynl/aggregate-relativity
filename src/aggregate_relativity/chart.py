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

from aggregate.charts import ChartAxis, ChartDoc, ChartSeries, MatrixData, Panel

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
            ChartAxis(id='position', label='position', kind='category'),
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
