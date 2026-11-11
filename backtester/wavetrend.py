"""WaveTrend oscillator, crosses, bullish divergences and the money-flow area.

Python port of the WaveTrend part of the 'VuManChu Cipher B Divergences' TradingView script
(WaveTrend by LazyBear, divergence logic by RicardoSantos / VuManChu). Every value at bar i
uses only bars 0..i, so signals are known at the close of bar i.
"""
import numpy as np
import pandas as pd


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def sma(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).rolling(n).mean().to_numpy()


def shift(x: np.ndarray, k: int) -> np.ndarray:
    """x[k bars ago], NaN-padded (Pine's x[k])."""
    out = np.full(len(x), np.nan)
    if k < len(x):
        out[k:] = x[: len(x) - k]
    return out


def valuewhen(cond: np.ndarray, src: np.ndarray) -> np.ndarray:
    """Pine valuewhen(cond, src, 0): value of src at the most recent bar where cond was true."""
    out, cur = np.full(len(src), np.nan), np.nan
    for i in range(len(src)):
        if cond[i]:
            cur = src[i]
        out[i] = cur
    return out


def wavetrend(high, low, close, channel_len=9, average_len=12, ma_len=3):
    """Returns (wt1, wt2): the fast wave and its 3-bar SMA (the slow wave)."""
    src = (high + low + close) / 3.0
    esa = ema(src, channel_len)
    de = ema(np.abs(src - esa), channel_len)
    with np.errstate(divide="ignore", invalid="ignore"):
        ci = (src - esa) / (0.015 * de)
    wt1 = ema(np.nan_to_num(ci), average_len)
    wt2 = sma(wt1, ma_len)
    return wt1, wt2


def crosses(wt1: np.ndarray, wt2: np.ndarray):
    """Bullish cross (wt1 moves above wt2) and bearish cross (wt1 moves below wt2)."""
    p1, p2 = shift(wt1, 1), shift(wt2, 1)
    with np.errstate(invalid="ignore"):
        up = (wt1 > wt2) & (p1 <= p2)
        down = (wt1 < wt2) & (p1 >= p2)
    return up, down


def bullish_divergence(src: np.ndarray, low: np.ndarray, bot_limit: float) -> np.ndarray:
    """f_findDivs bullish signal: a 5-bar bottom fractal in `src` at or below `bot_limit` whose price low
    is lower than the previous fractal's low while the oscillator low is higher. The fractal sits 2 bars
    back, so the signal is only known 2 bars after the actual low (no look-ahead)."""
    s1, s2, s3, s4 = (shift(src, k) for k in (1, 2, 3, 4))
    with np.errstate(invalid="ignore"):
        bot = (s4 > s2) & (s3 > s2) & (s2 < s1) & (s2 < src) & (s2 <= bot_limit)
        low_prev = shift(valuewhen(bot, s2), 2)
        price_prev = shift(valuewhen(bot, shift(low, 2)), 2)
        return bot & (shift(low, 2) < price_prev) & (s2 > low_prev)


def money_flow(open_, high, low, close, period=60, multiplier=150.0, pos_y=2.5):
    """Cipher B 'RSI+MFI area': smoothed candle-body position inside the range. > 0 = buying pressure."""
    rng = np.where(high - low == 0, np.nan, high - low)
    return sma(np.nan_to_num((close - open_) / rng * multiplier), period) - pos_y
