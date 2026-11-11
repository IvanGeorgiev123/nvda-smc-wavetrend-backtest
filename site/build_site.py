"""Build site/index.html: a one-page project summary for non-traders, with the interactive chart.

Run after run.py:  python site/build_site.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backtester.interactive import rescale_js  # noqa: E402

RES = ROOT / "results"


def pct(v, signed=True):
    if abs(v) < 0.0005:
        return "0%"
    return (f"{v * 100:+.1f}%" if signed else f"{v * 100:.1f}%").replace("-", "−")


def main():
    m = pd.read_csv(RES / "metrics.csv").set_index("Strategy")
    y = pd.read_csv(RES / "yearly_returns.csv", index_col=0)
    fig = (RES / "web_figure.json").read_text(encoding="utf-8")
    s, b, spy = m.loc["SMC + WaveTrend"], m.loc["Buy & hold NVDA"], m.loc["Buy & hold SPY"]

    rows = []
    for year, r in y.iterrows():
        cells = []
        for col in ("SMC + WaveTrend", "Buy & hold NVDA", "Buy & hold SPY"):
            v = r[col]
            cells.append(f'<td class="{"pos" if v > 0 else "neg" if v < 0 else "flat"}">{pct(v)}</td>')
        note = " *" if year == y.index[-1] else ""
        rows.append(f"<tr><th scope=\"row\">{year}{note}</th>{''.join(cells)}</tr>")

    repl = {
        "__FIGURE__": fig,
        "__RESCALE__": rescale_js("chart"),
        "__ROWS__": "\n".join(rows),
        "__S_MULT__": f"${1 + s['Total return']:,.0f}",
        "__B_MULT__": f"${1 + b['Total return']:,.0f}",
        "__SPY_MULT__": f"${1 + spy['Total return']:,.1f}",
        "__S_CAGR__": pct(s["CAGR"], False),
        "__B_CAGR__": pct(b["CAGR"], False),
        "__SPY_CAGR__": pct(spy["CAGR"], False),
        "__S_DD__": f"{s['Max drawdown'] * 100:.0f}%".replace("-", "−"),
        "__B_DD__": f"{b['Max drawdown'] * 100:.0f}%".replace("-", "−"),
        "__TRADES__": f"{int(s['Trades'])}",
        "__WIN__": f"{s['Win rate'] * 100:.0f}%",
        "__INMKT__": f"{s['Time in market'] * 100:.0f}%",
        "__Y22S__": pct(y.loc[2022, "SMC + WaveTrend"]),
        "__Y22B__": pct(y.loc[2022, "Buy & hold NVDA"]),
        "__LASTYEAR__": str(y.index[-1]),
    }
    html = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
    for k, v in repl.items():
        html = html.replace(k, v)
    # site/index.html is the local copy; docs/index.html is what GitHub Pages serves
    for out in (Path(__file__).parent / "index.html", ROOT / "docs" / "index.html"):
        out.parent.mkdir(exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"Wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
