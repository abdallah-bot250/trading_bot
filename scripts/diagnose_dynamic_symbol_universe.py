import os
import sys
import types
import importlib.util

os.environ["MAX_DYNAMIC_SYMBOLS"] = "120"
os.environ["MIN_DYNAMIC_QUOTE_VOLUME"] = "2000000"
os.environ["DYNAMIC_SYMBOLS_TTL_SECONDS"] = "0"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if importlib.util.find_spec("requests") is None:
    sys.modules["requests"] = types.SimpleNamespace(get=lambda *args, **kwargs: None)

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


def build_kucoin_tickers():
    rows = []
    volume = 300_000_000
    bases = [
        "GALA", "SEI", "WLD", "TIA", "JUP", "ONDO", "PENDLE", "RENDER",
        "LDO", "WIF", "PYTH", "ENA", "MANTA", "STRK", "MAV", "BLUR",
        "SAGA", "ARKM", "EIGEN", "ALT", "ACE", "MAGIC", "ROSE", "KSM",
        "MKR", "COMP", "SNX", "CRV", "DYDX", "GMX", "GMT", "AXS",
        "SAND", "MANA", "APE", "CHZ", "IMX", "FLOW", "MINA", "CELO",
        "ZEC", "DASH", "IOTA", "KAVA", "QTUM", "ZIL", "BAT", "ANKR",
        "HOT", "SKL", "IOST", "STORJ", "YFI", "ZRX", "ENS", "MASK",
        "LRC", "ONE", "ONT", "ZEN", "SFP", "CKB", "DENT", "ACH",
        "API3", "TRB", "SSV", "LPT", "GLM", "ID", "RDNT", "JOE",
    ]
    bases += ["USDC", "BTCDOWN", "PEPE", "1000MOG"]
    for base in bases:
        rows.append({
            "symbol": f"{base}-USDT",
            "last": "1",
            "vol": str(volume),
            "volValue": str(volume),
        })
        volume -= 1_000_000
    rows.append({
        "symbol": "BASEBIG-USDT",
        "last": "2",
        "vol": "999999999",
        "volValue": "1",
    })
    return {"data": {"ticker": rows}}


def build_large_kucoin_tickers(total=1042, liquid=160):
    rows = []
    priority_bases = [
        "GALA", "SEI", "WLD", "TIA", "JUP", "ONDO", "PENDLE", "RENDER",
        "LDO", "WIF", "PYTH", "ENA", "MANTA", "STRK", "MAV", "BLUR",
        "SAGA", "ARKM", "EIGEN", "ALT", "ACE", "MAGIC", "ROSE", "KSM",
        "MKR", "COMP", "SNX", "CRV", "DYDX", "GMX", "GMT", "AXS",
        "SAND", "MANA", "APE", "CHZ", "IMX", "FLOW", "MINA", "CELO",
        "ZEC", "DASH", "IOTA", "KAVA", "QTUM", "ZIL", "BAT", "ANKR",
        "HOT", "SKL", "IOST", "STORJ", "YFI", "ZRX", "ENS", "MASK",
        "LRC", "ONE", "ONT", "ZEN", "SFP", "CKB", "DENT", "ACH",
        "API3", "TRB", "SSV", "LPT", "GLM", "ID", "RDNT", "JOE",
    ]
    for idx in range(total):
        if idx < len(priority_bases):
            base = priority_bases[idx]
        else:
            base = f"KQC{idx}"
        quote_turnover = 250_000_000 - (idx * 1_000_000) if idx < liquid else 1_000
        rows.append({
            "symbol": f"{base}-USDT",
            "last": "1",
            "vol": "999999999",
            "volValue": str(max(quote_turnover, 1)),
        })
    rows.extend([
        {"symbol": "USDC-USDT", "last": "1", "vol": "999999999", "volValue": "999999999"},
        {"symbol": "BTCDOWN-USDT", "last": "1", "vol": "999999999", "volValue": "999999999"},
        {"symbol": "1000MOG-USDT", "last": "1", "vol": "999999999", "volValue": "999999999"},
    ])
    return {"data": {"ticker": rows}}


def fake_binance_down_kucoin_ok(url, timeout=12):
    if "kucoin.com" in url:
        return build_kucoin_tickers(), 200
    return None, 451


def fake_production_like_kucoin_fallback(url, timeout=12):
    if "api.binance.us/api/v3/exchangeInfo" in url:
        rows = []
        for idx in range(186):
            rows.append({"symbol": f"BUS{idx}USDT", "status": "TRADING", "permissions": ["SPOT"]})
        return {"symbols": rows}, 200
    if "api.binance.us/api/v3/ticker/24hr" in url:
        return [{"symbol": f"BUS{idx}USDT", "quoteVolume": str(20_000_000 - idx)} for idx in range(13)], 200
    if "kucoin.com" in url:
        return build_large_kucoin_tickers(), 200
    return None, 451


def fake_binance_us_ticker_sample(url, timeout=12):
    return [
        {"symbol": "BTCUSDT", "quoteVolume": "250000000", "volume": "3900"},
        {"symbol": "GALAUSDT", "quoteVolume": "15000000", "volume": "12000000"},
        {"symbol": "LOWVOLUSDT", "quoteVolume": "1", "volume": "999999999"},
    ], 200


