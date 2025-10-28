# analyzers/patterns.py
import numpy as np, pandas as pd
from dataclasses import dataclass

@dataclass
class Pattern:
    name: str
    confidence: float
    direction: str   # 'long' | 'short'
    breakout_price: float
    stop: float
    targets: list[float]
    meta: dict

def _linreg(x, y):
    x, y = np.array(x), np.array(y)
    A = np.vstack([x, np.ones(len(x))]).T
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    return m, c

def _last(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return df.iloc[-n:].copy()

def detect_pennant_flag(df: pd.DataFrame, win: int = 50):
    w = _last(df, win); idx = np.arange(len(w))
    m_hi, c_hi = _linreg(idx, w["high"]); m_lo, c_lo = _linreg(idx, w["low"])
    if m_hi < 0 and m_lo > 0:
        spread0 = (m_hi*0 + c_hi) - (m_lo*0 + c_lo)
        spread1 = (m_hi*len(w) + c_hi) - (m_lo*len(w) + c_lo)
        if spread1 < spread0 * 0.7:
            last_x = len(w) - 1
            upper = m_hi*last_x + c_hi
            lower = m_lo*last_x + c_lo
            close = w["close"].iloc[-1]
            vol_spike = w["volume"].iloc[-1] > (w["volume"].rolling(20).mean().iloc[-1] * 1.2)

            if close > upper:
                pole = w["close"].iloc[-1] - w["low"].iloc[0]
                t1, t2 = close + pole*0.6, close + pole*1.0
                stop = max(lower, w["low"].iloc[-5:-1].min())
                conf = min(0.6 + (0.1 if vol_spike else 0.0), 0.9)
                return Pattern("Bullish Pennant/Flag Breakout", conf, "long", float(close), float(stop), [float(t1), float(t2)], {"upper":(m_hi,c_hi),"lower":(m_lo,c_lo),"window":len(df)-len(w)})

            if close < lower:
                pole = w["high"].iloc[0] - w["close"].iloc[-1]
                t1, t2 = close - pole*0.6, close - pole*1.0
                stop = min(upper, w["high"].iloc[-5:-1].max())
                conf = min(0.6 + (0.1 if vol_spike else 0.0), 0.9)
                return Pattern("Bearish Pennant/Flag Breakdown", conf, "short", float(close), float(stop), [float(t1), float(t2)], {"upper":(m_hi,c_hi),"lower":(m_lo,c_lo),"window":len(df)-len(w)})
    return None

def detect_triangle(df: pd.DataFrame, win: int = 80):
    w = _last(df, win); idx = np.arange(len(w))
    m_hi, c_hi = _linreg(idx, w["high"]); m_lo, c_lo = _linreg(idx, w["low"])
    spread0 = (m_hi*0 + c_hi) - (m_lo*0 + c_lo)
    spread1 = (m_hi*len(w) + c_hi) - (m_lo*len(w) + c_lo)
    if spread1 < spread0 * 0.65 and spread1 / w["close"].iloc[-1] < 0.08:
        last_x = len(w) - 1
        upper = m_hi*last_x + c_hi
        lower = m_lo*last_x + c_lo
        close = w["close"].iloc[-1]
        base = spread1
        vol_spike = w["volume"].iloc[-1] > (w["volume"].rolling(20).mean().iloc[-1] * 1.2)

        if close > upper:
            t1, t2 = close + base*0.8, close + base*1.2
            stop = max(lower, w["low"].iloc[-6:-1].min())
            conf = min(0.55 + (0.1 if vol_spike else 0.0), 0.85)
            return Pattern("Ascending/Symmetric Triangle Breakout", conf, "long", float(close), float(stop), [float(t1), float(t2)], {"upper":(m_hi,c_hi),"lower":(m_lo,c_lo),"window":len(df)-len(w)})

        if close < lower:
            t1, t2 = close - base*0.8, close - base*1.2
            stop = min(upper, w["high"].iloc[-6:-1].max())
            conf = min(0.55 + (0.1 if vol_spike else 0.0), 0.85)
            return Pattern("Descending/Symmetric Triangle Breakdown", conf, "short", float(close), float(stop), [float(t1), float(t2)], {"upper":(m_hi,c_hi),"lower":(m_lo,c_lo),"window":len(df)-len(w)})
    return None

def detect_double_bottom(df: pd.DataFrame, lookback: int = 200, tol: float = 0.02):
    w = _last(df, lookback)
    lows, highs = w["low"].values, w["high"].values
    piv = []
    for i in range(2, len(lows)-2):
        if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
            piv.append(i)
    if len(piv) < 2: return None

    i2 = piv[-1]; i1 = None
    for j in reversed(piv[:-1]):
        if abs(lows[j] - lows[i2]) / max(1e-8, w["close"].iloc[-1]) < tol and (i2 - j) >= 5:
            i1 = j; break
    if i1 is None: return None

    left, right = min(i1,i2), max(i1,i2)
    neckline = float(np.max(highs[left:right+1]))
    close = float(w["close"].iloc[-1])
    if close > neckline:
        depth = abs(neckline - min(lows[i1], lows[i2]))
        t1, t2 = neckline + depth*0.8, neckline + depth*1.2
        stop = min(lows[i1], lows[i2])
        return Pattern("Double Bottom Breakout", 0.6, "long", close, float(stop), [float(t1), float(t2)], {"pivots":(i1,i2),"neckline":neckline,"window":len(df)-len(w)})
    return None

def detect_all_patterns(df: pd.DataFrame):
    out = []
    for f in (detect_pennant_flag, detect_triangle, detect_double_bottom):
        try:
            p = f(df)
            if p: out.append(p)
        except Exception:
            pass
    return out
