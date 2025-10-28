# analyzers/indicators.py
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, ADXIndicator
from ta.volume import ChaikinMoneyFlowIndicator
from ta.volatility import AverageTrueRange

def _series_1d(s: pd.Series) -> pd.Series:
    return pd.Series(getattr(s, "to_numpy")().ravel(), index=s.index, name=getattr(s, "name", None))

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    close = _series_1d(df["close"])
    high  = _series_1d(df["high"])
    low   = _series_1d(df["low"])
    vol   = _series_1d(df["volume"])

    df["rsi"] = RSIIndicator(close, window=14).rsi()

    macd = MACD(close)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    df["adx"] = ADXIndicator(high, low, close, window=14).adx()

    st = StochasticOscillator(high, low, close)
    df["stoch_k"] = st.stoch()
    df["stoch_d"] = st.stoch_signal()

    df["cmf"] = ChaikinMoneyFlowIndicator(high, low, close, vol).chaikin_money_flow()

    df["atr"] = AverageTrueRange(high, low, close, window=14).average_true_range()

    df["vol_ma20"] = vol.rolling(20).mean()

    return df.dropna()
