"""Interactive HTML dashboard (plotly): hover for values, drag to zoom, double-click to reset,
click legend items to show/hide lines."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BG, PANEL, GRID, TEXT = "#0e1117", "#151a23", "#262d3a", "#d6dbe4"
GREEN, RED, ORANGE, BLUE, PURPLE, GRAY = "#2ecc71", "#ff4d5e", "#ffa94d", "#4da3ff", "#b388ff", "#a3abbd"
LINE_COLORS = {"SMC + WaveTrend": BLUE, "WaveTrend only": PURPLE, "SMC only": ORANGE,
               "Buy & hold NVDA": GRAY, "Buy & hold SPY": "#6b7489"}


def _bias_segments(index, bias):
    segs, start = [], 0
    for i in range(1, len(bias) + 1):
        if i == len(bias) or bias[i] != bias[start]:
            if bias[start] != 0:
                segs.append((index[start], index[min(i, len(index) - 1)], bias[start]))
            start = i
    return segs


def build_figure(df, ind, results: dict, ticker: str) -> go.Figure:
    main = results["SMC + WaveTrend"]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.035, row_heights=[0.45, 0.33, 0.22],
                        subplot_titles=(f"{ticker} price with every buy and sell",
                                        "Growth of $1 invested at the start of the visible period (log scale)",
                                        "WaveTrend oscillator (entry/exit timing)"))

    # ---- row 1: candles + trades
    fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
                                 name=f"{ticker} price", increasing_line_color=GREEN, decreasing_line_color=RED,
                                 increasing_fillcolor=GREEN, decreasing_fillcolor=RED, line_width=1), row=1, col=1)

    tr = main.trades
    fig.add_trace(go.Scatter(
        x=[t.entry_date for t in tr], y=[t.entry_price for t in tr], mode="markers", name="Buy",
        marker=dict(symbol="triangle-up", size=12, color=GREEN, line=dict(color="white", width=1)),
        hovertemplate="<b>BUY</b> %{x|%d %b %Y}<br>Price $%{y:.2f}<extra></extra>"), row=1, col=1)
    closed = [t for t in tr if t.exit_date is not None]
    fig.add_trace(go.Scatter(
        x=[t.exit_date for t in closed], y=[t.exit_price for t in closed], mode="markers", name="Sell",
        marker=dict(symbol="triangle-down", size=12, line=dict(color="white", width=1),
                    color=[ORANGE if t.exit_reason == "stop" else RED for t in closed]),
        customdata=[[t.return_pct * 100, t.bars_held, "stop loss" if t.exit_reason == "stop" else "exit signal",
                     t.entry_date.strftime("%d %b %Y")] for t in closed],
        hovertemplate="<b>SELL</b> (%{customdata[2]}) %{x|%d %b %Y}<br>Price $%{y:.2f}<br>"
                      "Trade result <b>%{customdata[0]:+.1f}%</b><br>Bought %{customdata[3]}, held %{customdata[1]} trading days"
                      "<extra></extra>"), row=1, col=1)

    # SMC trend as background (green = bullish structure, red = bearish)
    for x0, x1, b in _bias_segments(df.index, ind["swing_bias"].to_numpy()):
        fig.add_vrect(x0=x0, x1=x1, fillcolor=GREEN if b > 0 else RED, opacity=0.07, line_width=0, layer="below",
                      row=1, col=1)

    # ---- row 2: equity lines
    for name, r in results.items():
        main_line = name == "SMC + WaveTrend"
        fig.add_trace(go.Scatter(
            x=r.equity.index, y=r.equity, mode="lines", name=name,
            line=dict(color=LINE_COLORS.get(name, TEXT), width=2.6 if main_line else 1.5,
                      dash="dot" if name.endswith("SPY") else None),
            visible=True if (main_line or name.startswith("Buy & hold")) else "legendonly",
            hovertemplate=f"<b>{name}</b><br>%{{x|%d %b %Y}}: $1 → $%{{y:,.2f}}<extra></extra>"), row=2, col=1)
    held = main.position.to_numpy() > 0
    fig.add_trace(go.Scatter(
        x=main.equity.index[~held], y=np.where(~held, main.equity, np.nan)[~held], mode="markers",
        marker=dict(size=2, color="#56607a"), name="Strategy in cash", hoverinfo="skip", visible="legendonly"),
        row=2, col=1)

    # ---- row 3: WaveTrend
    fig.add_trace(go.Scatter(x=ind.index, y=ind["wt1"], name="WT1 (fast)", line=dict(color=BLUE, width=1),
                             fill="tozeroy", fillcolor="rgba(77,163,255,0.25)",
                             hovertemplate="WT1 %{y:.1f}<extra></extra>"), row=3, col=1)
    fig.add_trace(go.Scatter(x=ind.index, y=ind["wt2"], name="WT2 (slow)", line=dict(color="#7b61ff", width=1),
                             fill="tozeroy", fillcolor="rgba(59,42,143,0.45)",
                             hovertemplate="WT2 %{y:.1f}<extra></extra>"), row=3, col=1)
    for lvl, col in ((60, RED), (-60, GREEN), (0, GRAY)):
        fig.add_hline(y=lvl, line=dict(color=col, width=1, dash="dash" if lvl else "solid"), opacity=0.6, row=3, col=1)

    fig.update_yaxes(type="log", title_text="Price $", row=1, col=1)
    fig.update_yaxes(type="log", title_text="$1 grew to", row=2, col=1)
    fig.update_yaxes(range=[-105, 105], title_text="WT", row=3, col=1)
    fig.update_xaxes(rangeslider_visible=False, showspikes=True, spikemode="across", spikecolor=GRAY, spikethickness=1)
    # zoom buttons with explicit date ranges (plotly's own range selector counts back from the wrong end)
    end = df.index[-1] + pd.Timedelta(days=3)
    spans = [("6M", pd.DateOffset(months=6)), ("1Y", pd.DateOffset(years=1)), ("3Y", pd.DateOffset(years=3)),
             ("5Y", pd.DateOffset(years=5)), ("All", None)]
    buttons = []
    for label, off in spans:
        start = df.index[0] - pd.Timedelta(days=3) if off is None else end - off
        buttons.append(dict(label=label, method="relayout",
                            args=[{"xaxis.range": [start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")]}]))
    fig.update_layout(updatemenus=[dict(type="buttons", direction="left", buttons=buttons, active=len(buttons) - 1,
                                        x=0, y=1.035,
                                        xanchor="left", yanchor="bottom", showactive=True, bgcolor=PANEL,
                                        bordercolor=GRID, font=dict(color=TEXT), pad=dict(r=4, t=0))])
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=PANEL, font=dict(color=TEXT, size=12),
        height=1100, autosize=True, hovermode="x unified", margin=dict(l=60, r=30, t=170, b=40),
        title=dict(text=f"<b>{ticker}: Smart Money Concepts + WaveTrend backtest</b><br>"
                        "<span style='font-size:13px;color:#8a93a6'>Drag to zoom · double-click to reset · "
                        "click legend items to show/hide lines · background = SMC trend</span>",
                   x=0.01, y=0.985, yanchor="top"),
        legend=dict(orientation="h", y=1.075, yanchor="bottom", x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    return fig


CONFIG = {"scrollZoom": False, "displaylogo": False, "responsive": True}


def build_dashboard(df, ind, results: dict, ticker: str, path):
    """Stand-alone offline HTML file (plotly.js embedded)."""
    fig = build_figure(df, ind, results, ticker)
    fig.write_html(path, include_plotlyjs=True, full_html=True, default_width="100%", default_height="1100px",
                   config=CONFIG, post_script=_RESCALE_JS)


def build_web_figure(df, ind, results: dict, ticker: str, path):
    """Figure JSON for the project web page (site/build_site.py): no title block, smaller height."""
    fig = build_figure(df, ind, results, ticker)
    fig.update_layout(title=None, height=980, margin=dict(l=55, r=20, t=110, b=30),
                      legend=dict(orientation="h", y=1.075, yanchor="bottom", x=0, font=dict(size=11)))
    path.write_text(fig.to_json(), encoding="utf-8")


def rescale_js(plot_id: str) -> str:
    return _RESCALE_JS.replace("{plot_id}", plot_id)


# Plotly keeps the full-history y range when you zoom in on dates; this rescales the two log-scale panels
# (price, equity) to the data that is actually visible.
_RESCALE_JS = """
var gd = document.getElementById('{plot_id}');
var busy = false;
function visibleRange(axis, keys, a, b) {
  var lo = Infinity, hi = -Infinity;
  gd._fullData.forEach(function (t) {           // _fullData holds decoded arrays (gd.data may be base64)
    if ((t.yaxis || 'y') !== axis || t.visible === false || t.visible === 'legendonly') return;
    keys.forEach(function (k) {
      var ys = t[k], xs = t.x;
      if (!ys || !xs) return;
      for (var i = 0; i < xs.length; i++) {
        var tx = new Date(xs[i]).getTime();
        if (tx < a || tx > b) continue;
        var v = +ys[i];
        if (v > 0 && isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; }
      }
    });
  });
  if (!(lo < hi)) return null;
  var pad = (Math.log10(hi) - Math.log10(lo)) * 0.05 + 0.01;
  return [Math.log10(lo) - pad, Math.log10(hi) + pad];
}
// equity curves (row 2) are rebased to $1 at the first visible day, so every line starts together
var eqIdx = [], eqOrig = [], eqTimes = [];
gd._fullData.forEach(function (t) {
  if (t.yaxis === 'y2' && t.y && t.mode === 'lines') {
    eqIdx.push(t.index);
    eqOrig.push(Array.prototype.slice.call(t.y).map(Number));
    eqTimes.push(Array.prototype.slice.call(t.x).map(function (d) { return new Date(d).getTime(); }));
  }
});
function rebase(a) {
  var ys = eqOrig.map(function (orig, k) {
    var times = eqTimes[k], base = NaN;
    for (var i = 0; i < times.length; i++) {
      if (times[i] >= a && isFinite(orig[i]) && orig[i] > 0) { base = orig[i]; break; }
    }
    if (!isFinite(base)) base = orig[0];
    return orig.map(function (v) { return v / base; });
  });
  return Plotly.restyle(gd, {y: ys}, eqIdx);
}
function rescale() {
  if (busy) return;
  busy = true;
  var xr = gd._fullLayout.xaxis.range.slice();
  var a = new Date(xr[0]).getTime(), b = new Date(xr[1]).getTime();
  rebase(a).then(function () {
    var upd = {'xaxis.range': xr}, r1 = visibleRange('y', ['low', 'high', 'y'], a, b), r2 = visibleRange('y2', ['y'], a, b);
    if (r1) upd['yaxis.range'] = r1;
    if (r2) upd['yaxis2.range'] = r2;
    return Plotly.relayout(gd, upd);
  }).then(function () { busy = false; }, function () { busy = false; });
}
gd.on('plotly_relayout', function (ev) {
  if (busy) return;
  var keys = Object.keys(ev || {});
  if (keys.some(function (k) { return k.indexOf('xaxis') === 0; })) rescale();
});
"""
