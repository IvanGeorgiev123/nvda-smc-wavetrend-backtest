"""Minimal long-only, all-in backtester for daily bars.

- A signal seen at the close of bar i is filled at the open of bar i+1 (no look-ahead).
- `cost` is charged on every fill (commission + slippage, as a fraction of the traded value).
- The stop level is frozen at entry: the strategy's stop series value on the signal bar.
- Equity is marked to the close of every bar.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp | None
    exit_price: float | None
    exit_reason: str
    return_pct: float            # after costs
    bars_held: int


@dataclass
class BacktestResult:
    equity: pd.Series            # starts at 1.0
    position: pd.Series          # 1 while holding at the close, else 0
    trades: list
    buys: list                   # fill dates
    sells: list


def run_backtest(df: pd.DataFrame, entry, exit_, stop=None, cost: float = 0.001) -> BacktestResult:
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    idx, n = df.index, len(df)
    entry, exit_ = np.asarray(entry, bool), np.asarray(exit_, bool)

    cash, shares = 1.0, 0.0
    equity, position = np.empty(n), np.zeros(n)
    pending, reason, stop_px = None, "", np.nan
    trades, buys, sells = [], [], []
    open_trade = None

    for i in range(n):
        # 1) fill yesterday's order at today's open
        if pending == "buy":
            shares, cash = cash * (1 - cost) / o[i], 0.0
            open_trade = dict(date=idx[i], price=o[i], bar=i, value_in=shares * o[i] / (1 - cost))
            buys.append(idx[i])
        elif pending == "sell":
            cash, shares = shares * o[i] * (1 - cost), 0.0
            trades.append(Trade(open_trade["date"], open_trade["price"], idx[i], o[i], reason,
                                cash / open_trade["value_in"] - 1, i - open_trade["bar"]))
            sells.append(idx[i])
            open_trade, stop_px = None, np.nan
        pending = None

        # 2) mark to market
        equity[i] = cash + shares * c[i]
        position[i] = 1.0 if shares > 0 else 0.0
        if i == n - 1:
            break

        # 3) decide at the close
        if shares > 0:
            if exit_[i]:
                pending, reason = "sell", "signal"
            elif not np.isnan(stop_px) and c[i] < stop_px:
                pending, reason = "sell", "stop"
        elif entry[i]:
            pending = "buy"
            s = np.nan if stop is None else stop[i]
            stop_px = s if (not np.isnan(s) and s < c[i]) else np.nan

    if open_trade is not None:                               # still holding on the last bar
        trades.append(Trade(open_trade["date"], open_trade["price"], None, None, "open",
                            equity[-1] / open_trade["value_in"] - 1, n - 1 - open_trade["bar"]))

    return BacktestResult(pd.Series(equity, idx), pd.Series(position, idx), trades, buys, sells)


def buy_and_hold(df: pd.DataFrame, cost: float = 0.001) -> BacktestResult:
    """Buy at the first bar's open, never sell."""
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    shares = (1 - cost) / o[0]
    eq = pd.Series(shares * c, df.index)
    trade = Trade(df.index[0], o[0], None, None, "open", eq.iloc[-1] - 1, len(df) - 1)
    return BacktestResult(eq, pd.Series(1.0, df.index), [trade], [df.index[0]], [])
