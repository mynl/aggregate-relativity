"""``aggregate_relativity.derive``: the arithmetic, against the approved output.

The golden test is the point of this file. The page it ports was already correct
and its answers were accepted, so the rewrite off the original's HTTP-and-parse
route onto the library's public frames must move **no number**. Any drift here is
a porting bug, never a design choice.

``reference/data/gini_view45_actuals*.csv`` are the approved outputs of the two
synthetic programs in ``tests/programs.py``. They are fixtures, not data.
"""

from pathlib import Path

import pandas as pd
import pytest
from aggregate import build

from aggregate_relativity import derive

from .programs import CAPSTONE, GOLDEN_CASES, PNL_LOSS_RATIO

GOLDEN_DIR = Path(__file__).resolve().parents[1] / 'reference' / 'data'


@pytest.fixture(scope='module')
def capstone_pnl():
    """The bottom-up program, built once for the whole module."""
    return build(CAPSTONE)


@pytest.fixture(scope='module')
def loss_ratio_pnl():
    """The top-down program, whose positions come out in the other order."""
    return build(PNL_LOSS_RATIO)


# --- the golden regression ---------------------------------------------------

@pytest.mark.golden
@pytest.mark.parametrize('suffix,program', GOLDEN_CASES,
                         ids=[s or 'capstone' for s, _ in GOLDEN_CASES])
def test_actuals_match_the_approved_output(suffix, program):
    """Every number in the exhibit's frame matches the accepted reference run.

    Read with the label column as the index, which is how ``to_csv`` wrote it.
    Compared on values with a float tolerance rather than on repr, since the
    reference captured full precision and the two routes reach the same numbers
    by different orders of operation.
    """
    golden = pd.read_csv(GOLDEN_DIR / f'gini_view45_actuals{suffix}.csv',
                         index_col=0)
    got = derive.actuals_frame(build(program))
    assert list(got.index) == list(golden.index)
    assert list(got.columns) == list(golden.columns)
    pd.testing.assert_frame_equal(got, golden, check_exact=False,
                                  rtol=1e-9, atol=1e-12)


# --- structure ---------------------------------------------------------------

def test_capstone_positions_follow_the_bottom_up_peel(capstone_pnl):
    """Four occurrence layers, their package and net, then the one quota share.

    No aggregate package row: the tier has a single cover, so a subtotal of it
    would repeat the cover. The net-of-occ book rides after the occurrence
    package (a third reference book, tier ``'book'``), since aggregate cover
    follows; its panel step is the running net before the package.
    """
    gini, walk = derive.source_frames(capstone_pnl)
    positions = derive.classify_positions(gini, walk)
    assert [p.label for p in positions] == [
        '500x500', '1x1', '3x2', '5x5', 'occ package', 'net of occ', 'QS']
    assert [p.tier for p in positions] == [
        'occurrence', 'occurrence', 'occurrence', 'occurrence',
        'occurrence_package', 'book', 'aggregate']
    net = positions[5]
    assert net.walk_step == derive.NET_OF_OCC_WALK_STEP
    assert net.grid_step.startswith('net through ')


def test_loss_ratio_positions_follow_the_top_down_peel(loss_ratio_pnl):
    """The same reader, the opposite order, and both packages present."""
    gini, walk = derive.source_frames(loss_ratio_pnl)
    positions = derive.classify_positions(gini, walk)
    assert [p.label for p in positions] == [
        'Occ 3', 'Occ 2', 'Occ 1', 'occ package', 'net of occ',
        'Agg Stop', 'Ltd QS', 'agg package']
    assert [p.tier for p in positions][-1] == 'aggregate_package'


def test_position_rows_bracket_the_positions_with_the_books(capstone_pnl):
    gini, walk = derive.source_frames(capstone_pnl)
    rows = derive.position_rows(gini, walk)
    assert rows[0].label == 'gross book' and rows[0].tier == 'book'
    assert rows[-1].label == 'final net' and rows[-1].tier == 'book'
    assert rows[-1].grid_step == derive.FINAL_GRID_STEP
    assert [p.label for p in rows[1:-1]] == [
        p.label for p in derive.classify_positions(gini, walk)]


def test_families_are_ordered_by_the_gross_books_own_gini(capstone_pnl):
    gini, _ = derive.source_frames(capstone_pnl)
    order = derive.distortion_order(gini)
    values = [gini[(derive.GROSS_GRID_STEP, d)] for d in order]
    assert values == sorted(values)
    assert set(order) == set(derive.DISTORTION_NAMES)


