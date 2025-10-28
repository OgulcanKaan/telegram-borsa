# analyzers/scoring.py
import pandas as pd
from .patterns import Pattern

def _indicator_bias(df: pd.DataFrame) -> tuple[str, float]:
    last = df.iloc[-1]
    score = 50.0
    long_pts = 0
    if last["rsi"] > 50: long_pts += 1; score += 10
    if last["macd"] > last["macd_signal"] > 0: long_pts += 1; score += 10
    if 20 <= last["adx"] <= 60: long_pts += 1; score += 10
    if last["cmf"] > 0: long_pts += 1; score += 5
    if last["volume"] > last["vol_ma20"] * 1.2: long_pts += 1; score += 5

    if long_pts >= 3: return "AL (uzun eğilim)", min(score, 90.0)
    if long_pts == 2: return "NÖTR/İZLE", 60.0
    return "SAT (zayıf)", 45.0

def _eta_by_atr(atr: float, price: float, target: float) -> str:
    if atr <= 0: return "3-7 gün"
    bars = abs(target - price) / max(atr, 1e-8)
    days = bars / 24  # ~60m barlar için yaklaşık
    if days < 2: return "1-2 gün"
    if days < 6: return "2-5 gün"
    return "5-10 gün"

def build_signal_summary(df: pd.DataFrame, patterns: list[Pattern]):
    price = float(df["close"].iloc[-1])
    atr = float(df["atr"].iloc[-1]) if "atr" in df.columns else 0.0
    bias_text, bias_score = _indicator_bias(df)

    best = max(patterns, key=lambda p: p.confidence) if patterns else None
    if best and best.direction == "long":
        t1, t2 = best.targets
        base_score = bias_score + best.confidence * 20
        return {
            "price": price, "atr": atr, "bias_text": bias_text,
            "pattern_text": f"{best.name} (güven {best.confidence*100:.0f}%)",
            "score": min(base_score, 100.0),
            "buy_zone": f"{best.breakout_price:.2f} üstü",
            "stop": f"{best.stop:.2f}", "t1": f"{t1:.2f}", "t2": f"{t2:.2f}",
            "eta": _eta_by_atr(atr, price, t1), "pattern": best
        }

    t1 = price + atr * 1.5
    t2 = price + atr * 3.0
    stop_val = price - atr * 1.2
    return {
        "price": price, "atr": atr, "bias_text": bias_text,
        "pattern_text": "Belirgin formasyon yok (indikatör bazlı öneri)",
        "score": bias_score, "buy_zone": f"{price:.2f} ± {atr:.2f}",
        "stop": f"{stop_val:.2f}", "t1": f"{t1:.2f}", "t2": f"{t2:.2f}",
        "eta": _eta_by_atr(atr, price, t1), "pattern": None
    }
