def normalize_targets(summary: dict, interval: str) -> dict:
    """
    build_signal_summary çıktısını yön ile tutarlı hale getirir:
    - Long ise H1/H2 fiyatın üzerinde, stop altında olur.
    - Short ise H1/H2 fiyatın altında, stop üstünde olur.
    Terslik varsa ATR tabanlı güvenli hedef/stop üretir.
    Ayrıca ETA (T1'e ulaşım süresi) hesaplar ve okunur formatta döner.
    """
    s = dict(summary or {})
    price = float(s.get("price", 0) or 0)
    atr   = float(s.get("atr", 0) or 0.01)  # 0'a bölünme önlemi
    t1    = float(s.get("t1", 0) or 0)
    t2    = float(s.get("t2", 0) or 0)
    stop  = float(s.get("stop", 0) or 0)
    bias_text = (s.get("bias_text") or "").upper()

    # interval'i dakika cinsine çevir
    def minutes_of(itv: str) -> float:
        itv = (itv or "").lower()
        if itv.endswith("m"): return float(itv[:-1])
        if itv.endswith("h"): return float(itv[:-1]) * 60.0
        if itv.endswith("d"): return float(itv[:-1]) * 60.0 * 24.0
        if itv.endswith("wk"): return float(itv[:-2]) * 60.0 * 24.0 * 7.0
        return 60.0  # varsayılan

    # Yön saptama
    if "SAT" in bias_text and "AL" not in bias_text:
        side = "short"
    elif "AL" in bias_text and "SAT" not in bias_text:
        side = "long"
    else:
        # belirsizse long varsayıyoruz
        side = "long"

    # Long/Short düzeltmeleri
    def fix_long():
        nonlocal t1, t2, stop
        # hedefler ters/yanlışsa ATR tabanlı üret
        if (t1 < price) or (t2 < price) or (t2 <= t1):
            t1 = round(price + 1.0 * atr, 2)
            t2 = round(price + 2.0 * atr, 2)
        # stop fiyatın altında olmalı
        if stop >= price or stop == 0:
            stop = round(max(price - 1.5 * atr, 0), 2)
        # alım bölgesi metni
        s["buy_zone"] = f"{price:.2f} üstü" if price >= t1 else f"{price:.2f} ± {atr:.2f}"

    def fix_short():
        nonlocal t1, t2, stop
        # hedefler ters/yanlışsa ATR tabanlı üret (aşağı)
        if (t1 > price) or (t2 > price) or (t2 >= t1):
            t1 = round(price - 1.0 * atr, 2)
            t2 = round(price - 2.0 * atr, 2)
        # stop fiyatın üstünde olmalı
        if stop <= price or stop == 0:
            stop = round(price + 1.5 * atr, 2)
        # giriş metni (short)
        s["buy_zone"] = f"{price:.2f} altı" if price <= t1 else f"{price:.2f} ± {atr:.2f}"

    if side == "long":
        fix_long()
    else:
        fix_short()

    # ETA hesapla (T1'e mesafe/ATR → bar sayısı → süre)
    dist = abs(t1 - price)
    bars = max(dist / max(atr, 1e-6), 1.0)   # en az 1 bar
    minutes = bars * minutes_of(interval)

    # okunabilir ETA
    if minutes < 90:
        eta = f"{int(round(minutes))} dk"
    elif minutes < 24*60:
        eta = f"{round(minutes/60, 1)} saat"
    else:
        eta = f"{round(minutes/(60*24), 1)} gün"

    # düzenlenmiş alanlar
    s["t1"] = t1
    s["t2"] = t2
    s["stop"] = stop
    s["eta"] = eta

    # bias_text küçük düzeltmesi
    orig_bias = s.get("bias_text", "")
    if side == "short" and "AL" in (orig_bias.upper()):
        s["bias_text"] = "SAT (kısa eğilim)"
    elif side == "long" and "SAT" in (orig_bias.upper()):
        s["bias_text"] = "AL (uzun eğilim)"

    return s