# --- the MSD sign ------------------------------------------------------------

def test_margin_sigma_flips_a_spender_and_leaves_an_earner(capstone_pnl):
    """A purchase's MSD arrives negative; the page wants its magnitude."""
    _, walk = derive.source_frames(capstone_pnl)
    assert float(walk.loc['500x500', 'Margin spent']) < 0
    assert float(walk.loc['500x500', 'MSD']) < 0
    assert derive.margin_sigma(walk, '500x500') > 0

    assert float(walk.loc['Gross', 'Margin spent']) > 0
    assert derive.margin_sigma(walk, 'Gross') == float(walk.loc['Gross', 'MSD'])


# --- the relativity matrix ---------------------------------------------------

def test_relativity_base_row_is_all_ones(capstone_pnl):
    """Dividing the frame by one of its own rows: that row is ones by identity."""
    matrix = derive.relativity_frame(capstone_pnl)
    ones = [1.0] * matrix.shape[1]
    assert list(matrix.loc['gross book']) == pytest.approx(ones)
    net = derive.relativity_frame(capstone_pnl, base='net')
    assert list(net.loc['final net']) == pytest.approx(ones)


def test_relativity_reproduces_the_hand_computed_ratio(capstone_pnl):
    """The matrix is the actuals over the base row, column by column."""
    actuals = derive.actuals_frame(capstone_pnl)
    matrix = derive.relativity_frame(actuals)
    for column in derive.matrix_columns(actuals):
        expected = actuals.loc['QS', column] / actuals.loc['gross book', column]
        assert matrix.loc['QS', column] == pytest.approx(expected)


def test_relativity_drops_cr_and_sa_coc(capstone_pnl):
    """margin is 1 - CR, so scoring both says one thing twice."""
    matrix = derive.relativity_frame(capstone_pnl)
    assert 'CR' not in matrix.columns and 'SA CoC' not in matrix.columns
    assert list(matrix.columns)[-3:] == list(derive.MATRIX_POINT_COLUMNS)


def test_relativity_accepts_a_prepared_actuals_frame(capstone_pnl):
    """A caller needing both frames pays for the derivation once."""
    actuals = derive.actuals_frame(capstone_pnl)
    pd.testing.assert_frame_equal(derive.relativity_frame(actuals),
                                  derive.relativity_frame(capstone_pnl))


def test_relativity_rejects_an_unknown_base(capstone_pnl):
    with pytest.raises(ValueError, match="'gross' or 'net'"):
        derive.relativity_frame(capstone_pnl, base='sideways')


def test_a_negative_div_coc_is_left_as_computed(capstone_pnl):
    """5x5's diversified cost of capital is negative, and stays negative.

    Masking it here would hide a real number. Declining to color the cell is the
    renderer's job, since it is the diverging scale that cannot read a sign flip,
    not the arithmetic.
    """
    actuals = derive.actuals_frame(capstone_pnl)
    assert actuals.loc['5x5', 'Div CoC'] < 0
    assert derive.relativity_frame(actuals).loc['5x5', 'Div CoC'] < 0


def test_net_of_occ_appears_without_an_occurrence_package():
    """One occurrence cover means no package step, and the row still lands.

    The gate is the walk's own ``Net of occurrence`` row, not the package: a
    single-cover tier earns no subtotal, yet the book still nets before the
    aggregate tier buys behind it, and the panel step is the running net
    named by the walk's own order.
    """
    pnl = build(
        'xpnl RelNoPkg 1000 premium less agg RelNoPkg_e 1000 premium at '
        '70% lr sev lognorm 100 cv 1.5 occurrence net of 250 xs 250 '
        'deposit 40 poisson aggregate net of 1000 xs 1500 deposit 30 '
        'peel bottom-up')
    gini, walk = derive.source_frames(pnl)
    positions = derive.classify_positions(gini, walk)
    labels = [p.label for p in positions]
    assert 'net of occ' in labels
    net = positions[labels.index('net of occ')]
    assert net.grid_step == 'net through occ 250 xs 250'
    assert labels.index('net of occ') == labels.index('occ 250 xs 250') + 1
    # and the row reaches the page with its own numbers
    actuals = derive.actuals_frame(pnl)
    assert 'net of occ' in actuals.index
    assert actuals.loc['net of occ'].notna().all()
