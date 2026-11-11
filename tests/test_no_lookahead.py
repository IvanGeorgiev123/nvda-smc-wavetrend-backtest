"""Look-ahead and engine checks.

1. Truncation test: every indicator/signal value at bar i must be identical whether the data ends at bar i
   or continues for years. If any value changed, the code would be using future bars.
2. Engine test: orders are filled at the NEXT bar's open, and costs are applied on both fills.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backtester.engine import run_backtest
from backtester.strategy import Params, compute_indicators, build_variants

DATA = Path(__file__).resolve().parent.parent / "data" / "NVDA.csv"


@pytest.fixture(scope="module")
def prices():
    if not DATA.exists():
        pytest.skip("run `python run.py` once to download data/NVDA.csv")
    return pd.read_csv(DATA, index_col=0, parse_dates=True)


def _same(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return np.allclose(a, b, equal_nan=True, rtol=1e-9, atol=1e-9)


@pytest.mark.parametrize("cut", [400, 900, 1700, 2600, 3300])
def test_signals_do_not_change_when_future_is_removed(prices, cut):
    p = Params()
    full = compute_indicators(prices, p)
    part = compute_indicators(prices.iloc[:cut], p)
    for col in part.columns:
        assert _same(full[col].iloc[:cut], part[col]), f"column {col} uses future data"
    vf, vp = build_variants(full, p), build_variants(part, p)
    for name in vp:
        for key in ("entry", "exit"):
            assert (vf[name][key][:cut] == vp[name][key]).all(), f"{name} {key} uses future data"


def test_orders_fill_at_next_open_with_costs():
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame({"open": [10, 11, 12, 13, 14], "high": [11, 12, 13, 14, 15],
                       "low": [9, 10, 11, 12, 13], "close": [10.5, 11.5, 12.5, 13.5, 14.5]}, index=idx)
    entry = np.array([True, False, False, False, False])
    exit_ = np.array([False, False, True, False, False])
    res = run_backtest(df, entry, exit_, cost=0.01)
    t = res.trades[0]
    assert t.entry_date == idx[1] and t.entry_price == 11          # signal on day 0 -> buy day 1 open
    assert t.exit_date == idx[3] and t.exit_price == 13            # signal on day 2 -> sell day 3 open
    assert t.return_pct == pytest.approx(13 / 11 * 0.99 * 0.99 - 1)
    assert res.equity.iloc[0] == 1.0


def test_stop_exit():
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame({"open": [10, 10, 10, 8, 8], "high": [11] * 5, "low": [9, 9, 7, 7, 7],
                       "close": [10, 10, 8, 8, 8]}, index=idx)
    entry = np.array([True, False, False, False, False])
    stop = np.full(5, 9.0)
    res = run_backtest(df, entry, np.zeros(5, bool), stop, cost=0.0)
    t = res.trades[0]
    assert t.exit_reason == "stop" and t.exit_date == idx[3]       # close 8 < 9 on day 2 -> sell day 3 open
