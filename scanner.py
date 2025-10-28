# scanner.py
import asyncio
from typing import List, Tuple, Optional
from data import fetch_ohlcv
from analyzers.indicators import add_indicators
from analyzers.patterns import detect_all_patterns
from analyzers.scoring import build_signal_summary

_SEM = asyncio.Semaphore(5)
_DELAY = 0.2

async def analyze_one(ticker: str, interval: str, period: str, loop) -> Optional[Tuple[str, dict]]:
    try:
        async with _SEM:
            await asyncio.sleep(_DELAY)
            df = await loop.run_in_executor(None, fetch_ohlcv, ticker, interval, period)
        if df is None or df.empty:
            return None
        df = await loop.run_in_executor(None, add_indicators, df)
        pats = await loop.run_in_executor(None, detect_all_patterns, df)
        summary = await loop.run_in_executor(None, build_signal_summary, df, pats)
        return ticker, summary
    except Exception:
        return None

async def scan_many(
    tickers: List[str],
    interval: str,
    period: str,
    limit: int | None = None,
    return_skipped: bool = False,
):
    loop = asyncio.get_running_loop()
    tasks = [analyze_one(t, interval, period, loop) for t in tickers]
    results: List[Tuple[str, dict]] = []
    skipped: List[str] = []

    for t, coro in zip(tickers, asyncio.as_completed(tasks)):
        res = await coro
        if res:
            results.append(res)
        else:
            skipped.append(t)

    # deterministik: skor ↓, eşitse sembol adı ↓
    results.sort(key=lambda kv: (kv[1].get("score", 0), kv[0]), reverse=True)

    if limit is not None:
        results = results[:limit]

    return (results, skipped) if return_skipped else results
