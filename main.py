# main.py
import asyncio
import os
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from utils import normalize_bist
from data import fetch_ohlcv
from analyzers.indicators import add_indicators
from analyzers.patterns import detect_all_patterns
from analyzers.scoring import build_signal_summary
from analyzers.plotting import draw_analysis
from analyzers.targets import normalize_targets
from scanner import scan_many
from symbols import BIST_LIST

# --- Logging & env ---
load_dotenv()
logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bot")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

HELP = (
    "Komutlar:\n"
    "/analiz TICKER [interval] [period]\n"
    "/score TICKER [interval] [period]\n"
    "/top10 [interval] [period]\n"
    "/top10kisa  (15m/14d + 30m/30d)\n"
    "/top10orta  (60m/60d + 90m/90d)\n"
    "/top10uzun  (1d/180d + 1d/365d)"
)

def pct_str(price: float, target: float, side: str = "long") -> str:
    """Hedefin yüzde farkını metin olarak döndürür: %+1.23% gibi."""
    try:
        if price <= 0:
            return "%0.00"
        pct = ((target - price) / price) * 100.0
        # short'ta da hedefler aşağıda olduğundan işaret doğal çıkar; formatı sabit tutuyoruz
        return f"%{pct:+.2f}"
    except Exception:
        return "%0.00"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Selam! Hisse analizi için komut ver.\n\n" + HELP)

async def analiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(HELP); return

    raw = context.args[0].upper()
    interval = context.args[1] if len(context.args) > 1 else "60m"
    period   = context.args[2] if len(context.args) > 2 else "60d"
    ticker = normalize_bist(raw)

    note = await update.message.reply_text(
        f"⏳ Analiz: {raw} → {ticker} | {interval}/{period}"
    )

    loop = asyncio.get_running_loop()
    try:
        df = await loop.run_in_executor(None, fetch_ohlcv, ticker, interval, period)
        if df is None or df.empty:
            await note.edit_text("Veri bulunamadı."); return

        df = await loop.run_in_executor(None, add_indicators, df)
        pats = await loop.run_in_executor(None, detect_all_patterns, df)
        summary = await loop.run_in_executor(None, build_signal_summary, df, pats)

        # Yön/tutarlılık + Zaman dilimine göre ATR ölçeklemesi
        summary = normalize_targets(summary, interval)

        img_bytes = await loop.run_in_executor(None, draw_analysis, df, summary)

        p = float(summary["price"])
        h1 = float(summary["t1"]); h2 = float(summary["t2"])
        stop = float(summary["stop"])
        # bias'a göre işaret doğal; sadece formatı ekliyoruz
        h1pct = pct_str(p, h1)
        h2pct = pct_str(p, h2)

        caption = (
            f"<b>{raw}</b> ({ticker}) — {interval}/{period}\n"
            f"Fiyat: <b>{summary['price']:.2f}</b> | ATR: {summary['atr']:.2f}\n"
            f"Öneri: <b>{summary['bias_text']}</b> | Skor: <b>{summary['score']:.0f}/100</b>\n"
            f"Durum: {summary['pattern_text']}\n"
            f"Alım Bölgesi: {summary['buy_zone']} | Stop: <b>{stop:.2f}</b>\n"
            f"Hedef1: <b>{h1:.2f}</b> ({h1pct}) | Hedef2: <b>{h2:.2f}</b> ({h2pct}) | ETA: {summary['eta']}"
        )
        await update.message.reply_photo(photo=img_bytes, caption=caption, parse_mode=ParseMode.HTML)
        await note.delete()
    except Exception as e:
        logger.exception("Analiz hatası: %s", e)
        await note.edit_text(f"❌ Hata: {e}")

