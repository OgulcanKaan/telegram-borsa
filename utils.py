# utils.py
def normalize_bist(sym: str) -> str:
    sym = sym.strip().upper()
    return sym if "." in sym else sym + ".IS"
