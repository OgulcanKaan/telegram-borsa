# data.py
import time
import logging
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)
_INTERVALS = {"30m": "30m", "60m": "60m", "120m": "120m", "1d": "1d"}

def fetch_ohlcv(ticker: str, interval: str = "60m", period: str = "60d") -> pd.DataFrame | None:
    interval = _INTERVALS.get(interval, "60m")

    df = None
    for attempt in range(3):
        try:
            df = yf.download(
                ticker,
                interval=interval,
                period=period,
                progress=False,
                auto_adjust=False,
                threads=False,
            )
            if df is not None and not df.empty:
                break
        except Exception as e:
            logger.warning(f"YF indirme hatası ({ticker}, deneme {attempt+1}/3): {e}")
        time.sleep(0.6)

    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns={
        "Open":"open","High":"high","Low":"low","Close":"close","Adj Close":"adj_close","Volume":"volume"
    }).copy()

    for col in ["open","high","low","close","adj_close","volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna()

    # 🔒 İntraday ise son (kapanmamış) barı at → tutarlı skor
    if interval in ("30m", "60m", "120m") and len(df) > 1:
        df = df.iloc[:-1]

    return df if not df.empty else None
