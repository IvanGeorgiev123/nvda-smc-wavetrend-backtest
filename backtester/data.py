"""Daily OHLCV download (Yahoo Finance via yfinance) with a local CSV cache so runs are reproducible offline."""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_prices(ticker: str, start: str = "2012-01-01", end: str | None = None, refresh: bool = False) -> pd.DataFrame:
    """Return split/dividend-adjusted daily bars with lowercase columns open/high/low/close/volume."""
    path = DATA_DIR / f"{ticker}.csv"
    if path.exists() and not refresh:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    else:
        import yfinance as yf

        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if df.empty:
            raise RuntimeError(f"No data returned for {ticker}")
        if isinstance(df.columns, pd.MultiIndex):          # yfinance >= 0.2.40 returns (field, ticker) columns
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.index.name = "date"
        # drop today's bar if the US session has not closed yet (an unfinished candle would change later)
        now_ny = pd.Timestamp.now(tz="America/New_York")
        if len(df) and df.index[-1].date() == now_ny.date() and now_ny.hour < 17:
            df = df.iloc[:-1]
        DATA_DIR.mkdir(exist_ok=True)
        df.to_csv(path)
    df = df[df.index >= pd.Timestamp(start)]
    if end is not None:
        df = df[df.index < pd.Timestamp(end)]
    return df
