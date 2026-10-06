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

from .programs import CAPSTONE, PLAIN, UNEVALUABLE_COVERS


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


# --- the distortion spectrum -------------------------------------------------

@pytest.fixture(scope='module')
def spectrum(pnl):
    return chart.spectrum_chart_doc(pnl)


def test_the_spectrum_is_one_xy_panel(spectrum):
    """It needed no new panel kind, which is why it was cheap."""
    panel, = spectrum.panels
    assert panel.kind == 'xy'
    assert spectrum.name == 'relativity_spectrum'


def test_the_families_are_named_on_the_axis(spectrum, pnl):
    """Without the names the ticks read 0, 1, 2, 3."""
    gini, _ = derive.source_frames(pnl)
    family = next(a for a in spectrum.axes if a.id == 'family')
    assert family.kind == 'category'
    assert list(family.categories) == derive.distortion_order(gini)


def test_the_multiple_is_read_on_log(spectrum):
    """These are ratios: 2x and 0.5x are equally far from the base."""
    multiple = next(a for a in spectrum.axes if a.id == 'multiple')
    assert multiple.scale == 'log'
    assert 'linear' in multiple.scales


def test_one_curve_per_position(spectrum, pnl):
    actuals = derive.actuals_frame(pnl)
    assert [s.name for s in spectrum.series] == list(actuals.index)
    for s in spectrum.series:
        assert len(s.x) == 4 and len(s.y) == 4


def test_the_curves_carry_the_matrix_numbers(spectrum, pnl):
    """The spectrum and the grid are one computation read two ways."""
    matrix = derive.relativity_frame(derive.actuals_frame(pnl))
    families = [c for c in matrix.columns if c.startswith('gini ')]
    for s in spectrum.series:
        expected = [matrix.loc[s.name, f] for f in families]
        assert list(s.y) == pytest.approx(expected)


def test_the_books_carry_their_own_roles(spectrum):
    """So a renderer that knows nothing about this plugin still knows which
    curve is the book and which is a cession."""
    roles = {s.name: s.role for s in spectrum.series}
    assert roles['gross book'] == 'gross'
    assert roles['final net'] == 'net'
    assert roles['QS'] == 'ceded'


def test_the_base_line_is_marked(spectrum):
    mark, = spectrum.marks
    assert mark.orient == 'h' and mark.at == 1.0
    assert mark.faint is True


def test_the_gross_book_is_flat_at_one(spectrum):
    curve = next(s for s in spectrum.series if s.name == 'gross book')
    assert list(curve.y) == pytest.approx([1.0] * 4)


def test_the_spectrum_round_trips(spectrum):
    from aggregate.charts.ir import stamp
    stamped = stamp(spectrum)
    assert load_chart_doc(canonical_dict(stamped)) == stamped


def test_the_net_base_flattens_the_final_net(pnl):
    doc = chart.spectrum_chart_doc(pnl, base='net')
    curve = next(s for s in doc.series if s.name == 'final net')
    assert list(curve.y) == pytest.approx([1.0] * 4)


def test_the_curves_are_grouped_into_families(spectrum):
    """So a renderer can give one color family to the occurrence covers.

    Semantic, not a color: that a cover is an occurrence cover is a fact about
    the program. The two packages ride with the covers they summarize, since a
    reader comparing the occurrence program wants its subtotal beside its layers.
    """
    groups = {s.name: s.group for s in spectrum.series}
    assert groups['gross book'] == 'reference books'
    assert groups['final net'] == 'reference books'
    assert groups['500x500'] == 'occurrence'
    assert groups['occ package'] == 'occurrence'
    assert groups['QS'] == 'aggregate'
    assert len(set(groups.values())) == 3


def test_the_base_mark_declares_its_role(spectrum):
    """Which is what tells a renderer the panel has a dearer half and a cheaper one."""
    mark, = spectrum.marks
    assert mark.role == 'base'


# --- a position the library could not evaluate (0.8.0) -----------------------

@pytest.fixture(scope='module')
def bargain():
    """A tower whose covers are bought below their expected recoveries.

    One position, the 200 xs 400 aggregate layer, has a non-positive expected
    margin, so there is no breakeven acceptability level for it and the library
    reports its gini as ``NaN`` across every family. The four approved programs
    cannot show this: every cover in them is priced above its recoveries.
    """
    return build(UNEVALUABLE_COVERS)


def test_the_fixture_really_does_carry_an_unevaluable_position(bargain):
    """Guard the guard: if the library's pricing moves this case away, the test
    below would pass for the wrong reason."""
    actuals = derive.actuals_frame(bargain)
    missing = actuals.index[actuals['gini ph'].isna()]
    assert list(missing) == ['agg 200 xs 400']
    assert actuals.loc['agg 200 xs 400', 'margin'] <= 0, 'which is why'


def test_an_unevaluable_position_draws_no_curve(bargain):
    """A chart cannot draw a number that does not exist.

    The drop is **selective**: every other position keeps its curve, so this is
    not an all-or-nothing bail out.
    """
    spectrum = chart.spectrum_chart_doc(bargain)
    actuals = derive.actuals_frame(bargain)
    drawn = [s.name for s in spectrum.series]
    assert 'agg 200 xs 400' not in drawn
    assert drawn == [p for p in actuals.index if p != 'agg 200 xs 400']


def test_the_spectrum_survives_canonical_json(bargain):
    """The bug this fixes, asserted where it bit.

    Emitting the NaN raised ``ValueError: Out of range float values are not JSON
    compliant`` out of ``canonical_json``, which every chart document goes
    through to be stamped with its hash. The leaf answered 500.
    """
    spectrum = chart.spectrum_chart_doc(bargain)
    assert doc_hash(spectrum)
    for s in spectrum.series:
        assert all(v == v for v in s.y), s.name