async def score_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Kullanım: /score TICKER [interval] [period]"); return

    raw = context.args[0].upper()
    interval = context.args[1] if len(context.args) > 1 else "60m"
    period   = context.args[2] if len(context.args) > 2 else "60d"
    ticker = normalize_bist(raw)

    note = await update.message.reply_text(
        f"⏳ Skor hesaplanıyor: {raw} → {ticker} | {interval}/{period}"
    )

    loop = asyncio.get_running_loop()
    try:
        df = await loop.run_in_executor(None, fetch_ohlcv, ticker, interval, period)
        if df is None or df.empty:
            await note.edit_text("Veri bulunamadı."); return

        df = await loop.run_in_executor(None, add_indicators, df)
        pats = await loop.run_in_executor(None, detect_all_patterns, df)
        s = await loop.run_in_executor(None, build_signal_summary, df, pats)
        s = normalize_targets(s, interval)

        p = float(s["price"]); h1 = float(s["t1"]); h2 = float(s["t2"])
        h1pct = pct_str(p, h1); h2pct = pct_str(p, h2)

        await note.edit_text(
            f"<b>{raw}</b> ({ticker}) — {interval}/{period}\n"
            f"Skor: <b>{s['score']:.0f}</b> | Öneri: {s['bias_text']} | Fiyat: {s['price']:.2f}\n"
            f"H1: <b>{h1:.2f}</b> ({h1pct}) | H2: <b>{h2:.2f}</b> ({h2pct}) | ETA: {s['eta']}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await note.edit_text(f"❌ Hata: {e}")

async def top10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    interval = context.args[0] if len(context.args) > 0 else "60m"
    period   = context.args[1] if len(context.args) > 1 else "60d"

    note = await update.message.reply_text(
        f"⏳ Taramaya başlandı: {len(BIST_LIST)} sembol | {interval}/{period}"
    )
    try:
        results, skipped = await scan_many(BIST_LIST, interval, period, limit=None, return_skipped=True)
        if not results:
            await note.edit_text("Sonuç yok."); return

        results = sorted(results, key=lambda x: (x[1].get("score",0), x[0]), reverse=True)
        top10_list = results[:10]
        cutoff = top10_list[-1][1].get("score", 0)

        lines = []
        for i, (tic, s) in enumerate(top10_list, start=1):
            s = normalize_targets(s, interval)
            p = float(s["price"]); h1 = float(s["t1"]); h2 = float(s["t2"])
            h1pct = pct_str(p, h1); h2pct = pct_str(p, h2)
            lines.append(
                f"{i:02d}. <b>{tic}</b> — Skor: <b>{s['score']:.0f}</b> | "
                f"Öneri: {s['bias_text']} | Fiyat: {s['price']:.2f}\n"
                f"Alım: {s['buy_zone']} | Stop: {s['stop']} | "
                f"H1: {h1:.2f} ({h1pct}) | H2: {h2:.2f} ({h2pct}) | ETA: {s['eta']}"
            )

        txt = f"🔥 <b>TOP 10</b> — {interval}/{period}\n" + "\n".join(lines)
        txt += f"\n\n<i>Cutoff (10. sıra) skor:</i> <b>{cutoff:.0f}</b>"

        if skipped:
            txt += f"\n\n<i>Atlanan:</i> {', '.join(skipped[:12])}"

        await note.edit_text(txt, parse_mode=ParseMode.HTML)
    except Exception as e:
        await note.edit_text(f"❌ Hata: {e}")

# --- Preset Top10 (multi timeframe) ---
async def run_presets(update: Update, presets, title: str):
    note = await update.message.reply_text(f"⏳ {title} için tarama başlıyor…")
    combined = {}

    for interval, period in presets:
        results, _ = await scan_many(BIST_LIST, interval, period, limit=None, return_skipped=True)
        for tic, s in results:
            if tic not in combined:
                combined[tic] = {"scores": [], "data": s, "interval": interval}
            combined[tic]["scores"].append(s["score"])

    averaged = []
    for tic, val in combined.items():
        avg_score = sum(val["scores"]) / max(len(val["scores"]), 1)
        data = normalize_targets(val["data"], val["interval"])
        averaged.append((tic, avg_score, data))

    averaged.sort(key=lambda x: x[1], reverse=True)
    top10 = averaged[:10]

    lines = []
    for i, (tic, score, s) in enumerate(top10, start=1):
        p = float(s["price"]); h1 = float(s["t1"]); h2 = float(s["t2"])
        h1pct = pct_str(p, h1); h2pct = pct_str(p, h2)
        lines.append(
            f"{i:02d}. <b>{tic}</b> — Ortalama Skor: <b>{score:.0f}</b>\n"
            f"Öneri: {s['bias_text']} | Fiyat: {s['price']:.2f}\n"
            f"Alım: {s['buy_zone']} | Stop: {s['stop']}\n"
            f"H1: {h1:.2f} ({h1pct}) | H2: {h2:.2f} ({h2pct}) | ETA: {s['eta']}\n"
        )

    txt = f"🔥 <b>TOP 10 {title}</b>\n\n" + "\n".join(lines)
    await note.edit_text(txt, parse_mode=ParseMode.HTML)

async def top10kisa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    presets = [("15m", "14d"), ("30m", "30d")]
    await run_presets(update, presets, "Kısa Vade")

async def top10orta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 120m Yahoo'da desteklenmiyor → 90m kullanalım
    presets = [("60m", "60d"), ("90m", "90d")]
    await run_presets(update, presets, "Orta Vade")

async def top10uzun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    presets = [("1d", "180d"), ("1d", "365d")]
    await run_presets(update, presets, "Uzun Vade")

# --- App bootstrap ---
def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN yok. .env dosyasını doldur.")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analiz", analiz))
    app.add_handler(CommandHandler("score", score_cmd))
    app.add_handler(CommandHandler("top10", top10))
    app.add_handler(CommandHandler("top10kisa", top10kisa))
    app.add_handler(CommandHandler("top10orta", top10orta))
    app.add_handler(CommandHandler("top10uzun", top10uzun))

    logger.info("Bot çalışıyor…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
