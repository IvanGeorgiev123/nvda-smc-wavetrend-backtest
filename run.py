"""Run the full study: download data, compute signals, backtest every variant, write charts + tables.

Usage:
    python run.py                     # NVDA, 2013-01-01 to today (cached data)
    python run.py --refresh           # re-download prices
    python run.py --ticker AMD        # any Yahoo Finance ticker
"""
import argparse
from pathlib import Path

import pandas as pd

from backtester.data import load_prices
from backtester.engine import run_backtest, buy_and_hold
from backtester.metrics import summarize, format_table, yearly_returns
from backtester.strategy import Params, compute_indicators, build_variants
from backtester import plots
from backtester.interactive import build_dashboard, build_web_figure

ROOT = Path(__file__).resolve().parent
WARMUP_START = "2012-01-01"     # extra year of history so indicators are warmed up before trading starts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="NVDA")
    ap.add_argument("--benchmark", default="SPY")
    ap.add_argument("--start", default="2013-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--cost", type=float, default=0.001, help="cost per fill (0.001 = 0.10%%)")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    p = Params()

    full = load_prices(args.ticker, WARMUP_START, args.end, refresh=args.refresh)
    ind_full = compute_indicators(full, p)                   # indicators use history before --start
    variants_full = build_variants(ind_full, p)

    keep = full.index >= pd.Timestamp(args.start)
    df, ind = full[keep], ind_full[keep]
    ind.attrs["events"] = ind_full.attrs["events"]
    offset = int((~keep).sum())
    for ev in ind.attrs["events"]:                           # re-index events to the trimmed frame
        ev.bar -= offset
        ev.pivot_bar -= offset
    ind.attrs["events"] = [ev for ev in ind.attrs["events"] if ev.bar >= 0]

    results = {}
    for name, v in variants_full.items():
        stop = None if v["stop"] is None else v["stop"][keep]
        results[name] = run_backtest(df, v["entry"][keep], v["exit"][keep], stop, cost=args.cost)
    results[f"Buy & hold {args.ticker}"] = buy_and_hold(df, args.cost)

    bench = {f"Buy & hold {args.ticker}": results[f"Buy & hold {args.ticker}"]}
    try:
        b = load_prices(args.benchmark, args.start, args.end, refresh=args.refresh)
        b = b[b.index.isin(df.index)]
        results[f"Buy & hold {args.benchmark}"] = buy_and_hold(b, args.cost)
        bench[f"Buy & hold {args.benchmark}"] = results[f"Buy & hold {args.benchmark}"]
    except Exception as e:                                   # benchmark is optional
        print(f"Benchmark {args.benchmark} skipped: {e}")

    # ---- tables
    rows = [summarize(n, r) for n, r in results.items()]
    table = format_table(rows)
    pd.DataFrame(rows).to_csv(out / "metrics.csv", index=False)

    main_res = results["SMC + WaveTrend"]
    trades = pd.DataFrame([t.__dict__ for t in main_res.trades])
    trades.to_csv(out / "trades.csv", index=False)
    yr = pd.DataFrame({n: yearly_returns(r.equity) for n, r in results.items()})
    yr.to_csv(out / "yearly_returns.csv")

    # split check: first half vs second half of the sample (rules were NOT tuned on either half)
    mid = df.index[len(df) // 2]
    halves = []
    for label, lo, hi in (("First half", df.index[0], mid), ("Second half", mid, df.index[-1] + pd.Timedelta(days=1))):
        part = df[(df.index >= lo) & (df.index < hi)]
        m = (df.index >= lo) & (df.index < hi)
        v = variants_full["SMC + WaveTrend"]
        r1 = run_backtest(part, v["entry"][keep][m], v["exit"][keep][m], v["stop"][keep][m], cost=args.cost)
        r2 = buy_and_hold(part, args.cost)
        s1, s2 = summarize("x", r1), summarize("x", r2)
        halves.append({"Period": f"{label} ({part.index[0]:%Y-%m-%d} to {part.index[-1]:%Y-%m-%d})",
                       "Strategy CAGR": f"{s1['CAGR'] * 100:.1f}%", "Strategy max DD": f"{s1['Max drawdown'] * 100:.1f}%",
                       "Buy & hold CAGR": f"{s2['CAGR'] * 100:.1f}%", "Buy & hold max DD": f"{s2['Max drawdown'] * 100:.1f}%"})
    halves = pd.DataFrame(halves)

    with open(out / "summary.md", "w", encoding="utf-8") as f:
        f.write(f"# Results: {args.ticker} daily, {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}\n\n")
        f.write(f"Cost per fill: {args.cost * 100:.2f}% (commission + slippage). Signals at the close, fills at the next open.\n\n")
        f.write(table.to_markdown() + "\n\n## Robustness: two halves of the sample\n\n")
        f.write(halves.to_markdown(index=False) + "\n\n## Parameters\n\n")
        f.write(pd.Series(p.as_dict()).to_frame("value").to_markdown() + "\n")

    # ---- charts
    plots.plot_overview(df, ind, main_res, bench, p, out / "01_overview.png",
                        f"{args.ticker}: SMC + WaveTrend signals ({df.index[0]:%Y} to {df.index[-1]:%Y})")
    plots.plot_recent(df, ind, main_res, p, out / "02_recent_trades.png")
    plots.plot_equity(results, out / "03_equity_drawdown.png")
    plots.plot_yearly(results, out / "04_yearly_returns.png")
    plots.plot_trade_returns(main_res, out / "05_trade_returns.png")
    build_dashboard(df, ind, results, args.ticker, out / "interactive_chart.html")
    build_web_figure(df, ind, results, args.ticker, out / "web_figure.json")

    pd.set_option("display.width", 200)
    print(table.to_string())
    print()
    print(halves.to_string(index=False))
    print(f"\nWrote charts and tables to {out}")


if __name__ == "__main__":
    main()
