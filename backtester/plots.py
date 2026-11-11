"""Charts (matplotlib, dark theme)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .metrics import yearly_returns

BG, PANEL, GRID, TEXT = "#0e1117", "#151a23", "#262d3a", "#d6dbe4"
GREEN, RED, ORANGE, BLUE, PURPLE, GRAY, GOLD = "#2ecc71", "#ff4d5e", "#ffa94d", "#4da3ff", "#b388ff", "#8a93a6", "#ffd43b"
COLORS = {"SMC + WaveTrend": BLUE, "WaveTrend only": PURPLE, "SMC only": ORANGE,
          "Buy & hold NVDA": GRAY, "Buy & hold SPY": "#5c6577"}

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL, "axes.edgecolor": GRID, "axes.labelcolor": TEXT,
    "xtick.color": TEXT, "ytick.color": TEXT, "text.color": TEXT, "grid.color": GRID, "axes.grid": True,
    "grid.linewidth": 0.6, "font.size": 10, "axes.titleweight": "bold", "legend.facecolor": PANEL,
    "legend.edgecolor": GRID, "savefig.facecolor": BG, "savefig.dpi": 150, "axes.axisbelow": True,
})


def _bias_background(ax, idx, bias, alpha=0.10):
    """Shade bullish swing structure green and bearish red."""
    bias = np.asarray(bias)
    start = 0
    for i in range(1, len(bias) + 1):
        if i == len(bias) or bias[i] != bias[start]:
            if bias[start] != 0:
                ax.axvspan(idx[start], idx[min(i, len(idx) - 1)], color=GREEN if bias[start] > 0 else RED,
                           alpha=alpha, lw=0)
            start = i


def _trade_markers(ax, df, res, size=60):
    buys = [d for d in res.buys if d in df.index]
    ax.scatter(buys, df.loc[buys, "open"], marker="^", s=size, color=GREEN, edgecolor="white", lw=0.5,
               zorder=5, label="Buy (next open)")
    for t in res.trades:
        if t.exit_date is not None and t.exit_date in df.index:
            ax.scatter(t.exit_date, t.exit_price, marker="v", s=size, zorder=5, edgecolor="white", lw=0.5,
                       color=ORANGE if t.exit_reason == "stop" else RED)
    ax.scatter([], [], marker="v", s=size, color=RED, edgecolor="white", lw=0.5, label="Sell: signal")
    ax.scatter([], [], marker="v", s=size, color=ORANGE, edgecolor="white", lw=0.5, label="Sell: stop")


def _wavetrend_panel(ax, ind, p):
    idx = ind.index
    ax.fill_between(idx, ind["wt1"], 0, color=BLUE, alpha=0.45, lw=0, label="WT1 (fast)")
    ax.fill_between(idx, ind["wt2"], 0, color="#3b2a8f", alpha=0.75, lw=0, label="WT2 (slow)")
    ax.axhline(p.exit_wt_level, color=RED, lw=0.8, ls="--")
    ax.axhline(-p.exit_wt_level, color=GREEN, lw=0.8, ls="--")
    ax.axhline(0, color=TEXT, lw=0.6, alpha=0.6)
    up, dn = ind["wt_cross_up"], ind["wt_cross_down"]
    ax.scatter(idx[up], ind["wt2"][up], s=8, color=GREEN, zorder=3)
    ax.scatter(idx[dn], ind["wt2"][dn], s=8, color=RED, zorder=3)
    div = ind["wt_bull_div"]
    ax.scatter(idx[div], np.full(div.sum(), -95), marker="o", s=18, color=GOLD, zorder=4, label="Bullish divergence")
    ax.set_ylim(-110, 110)
    ax.set_ylabel("WaveTrend")
    ax.legend(loc="upper left", fontsize=8, ncol=3)


def plot_overview(df, ind, res, bench, p, path, title):
    fig, axes = plt.subplots(3, 1, figsize=(15, 11), sharex=True, gridspec_kw={"height_ratios": [3, 1.3, 1.6]})
    ax = axes[0]
    _bias_background(ax, df.index, ind["swing_bias"])
    pos = res.position.to_numpy() > 0
    ax.plot(df.index, df["close"], color=TEXT, lw=0.9, label="NVDA close")
    ax.fill_between(df.index, df["close"].min() * 0.9, df["close"], where=pos, color=BLUE, alpha=0.18, lw=0,
                    label="In position")
    _trade_markers(ax, df, res, size=35)
    ax.set_yscale("log")
    ax.set_ylabel("Price (log, split-adjusted)")
    ax.set_title(title, loc="left")
    ax.legend(loc="upper left", fontsize=8, ncol=3)
    ax.text(0.995, 0.02, "background: SMC swing structure (green = bullish, red = bearish)", transform=ax.transAxes,
            ha="right", fontsize=8, color=GRAY)

    _wavetrend_panel(axes[1], ind, p)

    ax = axes[2]
    for name, r in {"SMC + WaveTrend": res, **bench}.items():
        ax.plot(r.equity.index, r.equity, color=COLORS.get(name, TEXT), lw=1.6 if name == "SMC + WaveTrend" else 1.1,
                label=name)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $1 (log)")
    ax.legend(loc="upper left", fontsize=8)
    axes[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_recent(df, ind, res, p, path, months=18):
    start = df.index[-1] - pd.DateOffset(months=months)
    d, i2 = df[df.index >= start], ind[ind.index >= start]
    x = np.arange(len(d))
    pos_of = {ts: k for k, ts in enumerate(d.index)}

    fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True, gridspec_kw={"height_ratios": [3, 1.2]})
    ax = axes[0]
    bias = i2["swing_bias"].to_numpy()
    for k in range(len(x)):
        if bias[k] != 0:
            ax.axvspan(k - 0.5, k + 0.5, color=GREEN if bias[k] > 0 else RED, alpha=0.07, lw=0)
    up = d["close"] >= d["open"]
    col = np.where(up, GREEN, RED)
    ax.vlines(x, d["low"], d["high"], color=col, lw=0.8)
    ax.bar(x, (d["close"] - d["open"]).abs().clip(lower=d["close"] * 0.0015), bottom=np.minimum(d["open"], d["close"]),
           color=col, width=0.7)

    # SMC structure breaks: horizontal line from the pivot to the bar that broke it
    first = df.index.get_loc(d.index[0])
    for ev in ind.attrs["events"]:
        if ev.bar < first or (ev.kind == "internal" and ev.tag != "CHoCH"):
            continue
        a, b = max(ev.pivot_bar - first, 0), ev.bar - first
        c = GREEN if ev.bias > 0 else RED
        ls, lw, fs = ("-", 1.2, 9) if ev.kind == "swing" else ("--", 0.8, 7)
        ax.hlines(ev.level, a, b, color=c, ls=ls, lw=lw)
        label = ev.tag if ev.kind == "swing" else f"i-{ev.tag}"
        ax.text((a + b) / 2, ev.level, label, color=c, fontsize=fs, ha="center",
                va="bottom" if ev.bias > 0 else "top")

    for t in res.trades:
        if t.entry_date in pos_of:
            ax.scatter(pos_of[t.entry_date], t.entry_price, marker="^", s=90, color=GREEN, edgecolor="white", zorder=6)
        if t.exit_date is not None and t.exit_date in pos_of:
            ax.scatter(pos_of[t.exit_date], t.exit_price, marker="v", s=90, edgecolor="white", zorder=6,
                       color=ORANGE if t.exit_reason == "stop" else RED)
            win = t.return_pct > 0
            ax.annotate(f"{t.return_pct * 100:+.1f}%", (pos_of[t.exit_date], t.exit_price),
                        xytext=(0, 11 if win else -13), textcoords="offset points", ha="center", fontsize=8,
                        va="bottom" if win else "top", color=GREEN if win else RED)
    ax.set_ylabel("Price")
    ax.set_title(f"Last {months} months: candles, SMC structure breaks (BOS / CHoCH, i- = internal) and trades",
                 loc="left")

    ax2 = axes[1]
    i2r = i2.reset_index(drop=True)
    _wavetrend_panel(ax2, i2r, p)
    ticks = list(range(0, len(x), max(len(x) // 12, 1)))
    ax2.set_xticks(ticks)
    ax2.set_xticklabels([d.index[k].strftime("%b %y") for k in ticks])
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_equity(results: dict, path):
    fig, axes = plt.subplots(2, 1, figsize=(14, 8.5), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    for name, r in results.items():
        lw = 2.0 if name == "SMC + WaveTrend" else 1.2
        ls = "--" if name.startswith("Buy & hold") and not name.endswith("NVDA") else "-"
        axes[0].plot(r.equity.index, r.equity, color=COLORS.get(name, TEXT), lw=lw, ls=ls, label=name)
        dd = r.equity / r.equity.cummax() - 1
        axes[1].plot(dd.index, dd * 100, color=COLORS.get(name, TEXT), lw=lw * 0.8)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Growth of $1 (log)")
    axes[0].set_title("Equity curves: strategy variants vs buy & hold", loc="left")
    axes[0].legend(loc="upper left")
    axes[1].set_ylabel("Drawdown %")
    axes[1].set_title("Drawdown from previous peak", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_yearly(results: dict, path):
    names = list(results)
    yr = pd.DataFrame({n: yearly_returns(results[n].equity) for n in names}) * 100
    fig, ax = plt.subplots(figsize=(14, 5.5))
    w = 0.8 / len(names)
    x = np.arange(len(yr))
    for k, n in enumerate(names):
        ax.bar(x + (k - (len(names) - 1) / 2) * w, yr[n], width=w, color=COLORS.get(n, TEXT), label=n)
    ax.axhline(0, color=TEXT, lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(yr.index.astype(str))
    ax.set_ylabel("Return %")
    ax.set_title("Calendar-year returns", loc="left")
    ax.legend(ncol=len(names), fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_trade_returns(res, path):
    r = np.array([t.return_pct for t in res.trades if t.exit_reason != "open"]) * 100
    fig, ax = plt.subplots(figsize=(10, 4.5))
    bins = np.linspace(min(r.min(), -1), max(r.max(), 1), 30)
    ax.hist(r[r > 0], bins=bins, color=GREEN, alpha=0.85, label=f"Winners ({(r > 0).sum()})")
    ax.hist(r[r <= 0], bins=bins, color=RED, alpha=0.85, label=f"Losers ({(r <= 0).sum()})")
    ax.axvline(0, color=TEXT, lw=0.8)
    ax.set_xlabel("Trade return % (after costs)")
    ax.set_ylabel("Trades")
    ax.set_title("SMC + WaveTrend: distribution of closed-trade returns", loc="left")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
