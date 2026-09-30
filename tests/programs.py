"""The two synthetic DecL programs the golden data was produced from.

Copied from ``reference/gini_decl.py``, which is the porting spec. They are
transcribed here rather than imported from it, because ``reference/`` is a
frozen record of the approved original and is deliberately neither packaged nor
importable: a test that imported it would make the spec a dependency of the
thing it specifies.

Both are synthetic. Every number is invented for the example, so the golden CSVs
beside them in ``reference/data/`` are fixtures rather than data, and the data
firewall is satisfied.

``CAPSTONE`` peels **bottom-up** and ``PNL_LOSS_RATIO`` peels **top-down**, which
is why their position rows come out in opposite orders. That is the pair worth
keeping: it is what proves :func:`aggregate_relativity.derive.classify_positions`
reads the panel's own step order rather than imposing one.
"""

CAPSTONE = """xpnl Capstone.PnL
  derive premium
  less
    agg Capstone.FullProgram
      [2000 5000 10000 3000 1000] premium as GWP at [0.95 0.95 0.9 0.85 0.75] lr
      [500 1000 5000 10000 5000] xs [0 0 0 0 1000]
      sev 151.63266492815836 * lognorm 1
        picks [500 1000 2000 5000 10000] [14900 2250 1250 500 50]
      occurrence net of
        50% po 500 xs 500 deposit 3000 as "500x500" and
        90% po 1000 xs 1000 deposit 1750 as "1x1" and
        95% po 3000 xs 2000 rol 0.25 as "3x2" and
        5000 xs 5000 rol 0.03 as "5x5"
      mixed gamma 0.125
      aggregate net of
        75% po inf xs 0 rate 1 cede 0.325 as QS
  less
    0.25 premium expenses as "G&A"
  peel bottom-up
"""

PNL_LOSS_RATIO = """xpnl PnLLossRatio
  1000 premium
  less
    agg PnL.D
      1000 premium at 0.5 lr
      2000 xs 0
      sev 90 *  lognorm 2
      occurrence net of 75% po 500 xs 500 rol 35% as "Occ 1" and
      95% po 500 xs 1000 rol 17.5% as "Occ 2" and
      100% po 500 xs 1500 rol 15% as "Occ 3"
      mixed gamma 0.25
    aggregate net of
      75% po 500 xs 0 rate .85 cede 42.5% as "Ltd QS" and
      100% po 1400 xs 600 rol 0.07 as "Agg Stop"
  less
    25% premium expense as "G&A"
  peel top-down
"""

#: A P&L with no peel clause: one margin row, an empty walk, no positions. The
#: plugin's exhibit must report itself unavailable for it.
PLAIN = """pnl PlainBook
  1000 premium
  less
    agg PlainBook.Loss
      1000 premium at 0.7 lr
      1000 xs 0
      sev 100 * lognorm 1.5
      poisson
"""


def capstone(cede):
    """``CAPSTONE`` with the quota share's cede commission moved.

    Parameters
    ----------
    cede : float
        The ``cede`` fraction, as the DecL spells it. The reference run swept
        0.325, 0.31, 0.30 and 0.29, and captured one golden file per value.

    Returns
    -------
    str
    """
    return CAPSTONE.replace('cede 0.325', f'cede {cede}')


#: ``(golden file suffix, DecL program)`` for every approved reference output.
GOLDEN_CASES = [
    ('', CAPSTONE),
    ('_qs31', capstone(0.31)),
    ('_qs30', capstone(0.30)),
    ('_qs29', capstone(0.29)),
    ('_PnLLossRatio', PNL_LOSS_RATIO),
]
