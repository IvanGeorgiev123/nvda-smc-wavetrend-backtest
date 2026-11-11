"""Performance statistics."""
import math

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def summarize(name: str, res) -> dict:
    eq = res.equity                                  # every strategy starts with $1 of capital
    rets = eq / eq.shift(1, fill_value=1.0) - 1      # first day measured against the starting $1
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    total = eq.iloc[-1] - 1
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    dd = eq / np.maximum(eq.cummax(), 1.0) - 1
    vol = rets.std() * math.sqrt(TRADING_DAYS)
    sharpe = rets.mean() / rets.std() * math.sqrt(TRADING_DAYS) if rets.std() > 0 else np.nan
    downside = rets[rets < 0].std()
    sortino = rets.mean() / downside * math.sqrt(TRADING_DAYS) if downside > 0 else np.nan

    closed = [t for t in res.trades if t.exit_reason != "open"]
    r = np.array([t.return_pct for t in closed])
    wins, losses = r[r > 0], r[r <= 0]
    pf = wins.sum() / -losses.sum() if losses.sum() < 0 else np.nan

    return {
        "Strategy": name,
        "Total return": total,
        "CAGR": cagr,
        "Max drawdown": dd.min(),
        "Volatility": vol,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Calmar": cagr / abs(dd.min()) if dd.min() < 0 else np.nan,
        "Time in market": res.position.mean(),
        "Trades": len(closed),
        "Win rate": len(wins) / len(r) if len(r) else np.nan,
        "Avg trade": r.mean() if len(r) else np.nan,
        "Profit factor": pf,
        "Avg trading days held": np.mean([t.bars_held for t in closed]) if closed else np.nan,
    }


def yearly_returns(equity: pd.Series) -> pd.Series:
    year_end = equity.groupby(equity.index.year).last()
    start = pd.Series([1.0], index=[year_end.index[0] - 1])      # starting capital
    return pd.concat([start, year_end]).pct_change().dropna()


PCT_COLS = ["Total return", "CAGR", "Max drawdown", "Volatility", "Time in market", "Win rate", "Avg trade"]


def format_table(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(rows).set_index("Strategy")
    out = df.copy().astype(object)
    for col in df.columns:
        if col in PCT_COLS:
            out[col] = df[col].map(lambda v: "-" if pd.isna(v) else f"{v * 100:,.1f}%")
        elif col == "Trades":
            out[col] = df[col].map(lambda v: f"{int(v)}")
        else:
            out[col] = df[col].map(lambda v: "-" if pd.isna(v) else f"{v:,.2f}")
    return out
