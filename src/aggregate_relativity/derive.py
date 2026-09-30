"""The relativity arithmetic, over public ``aggregate`` frames.

Pure pandas. No HTTP, no matplotlib, no reach into an underscore-prefixed name,
and nothing here knows it is being served by an exhibit or drawn as a chart, so
it is testable on its own and is what the golden regression in
``tests/test_derive.py`` checks.

The question the page answers: **for each cover the program buys, is it priced
above or below the book's own acceptability?** A position's ``gini_p`` is the
distortion parameter at which the position breaks even, so a layer whose
``gini_p`` sits above the gross book's is priced above what the holder would
itself charge, and buying it therefore lowers the net. Reading the same row under
four distortion families, beside three point estimates, is how a verdict that
survives the choice of family is told from one that depends on it.

Notes
-----
Two frames feed it, both public, and the distinction matters because the P&L
surface spells them almost identically:

* :attr:`aggregate.PnL.evaluation_df`, a **property**, is the ratio walk. One
  row per step, carrying ``Premium spent``, ``Margin spent``, ``CR``, ``MSD``,
  ``SA CoC`` and ``Div CoC``.
* ``PnL.evaluate().evaluation_df``, the frame on the **result** of the method, is
  the gini panel, indexed ``(Step, distortion)`` and carrying ``gini_p``.

The two index vocabularies differ, which is why a position carries both of its
step names: the walk says ``500x500`` where the panel says ``500x500 result``.

The relativity matrix is computed as a **division of the actuals frame** rather
than by a second pass over the source frames. In the script this was ported from
the arithmetic existed twice, once inside the renderer and once in the frame
builder. That is harmless in a script that runs both in one pass and unacceptable
here, where the exhibit and the chart are served by separate requests and must
not be able to disagree. Dividing one frame by one of its own rows makes a
disagreement structurally impossible rather than merely unlikely.
"""

from collections import namedtuple

import pandas as pd

#: The distortion families the gini panel carries, with their display names.
#: Order here is irrelevant: the page orders them by the gross book's own gini,
#: cheapest first, so the reader meets the families in severity order.
DISTORTION_NAMES = {
    'ph': 'Proportional hazard',
    'wang': 'Wang',
    'dual': 'Dual moment',
    'tvar': 'TVaR',
}

#: The gini panel's step for the gross book, and the walk's name for it.
GROSS_GRID_STEP, GROSS_WALK_STEP = 'Gross result', 'Gross'

#: The final net. The panel's ``margin`` rows *are* the final net, which is why
#: this one is not spelled ``... result`` like every other step.
FINAL_GRID_STEP, FINAL_WALK_STEP = 'margin', 'All'

#: The two tier subtotals, present only where their tier has more than one cover.
OCCURRENCE_PACKAGE = 'All occurrence result'
AGGREGATE_PACKAGE = 'All aggregate result'

_RESULT_SUFFIX = ' result'

#: The exhibit's columns after the four gini columns.
POINT_COLUMNS = ('CR', 'margin', 'MSD', 'SA CoC', 'Div CoC')

#: The subset the relativity matrix scores. ``CR`` drops out because ``margin``
#: is ``1 - CR`` and scoring both carries one fact twice; ``SA CoC`` drops
#: because a stand-alone cost of capital is not a quantity one purchase moves
#: relative to the book.
MATRIX_POINT_COLUMNS = ('margin', 'MSD', 'Div CoC')

#: One row of the page. ``tier`` is ``'book'`` for the two reference rows,
#: ``'occurrence'`` or ``'aggregate'`` for a cover, and ``'occurrence_package'``
#: or ``'aggregate_package'`` for a tier subtotal. It is structure, not
#: presentation: a renderer maps it to a color and a marker, and this module
#: holds no colors at all.
Position = namedtuple('Position', 'label grid_step walk_step tier')


def source_frames(pnl):
    """Return ``(gini, walk)``, the two public frames the page reads.

    Parameters
    ----------
    pnl : aggregate.PnL
        An extended P&L, meaning one built with a ``peel`` clause. A plain P&L
        has an empty walk and no positions to score.

    Returns
    -------
    (pandas.Series, pandas.DataFrame)
        ``gini`` indexed ``(Step, distortion)``, and the ratio walk indexed by
        ``Step``.
    """
    return (pnl.evaluate().evaluation_df['gini_p'].astype(float),
            pnl.evaluation_df)


def distortion_order(gini):
    """The families ordered by the gross book's own gini, cheapest first.

    Parameters
    ----------
    gini : pandas.Series
        Indexed ``(Step, distortion)``.

    Returns
    -------
    list of str
    """
    return sorted(DISTORTION_NAMES, key=lambda d: gini[(GROSS_GRID_STEP, d)])


