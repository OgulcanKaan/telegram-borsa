# symbols.py
from pathlib import Path

# İstersen bu dosyanın yanına "symbols_bist250.txt" koy (her satır bir sembol, .IS ile)
# Dosya varsa oradan okur; yoksa alttaki varsayılan liste kullanılır.
DEFAULT_BIST250 = [
    "THYAO.IS","ASELS.IS","BIMAS.IS","KCHOL.IS","ALARK.IS","EREGL.IS","SISE.IS","TUPRS.IS","TOASO.IS","FROTO.IS",
    "HEKTS.IS","BRSAN.IS","AKBNK.IS","YKBNK.IS","GARAN.IS","ISCTR.IS","SAHOL.IS","PETKM.IS","ENJSA.IS","ULUSE.IS",
    "FENER.IS","KOZAA.IS","KRONT.IS","QUAGR.IS","TSKB.IS","ATAGY.IS","BAGFS.IS","VESBE.IS","VESTL.IS","MGROS.IS",
    # ... burayı kendi BIST-250 listenle genişletebilirsin
]

def load_bist_list() -> list[str]:
    p = Path(__file__).with_name("symbols_bist250.txt")
    if p.exists():
        syms = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return [s if s.endswith(".IS") else s + ".IS" for s in syms]
    return DEFAULT_BIST250

# 🔑 önemli: bu satır mutlaka olmalı
BIST_LIST = load_bist_list()
