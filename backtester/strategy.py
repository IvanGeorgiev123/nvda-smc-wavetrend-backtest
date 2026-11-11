"""Signal rules. Everything is decided at the CLOSE of a bar; the backtester fills at the NEXT bar's open.

Combined strategy ("SMC + WaveTrend"), long only:
  Trend filter (SMC)    : swing structure is bullish (last swing break was a bullish BOS/CHoCH).
  Entry trigger (WT)    : WaveTrend bullish cross while wt2 <= `entry_wt_max` (a pullback inside the uptrend),
                          or a WaveTrend bullish divergence (bottom at or below `div_level`).
  Exit (first that fires):
    - take profit       : WaveTrend bearish cross with wt2 >= `exit_wt_level` (overbought),
    - trend change      : swing structure turns bearish (bearish CHoCH),
    - protective stop   : close below the latest internal (short-term) swing low known at entry; if price is
                          already below that level, the lowest low of the last `stop_lookback` bars is used.

Variants for comparison (ablation):
  "WaveTrend only" : same WT entries/exits and stop, no SMC trend filter / trend exit.
  "SMC only"       : in the market whenever swing structure is bullish.
"""
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from .smc import market_structure, BULLISH, BEARISH
from .wavetrend import wavetrend, crosses, bullish_divergence, money_flow


@dataclass
class Params:
    swing_len: int = 50          # SMC swing structure length (TradingView default)
    internal_len: int = 5        # SMC internal structure length (TradingView default)
    entry_wt_max: float = 0.0    # only buy WT crosses that happen below the zero line
    div_level: float = -40.0     # Cipher B "2nd divergence" level
    use_divergence: bool = True
    exit_wt_level: float = 60.0  # Cipher B overbought line 2
    use_stop: bool = True
    stop_lookback: int = 10      # fallback stop: lowest low of the last N bars

    def as_dict(self):
        return asdict(self)


def compute_indicators(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    wt1, wt2 = wavetrend(h, l, c)
    up, down = crosses(wt1, wt2)
    smc = market_structure(h, l, c, p.swing_len, p.internal_len)
    ind = pd.DataFrame(
        {
            "wt1": wt1,
            "wt2": wt2,
            "wt_cross_up": up,
            "wt_cross_down": down,
            "wt_bull_div": bullish_divergence(wt2, l, p.div_level),
            "money_flow": money_flow(o, h, l, c),
            "swing_bias": smc.swing_bias,
            "internal_bias": smc.internal_bias,
            "swing_high": smc.swing_high,
            "swing_low": smc.swing_low,
            "internal_low": smc.internal_low,
        },
        index=df.index,
    )
    recent_low = df["low"].rolling(p.stop_lookback).min().to_numpy()
    with np.errstate(invalid="ignore"):
        ind["stop_level"] = np.where(smc.internal_low < c, smc.internal_low, recent_low)
    ind.attrs["events"] = smc.events
    return ind


def build_variants(ind: pd.DataFrame, p: Params) -> dict:
    """Return {name: dict(entry=bool[], exit=bool[], stop=float[] or None)} for every strategy variant."""
    wt2 = ind["wt2"].to_numpy()
    with np.errstate(invalid="ignore"):
        wt_entry = ind["wt_cross_up"].to_numpy() & (wt2 <= p.entry_wt_max)
        if p.use_divergence:
            wt_entry = wt_entry | ind["wt_bull_div"].to_numpy()
        wt_exit = ind["wt_cross_down"].to_numpy() & (wt2 >= p.exit_wt_level)
    bull = ind["swing_bias"].to_numpy() == BULLISH
    bear = ind["swing_bias"].to_numpy() == BEARISH
    stop = ind["stop_level"].to_numpy() if p.use_stop else None

    return {
        "SMC + WaveTrend": dict(entry=bull & wt_entry, exit=wt_exit | bear, stop=stop),
        "WaveTrend only": dict(entry=wt_entry, exit=wt_exit, stop=stop),
        "SMC only": dict(entry=bull, exit=bear, stop=None),
    }