def classify_positions(gini):
    """One :class:`Position` per cover the program buys, in peel order.

    Parameters
    ----------
    gini : pandas.Series
        Indexed ``(Step, distortion)``; only its step sequence is read.

    Returns
    -------
    list of Position

    Notes
    -----
    The tier a cover belongs to is read off the panel's own step order, which
    follows the peel: buy steps before ``All occurrence result`` are occurrence
    covers, and those after it are aggregate-tier covers. A program with only an
    aggregate tier carries no occurrence package step at all, and then every
    cover is an aggregate one, which is why the tier starts as ``'aggregate'`` in
    that case rather than being corrected afterwards.

    ``net through <cover>`` steps are skipped. They are the running net after a
    purchase, not a position anybody holds, so there is no price to judge.
    """
    steps = list(dict.fromkeys(gini.index.get_level_values('Step')))
    occurrence, aggregate = [], []
    current = occurrence if OCCURRENCE_PACKAGE in steps else aggregate
    for step in steps:
        if step == OCCURRENCE_PACKAGE:
            current = aggregate
        elif (step.endswith(_RESULT_SUFFIX)
                and step not in (GROSS_GRID_STEP, AGGREGATE_PACKAGE)):
            current.append(step[:-len(_RESULT_SUFFIX)])
    out = [Position(nm, f'{nm}{_RESULT_SUFFIX}', nm, 'occurrence')
           for nm in occurrence]
    if OCCURRENCE_PACKAGE in steps:
        out.append(Position('occ package', OCCURRENCE_PACKAGE,
                            'All occurrence', 'occurrence_package'))
    out += [Position(nm, f'{nm}{_RESULT_SUFFIX}', nm, 'aggregate')
            for nm in aggregate]
    if AGGREGATE_PACKAGE in steps:
        out.append(Position('agg package', AGGREGATE_PACKAGE,
                            'All aggregate', 'aggregate_package'))
    return out


def position_rows(gini):
    """Every row of the page: the gross book, each position, the final net.

    Parameters
    ----------
    gini : pandas.Series
        Indexed ``(Step, distortion)``.

    Returns
    -------
    list of Position
        The two book rows bracket the positions, since they are what the
        purchases move between.
    """
    return ([Position('gross book', GROSS_GRID_STEP, GROSS_WALK_STEP, 'book')]
            + classify_positions(gini)
            + [Position('final net', FINAL_GRID_STEP, FINAL_WALK_STEP, 'book')])


def margin_sigma(walk, step):
    """``MSD`` for one step, signed by whether that step spends or earns margin.

    Parameters
    ----------
    walk : pandas.DataFrame
        The ratio walk, indexed by ``Step``.
    step : str
        A walk step name.

    Returns
    -------
    float

    Notes
    -----
    The walk reports a purchase's ``MSD`` negatively, because a purchase spends
    margin, and its ``Margin spent`` is negative for the same reason. What the
    page wants is the **magnitude** of the position's own margin per unit of
    standard deviation, so that a layer's ratio against the book reads as "this
    cover costs 1.6 times what the book charges itself" rather than carrying a
    sign that says only which side of the trade it sits on. Flipping on the sign
    of ``Margin spent`` recovers that magnitude, and leaves the two book rows,
    which earn margin rather than spend it, untouched.
    """
    value = float(walk.loc[step, 'MSD'])
    return -value if float(walk.loc[step, 'Margin spent']) < 0 else value


def actuals_frame(pnl):
    """The page's rows with their own numbers, one row per position.

    This is what the ``relativity`` exhibit serves, and what
    :func:`relativity_frame` divides.

    Parameters
    ----------
    pnl : aggregate.PnL
        An extended P&L.

    Returns
    -------
    pandas.DataFrame
        Indexed by position label in peel order, gross book first and final net
        last. Columns are ``gini <family>`` for each family in
        :func:`distortion_order` order, then ``CR``, ``margin`` (which is
        ``1 - CR``), ``MSD`` signed per :func:`margin_sigma`, ``SA CoC`` and
        ``Div CoC``.
    """
    gini, walk = source_frames(pnl)
    order = distortion_order(gini)
    records = {}
    for row in position_rows(gini):
        cr = float(walk.loc[row.walk_step, 'CR'])
        records[row.label] = (
            [float(gini[(row.grid_step, d)]) for d in order]
            + [cr, 1 - cr, margin_sigma(walk, row.walk_step),
               float(walk.loc[row.walk_step, 'SA CoC']),
               float(walk.loc[row.walk_step, 'Div CoC'])])
    columns = [f'gini {d}' for d in order] + list(POINT_COLUMNS)
    return pd.DataFrame.from_dict(records, orient='index', columns=columns)


def matrix_columns(actuals):
    """The columns :func:`relativity_frame` scores, in page order.

    Parameters
    ----------
    actuals : pandas.DataFrame
        The frame :func:`actuals_frame` returned.

    Returns
    -------
    list of str
    """
    return ([c for c in actuals.columns if c.startswith('gini ')]
            + list(MATRIX_POINT_COLUMNS))


def relativity_frame(source, base='gross'):
    """Each cell as a multiple of the base row's value.

    Parameters
    ----------
    source : aggregate.PnL or pandas.DataFrame
        An extended P&L, or the frame :func:`actuals_frame` already returned, so
        a caller needing both pays for the derivation once.
    base : {'gross', 'net'}, default 'gross'
        Which book anchors every ratio. ``'gross'`` is the default because the
        gross book is the one thing the reinsurance choices cannot move, so no
        cover's verdict leans on another cover's.

    Returns
    -------
    pandas.DataFrame
        The same index as :func:`actuals_frame`, columns from
        :func:`matrix_columns`. The base row is all ones by construction.

    Notes
    -----
    A ratio rather than a difference, because the four families sit on four
    different parameter scales and only a ratio is comparable across them.

    A negative ``Div CoC``, which a high thin layer can have, yields a negative
    ratio. It is left in the frame as computed rather than masked: the number is
    real, and it is the renderer that declines to color a cell whose sign makes
    the diverging scale meaningless.
    """
    if base not in ('gross', 'net'):
        raise ValueError(f"base is 'gross' or 'net', not {base!r}")
    actuals = (source if isinstance(source, pd.DataFrame)
               else actuals_frame(source))
    columns = matrix_columns(actuals)
    base_label = 'gross book' if base == 'gross' else 'final net'
    return actuals[columns].div(actuals.loc[base_label, columns],
                                axis='columns')