def fake_kucoin_ticker_sample(url, timeout=12):
    return {
        "code": "200000",
        "data": {
            "ticker": [
                {"symbol": "BTC-USDT", "last": "60000", "vol": "10", "volValue": "600000000"},
                {"symbol": "GALA-USDT", "last": "0.02", "vol": "100000000", "volValue": "9000000"},
                {"symbol": "BASEBIG-USDT", "last": "2", "vol": "999999999", "volValue": "1"},
            ]
        },
    }, 200


def fake_malformed_ticker_sample(url, timeout=12):
    return [{"pair": "BTCUSDT", "quote": "100000000"}], 200


def main():
    original = ma._safe_market_json
    try:
        ma._reset_symbol_universe_stats()
        ma._safe_market_json = fake_binance_us_ticker_sample
        volume_map, status, meta = ma._ticker_volume_map("https://api.binance.us/api/v3/ticker/24hr", "BINANCE_US_TICKER")
    finally:
        ma._safe_market_json = original
    assert_true(status == 200, "Binance US sample status was not 200")
    assert_true(meta["parsed_count"] == 3, f"Binance US sample parsed wrong count: {meta}")
    assert_true(volume_map.get("BTCUSDT") == 250_000_000, "Binance US quoteVolume was not parsed")
    assert_true(volume_map.get("GALAUSDT") == 15_000_000, "Binance US outside-old symbol was not parsed")

    try:
        ma._reset_symbol_universe_stats()
        ma._safe_market_json = fake_kucoin_ticker_sample
        fallback_selected, alt_status, alt_meta = ma._alternative_exchange_universe()
    finally:
        ma._safe_market_json = original
    assert_true(alt_status == "KUCOIN", "KuCoin sample did not report KUCOIN")
    assert_true(alt_meta["parsed_count"] == 3, f"KuCoin sample parsed wrong count: {alt_meta}")
    assert_true("BTCUSDT" in fallback_selected, "BTC-USDT did not normalize to BTCUSDT")
    assert_true("GALAUSDT" in fallback_selected, "KuCoin volValue quote turnover was not used")
    assert_true("BASEBIGUSDT" not in fallback_selected, "base volume was incorrectly used as quote turnover")

    try:
        ma._reset_symbol_universe_stats()
        ma._safe_market_json = fake_malformed_ticker_sample
        malformed_map, malformed_status, malformed_meta = ma._ticker_volume_map("https://api.binance.us/api/v3/ticker/24hr", "BINANCE_US_TICKER")
    finally:
        ma._safe_market_json = original
    assert_true(malformed_status == 200, "Malformed sample status was not 200")
    assert_true(not malformed_map and malformed_meta["raw_count"] == 1, "Malformed schema did not fail explicitly")
    assert_true(ma.SYMBOL_UNIVERSE_FILTER_STATS.get("schema_warnings"), "Malformed schema warning was not recorded")

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

    try:
        ma.DYNAMIC_SYMBOL_CACHE.clear()
        ma.DYNAMIC_SYMBOL_CACHE.update({"time": 0, "symbols": None})
        ma._safe_market_json = fake_binance_down_kucoin_ok
        fallback_selected = ma.get_scan_symbols(force_refresh=True)
    finally:
        ma._safe_market_json = original

    fallback_outside_old = [s for s in fallback_selected if s[:-4] not in OLD_ALLOWED]
    assert_true(len(fallback_selected) > 30, f"alternative fallback did not return more than 30 symbols: {len(fallback_selected)}")
    assert_true(fallback_outside_old, "alternative fallback returned only the old fixed universe")
    assert_true(not blocked.intersection(fallback_selected), f"blocked assets leaked into alternative fallback: {blocked.intersection(fallback_selected)}")
    assert_true("BASEBIGUSDT" not in fallback_selected, "KuCoin fallback used base volume instead of quote turnover")
    assert_true(
        "alternative_exchange_universe" in str(ma.SYMBOL_UNIVERSE_FILTER_STATS.get("fallback_reason")),
        "fallback_reason did not expose the alternative exchange universe",
    )

    try:
        ma.DYNAMIC_SYMBOL_CACHE.clear()
        ma.DYNAMIC_SYMBOL_CACHE.update({"time": 0, "symbols": None})
        ma._safe_market_json = fake_production_like_kucoin_fallback
        production_like_selected = ma.get_scan_symbols(force_refresh=True)
    finally:
        ma._safe_market_json = original
    assert_true(len(production_like_selected) > 30, f"production-like KuCoin fallback stayed too small: {len(production_like_selected)}")
    assert_true(ma.SYMBOL_UNIVERSE_FILTER_STATS.get("authoritative_universe_source") == "KUCOIN", "KuCoin was not authoritative in production-like fallback")
    assert_true(ma.SYMBOL_UNIVERSE_FILTER_STATS.get("kucoin_symbols_with_ticker", 0) > 800, "KuCoin parsed ticker universe was not used")
    assert_true(ma.SYMBOL_UNIVERSE_FILTER_STATS.get("kucoin_symbols_above_volume", 0) > 30, "KuCoin volume-filtered universe did not exceed 30")
    assert_true(
        ma.SYMBOL_UNIVERSE_FILTER_STATS.get("symbols_dropped_due_to_cross_exchange_requirement", -1) == 0,
        "KuCoin fallback incorrectly required Binance cross-exchange membership",
    )
    print(
        "DYNAMIC_SYMBOL_UNIVERSE_OK "
        f"selected={len(selected)} outside_old={len(outside_old)} "
        f"alternative_fallback={len(fallback_selected)} "
        f"production_like_kucoin={len(production_like_selected)} "
        f"sample_outside={outside_old[:5]}"
    )


if __name__ == "__main__":
    main()
