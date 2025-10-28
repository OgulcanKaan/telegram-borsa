# analyzers/plotting.py
import io
import matplotlib
matplotlib.use("Agg")  # GUI backend kapalı (ana thread uyarıları biter)
import matplotlib.pyplot as plt
import pandas as pd
from .patterns import Pattern

def _apply_style():
    plt.rcParams["figure.figsize"] = (12, 6)
    plt.rcParams["axes.grid"] = True

def draw_analysis(df: pd.DataFrame, summary: dict) -> io.BytesIO:
    _apply_style()
    fig, ax = plt.subplots()
    ax.plot(df.index, df["close"], label="Close")

    pat: Pattern | None = summary.get("pattern")
    if pat and "upper" in pat.meta and "lower" in pat.meta:
        wlen = 60
        idx = list(range(wlen))
        m_hi, c_hi = pat.meta["upper"]; m_lo, c_lo = pat.meta["lower"]
        xs = df.index[-wlen:]
        upper = [m_hi*i + c_hi for i in idx]
        lower = [m_lo*i + c_lo for i in idx]
        ax.plot(xs, upper, linestyle="--", label="Üst trend")
        ax.plot(xs, lower, linestyle="--", label="Alt trend")

    price = float(summary["price"])
    t1 = float(summary["t1"]); t2 = float(summary["t2"]); stop = float(summary["stop"])
    ax.axhline(price, linewidth=1, label=f"Fiyat {price:.2f}")
    ax.axhline(t1, linestyle=":", label=f"Hedef1 {t1:.2f}")
    ax.axhline(t2, linestyle=":", label=f"Hedef2 {t2:.2f}")
    ax.axhline(stop, linestyle="-.", label=f"Stop {stop:.2f}")

    ax.legend(loc="best")
    ax.set_title("Formasyon + Analiz")

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    buf.seek(0)
    return buf
