import os
import sys

os.environ["MAX_DYNAMIC_SYMBOLS"] = "120"
os.environ["MIN_DYNAMIC_QUOTE_VOLUME"] = "1000000"
os.environ["DYNAMIC_SYMBOLS_TTL_SECONDS"] = "0"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import market_analyzer as ma  # noqa: E402


OLD_ALLOWED = set(ma.ALLOWED_DYNAMIC_BASE_ASSETS)


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def build_exchange_symbols():
    bases = list(ma.ALLOWED_DYNAMIC_BASE_ASSETS)
    bases += [
        "GALA", "SEI", "WLD", "TIA", "JUP", "ONDO", "PENDLE", "RENDER",
        "LDO", "WIF", "PYTH", "ENA", "MANTA", "STRK", "MAV", "BLUR",
        "SAGA", "ARKM", "EIGEN", "ALT", "ACE", "MAGIC", "ROSE", "KSM",
        "MKR", "COMP", "SNX", "CRV", "DYDX", "GMX", "TIA2", "XAI",
        "GMT", "AXS", "SAND", "MANA", "APE", "CHZ", "IMX", "FLOW",
        "MINA", "CELO", "ZEC", "DASH", "IOTA", "KAVA", "QTUM", "ZIL",
        "BAT", "ANKR", "HOT", "SKL", "IOST", "STORJ", "YFI", "ZRX",
        "ENS", "MASK", "LRC", "ONE", "ONT", "ZEN", "SFP", "CKB",
        "DENT", "ACH", "API3", "TRB", "SSV", "LPT", "GLM", "ID",
        "RDNT", "JOE", "CYBER", "NMR", "METIS", "UMA", "POLYX", "RPL",
        "PIXEL", "PORTAL", "BOME", "AEVO", "ETHFI", "OMNI", "NOT",
        "ZK", "ZRO", "BB", "IO", "LISTA", "BANANA", "CATI", "HMSTR",
    ]
    bases += ["USDC", "FDUSD", "BTCDOWN", "ETHUP", "PEPE", "1000MOG"]
    rows = []
    seen = set()
    for base in bases:
        symbol = f"{base}USDT"
        if symbol in seen:
            continue
        seen.add(symbol)
        rows.append({
            "symbol": symbol,
            "status": "TRADING",
            "permissions": ["SPOT"],
            "contractType": "PERPETUAL",
        })
    rows.append({"symbol": "OLDCONTRACTUSDT", "status": "TRADING", "contractType": "CURRENT_QUARTER"})
    rows.append({"symbol": "DEADUSDT", "status": "BREAK"})
    return {"symbols": rows}


def build_tickers():
    tickers = []
    exchange = build_exchange_symbols()["symbols"]
    volume = 500_000_000
    for row in exchange:
        symbol = row["symbol"]
        tickers.append({"symbol": symbol, "quoteVolume": str(volume)})
        volume -= 1_000_000
    tickers.append({"symbol": "LOWVOLUSDT", "quoteVolume": "1"})
    return tickers


def fake_market_json(url, timeout=12):
    if "exchangeInfo" in url:
        return build_exchange_symbols(), 200
    if "ticker/24hr" in url:
        return build_tickers(), 200
    return None, 404


def main():
    original = ma._safe_market_json
    try:
        ma.DYNAMIC_SYMBOL_CACHE.clear()
        ma.DYNAMIC_SYMBOL_CACHE.update({"time": 0, "symbols": None})
        ma._safe_market_json = fake_market_json
        selected = ma.get_scan_symbols(force_refresh=True)
    finally:
        ma._safe_market_json = original

    outside_old = [s for s in selected if s[:-4] not in OLD_ALLOWED]
    assert_true("GALAUSDT" in selected, "valid liquid symbol outside old allowlist was not selected")
    assert_true(outside_old, "no outside-old-allowlist symbols selected")
    assert_true(len(selected) > 30, f"MAX_DYNAMIC_SYMBOLS=120 did not allow more than 30 symbols: {len(selected)}")
    assert_true(len(selected) <= 120, f"selected count exceeds MAX_DYNAMIC_SYMBOLS: {len(selected)}")
    blocked = {"USDCUSDT", "FDUSDUSDT", "BTCDOWNUSDT", "ETHUPUSDT", "PEPEUSDT", "1000MOGUSDT"}
    assert_true(not blocked.intersection(selected), f"blocked assets leaked into selection: {blocked.intersection(selected)}")
    assert_true("OLDCONTRACTUSDT" not in selected, "non-perpetual futures leaked into selection")
    assert_true("DEADUSDT" not in selected, "inactive symbol leaked into selection")
    print(
        "DYNAMIC_SYMBOL_UNIVERSE_OK "
        f"selected={len(selected)} outside_old={len(outside_old)} "
        f"sample_outside={outside_old[:5]}"
    )


if __name__ == "__main__":
    main()
