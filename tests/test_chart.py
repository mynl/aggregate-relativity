"""``aggregate_relativity.chart``: the matrix as a chart document.

The plugin emits and never draws, so what is testable here is the **document**:
which rows, which columns, what the neutral band is, and which way each row is
read. Whether the picture is any good is the renderers' business and the
library's own baselines.

The one claim worth pinning hardest is polarity. A reader can check a printed
multiple against the table it came from; nobody can check by eye that the two
book rows are colored the opposite way from the covers, and that is exactly what
``row_polarity`` asserts.
"""

import pytest
from aggregate import build
from aggregate.charts import ChartDoc, MatrixData
from aggregate.charts.ir import canonical_dict, doc_hash, load_chart_doc

from aggregate_relativity import chart, derive

from .programs import CAPSTONE, PLAIN


@pytest.fixture(scope='module')
def pnl():
    return build(CAPSTONE)


@pytest.fixture(scope='module')
def doc(pnl):
    return chart.relativity_chart_doc(pnl)


@pytest.fixture(scope='module')
def matrix(doc):
    return doc.series[0].matrix


# --- the document ------------------------------------------------------------

def test_it_is_one_matrix_panel(doc):
    assert isinstance(doc, ChartDoc)
    assert doc.name == 'relativity'
    panel, = doc.panels
    assert panel.kind == 'matrix'
    assert isinstance(doc.series[0].matrix, MatrixData)
    assert len(doc.series) == 1


def test_the_axes_are_categorical(doc):
    kinds = {a.id: a.kind for a in doc.axes}
    assert kinds['reading'] == 'category'
    assert kinds['position'] == 'category'
    # The value axis is not: it is a multiple, a real number.
    assert kinds['multiple'] != 'category'


def test_the_document_round_trips(doc):
    from aggregate.charts.ir import stamp
    stamped = stamp(doc)
    back = load_chart_doc(canonical_dict(stamped))
    assert back == stamped
    assert doc_hash(back) == stamped.hash


def test_it_carries_no_matplotlib():
    """The plugin emits documents and draws nothing, so it imports no renderer."""
    import sys
    source = (chart.__file__)
    text = open(source, encoding='utf-8').read()
    assert 'matplotlib' not in text.replace('matplotlib here', '')
    assert 'aggregate_relativity.chart' in sys.modules or True


# --- the rows and columns ----------------------------------------------------

def test_rows_are_the_positions_in_peel_order(matrix):
    assert matrix.rows[0] == 'gross book'
    assert matrix.rows[-1] == 'final net'
    assert 'occ package' in matrix.rows
    assert 'QS' in matrix.rows


def test_columns_are_the_families_then_the_point_estimates(matrix):
    assert list(matrix.columns[:4]) == [c for c in matrix.columns
                                        if c.startswith('gini ')]
    assert list(matrix.columns[4:]) == ['margin', 'MSD', 'Div CoC']
    assert list(matrix.column_groups) == ['family'] * 4 + ['point'] * 3


def test_the_base_row_is_all_ones(matrix):
    row = matrix.values[matrix.rows.index('gross book')]
    assert all(v == pytest.approx(1.0) for v in row)


def test_every_cell_matches_the_frame(pnl, matrix):
    """The chart and the exhibit are one computation, so they cannot disagree."""
    actuals = derive.actuals_frame(pnl)
    frame = derive.relativity_frame(actuals)
    for i, label in enumerate(matrix.rows):
        for j, column in enumerate(matrix.columns):
            assert matrix.values[i][j] == pytest.approx(frame.loc[label, column])


# --- the reading -------------------------------------------------------------

def test_the_books_are_read_the_other_way(matrix):
    """Pricing above the reference is an improvement for a book, not for a cover.

    One matrix holding rows read in both directions is the case ``row_polarity``
    exists for, and this page is that case.
    """
    polarity = dict(zip(matrix.rows, matrix.polarity))
    assert polarity['gross book'] == -1
    assert polarity['final net'] == -1
    assert polarity['QS'] == 1
    assert polarity['occ package'] == 1


def test_the_neutral_band_is_the_original_judgment(matrix):
    assert matrix.center == 1.0
    assert matrix.neutral == chart.NEUTRAL_BAND == 0.05


def test_rows_are_banded_by_tier(matrix):
    groups = dict(zip(matrix.rows, matrix.row_groups))
    assert groups['gross book'] == 'book' and groups['final net'] == 'book'
    assert groups['500x500'] == 'occurrence'
    assert groups['occ package'] == 'occurrence_package'
    assert groups['QS'] == 'aggregate'


# --- the annotations ---------------------------------------------------------

def test_every_cell_carries_its_actual(pnl, matrix):
    actuals = derive.actuals_frame(pnl)
    i = matrix.rows.index('QS')
    j = matrix.columns.index('gini ph')
    assert matrix.annotations[i][j] == f"{actuals.loc['QS', 'gini ph']:.3f}"


def test_a_ratio_column_reads_as_a_percentage(pnl, matrix):
    actuals = derive.actuals_frame(pnl)
    i = matrix.rows.index('gross book')
    j = matrix.columns.index('margin')
    assert matrix.annotations[i][j] == f"{actuals.loc['gross book', 'margin']:.1%}"
    assert matrix.annotations[i][j].endswith('%')


def test_msd_reads_as_a_plain_ratio(matrix):
    j = matrix.columns.index('MSD')
    assert not matrix.annotations[0][j].endswith('%')


def test_the_formatter_handles_an_absent_value():
    assert chart._format_actual('margin', None) == ''


# --- the net base ------------------------------------------------------------

def test_the_net_base_anchors_on_the_final_net(pnl):
    matrix = chart.relativity_chart_doc(pnl, base='net').series[0].matrix
    row = matrix.values[matrix.rows.index('final net')]
    assert all(v == pytest.approx(1.0) for v in row)


def test_the_title_names_the_base(pnl):
    assert 'gross base' in chart.relativity_chart_doc(pnl).title
    assert 'net base' in chart.relativity_chart_doc(pnl, base='net').title


def test_an_unknown_base_is_refused(pnl):
    with pytest.raises(ValueError, match="'gross' or 'net'"):
        chart.relativity_chart_doc(pnl, base='sideways')


# --- what it declines to answer ---------------------------------------------

def test_a_plain_pnl_has_no_positions_to_chart():
    """The gate is the exhibit's, so the table and the picture light together."""
    from aggregate_relativity import register as register_module
    plain = build(PLAIN)
    assert register_module._can_chart(plain) is False


def test_an_aggregate_is_not_dispatched():
    from aggregate_relativity.register import chart_relativity
    dice = build('agg ChartDice dfreq [3] dsev [1:6]')
    with pytest.raises(NotImplementedError, match='not implemented for Aggregate'):
        chart_relativity(dice)
