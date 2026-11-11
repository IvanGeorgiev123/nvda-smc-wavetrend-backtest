"""Market-structure part of 'Smart Money Concepts' (LuxAlgo, CC BY-NC-SA 4.0), ported bar by bar.

Only the logic that decides structure breaks and trend bias is ported: swing/internal pivots (leg()),
break of structure (BOS) and change of character (CHoCH). Drawing code (labels, boxes, FVG, zones)
is omitted because it does not change these values.

How it works, in plain words:
- A pivot high is confirmed `size` bars after it happens (that bar's high is higher than the next `size` highs).
- When the close crosses ABOVE the latest pivot high, structure breaks bullish; if the trend was bearish
  that break is a CHoCH (trend change), otherwise a BOS (trend continuation). Mirror logic for lows.
- 'swing' structure uses size 50 (big picture), 'internal' structure uses size 5 (short term).
Everything at bar i uses bars 0..i only.
"""
from dataclasses import dataclass
import math

import numpy as np

BULLISH, BEARISH = 1, -1
_BULL_LEG, _BEAR_LEG = 1, 0


def _isna(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


@dataclass
class _Pivot:
    level: float = float("nan")
    crossed: bool = False
    bar: int = -1


@dataclass
class StructureEvent:
    bar: int          # bar where the close broke the level
    kind: str         # 'swing' | 'internal'
    bias: int         # BULLISH | BEARISH
    tag: str          # 'BOS' | 'CHoCH'
    level: float      # price level that was broken
    pivot_bar: int    # bar of the pivot that formed the level


class _Leg:
    """Pine leg(size) plus ta.change() history for one call site."""

    def __init__(self, size: int):
        self.size, self.leg, self.prev = size, 0, None

    def update(self, i, high, low):
        s = self.size
        if i >= s:
            if high[i - s] > high[i - s + 1 : i + 1].max():
                self.leg = _BEAR_LEG                    # confirmed pivot high -> new bearish leg
            elif low[i - s] < low[i - s + 1 : i + 1].min():
                self.leg = _BULL_LEG                    # confirmed pivot low -> new bullish leg
        change = None if self.prev is None else self.leg - self.prev
        self.prev = self.leg
        return change


@dataclass
class SMCResult:
    swing_bias: np.ndarray        # trend after bar i closes: +1 bullish, -1 bearish, 0 unknown
    internal_bias: np.ndarray
    swing_high: np.ndarray        # latest swing pivot levels known at bar i
    swing_low: np.ndarray
    internal_low: np.ndarray      # latest internal pivot low known at bar i (used as stop)
    events: list


def market_structure(high, low, close, swing_len: int = 50, internal_len: int = 5) -> SMCResult:
    h, l, c = (np.asarray(a, dtype=float) for a in (high, low, close))
    n = len(c)
    sw_hi, sw_lo, in_hi, in_lo = _Pivot(), _Pivot(), _Pivot(), _Pivot()
    bias = {"swing": 0, "internal": 0}
    legs = {"swing": _Leg(swing_len), "internal": _Leg(internal_len)}
    prev_level = {}                                   # ta.crossover / crossunder history per call site
    events: list[StructureEvent] = []
    out = {k: np.full(n, np.nan) for k in ("swing_high", "swing_low", "internal_low")}
    swing_bias, internal_bias = np.zeros(n, int), np.zeros(n, int)

    def update_pivots(i, kind, hi, lo):
        change = legs[kind].update(i, h, l)
        if not change:
            return
        s = legs[kind].size
        p, price = (lo, l[i - s]) if change == +1 else (hi, h[i - s])
        p.level, p.crossed, p.bar = float(price), False, i - s

    def cross(slot, i, level, above):
        prev = prev_level.get(slot)
        prev_level[slot] = level
        if i == 0 or _isna(level) or _isna(prev):
            return False
        return (c[i] > level and c[i - 1] <= prev) if above else (c[i] < level and c[i - 1] >= prev)

    def neq(a, b):                                    # Pine float a != b with na -> true when exactly one is na
        if _isna(a) or _isna(b):
            return _isna(a) != _isna(b)
        return a != b

    def detect(i, kind, hi, lo):
        internal = kind == "internal"
        extra = neq(in_hi.level, sw_hi.level) if internal else True     # skip internal breaks of swing levels
        if cross((kind, "up"), i, hi.level, True) and not hi.crossed and extra:
            tag = "CHoCH" if bias[kind] == BEARISH else "BOS"
            hi.crossed, bias[kind] = True, BULLISH
            events.append(StructureEvent(i, kind, BULLISH, tag, hi.level, hi.bar))
        extra = neq(in_lo.level, sw_lo.level) if internal else True
        if cross((kind, "down"), i, lo.level, False) and not lo.crossed and extra:
            tag = "CHoCH" if bias[kind] == BULLISH else "BOS"
            lo.crossed, bias[kind] = True, BEARISH
            events.append(StructureEvent(i, kind, BEARISH, tag, lo.level, lo.bar))

    for i in range(n):
        update_pivots(i, "swing", sw_hi, sw_lo)
        update_pivots(i, "internal", in_hi, in_lo)
        detect(i, "internal", in_hi, in_lo)
        detect(i, "swing", sw_hi, sw_lo)
        swing_bias[i], internal_bias[i] = bias["swing"], bias["internal"]
        out["swing_high"][i], out["swing_low"][i], out["internal_low"][i] = sw_hi.level, sw_lo.level, in_lo.level

    return SMCResult(swing_bias, internal_bias, out["swing_high"], out["swing_low"], out["internal_low"], events)
