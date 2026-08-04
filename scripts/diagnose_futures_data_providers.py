import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import market_analyzer as ma  # noqa: E402


def _run_provider_selection_self_test():
    original_fetch = ma._fetch_futures_json
    original_order = ma._futures_provider_order
    ma.FUTURES_PROVIDER_CYCLE_LOCK.clear()
    ma.FUTURES_PROVIDER_HEALTH_CACHE.clear()
    ma.MARKET_CONTEXT_CACHE.clear()
    ma.SIGNAL_SCAN_DIAGNOSTICS.clear()
    ma.SIGNAL_SCAN_DIAGNOSTICS["scan_cycle_id"] = "diagnostic-cycle"

    def fake_fetch(provider, endpoint, url, fallback_used=False):
        provider_key = str(provider or "").upper()
        if provider_key == "BINANCE_FUTURES":
            return None, 451, "blocked", None
        if provider_key == "BYBIT":
            return None, 403, "forbidden", None
        if provider_key == "OKX" and endpoint == "exchangeInfo":
            return {"data": [{"instId": "BTC-USDT-SWAP", "state": "live"}]}, 200, "ok", None
        if provider_key == "OKX" and endpoint == "ticker/24hr":
            return {"data": [{"instId": "BTC-USDT-SWAP", "last": "65000"}]}, 200, "ok", None
        if provider_key == "OKX" and endpoint == "klines":
            rows = []
            now = 1800000000000
            for i in range(6):
                rows.append([str(now + i * 900000), "1", "2", "0.9", "1.5", "100", "100", "100", "1"])
            return {"data": rows}, 200, "ok", None
        return None, 500, "unexpected", None

    try:
        ma._fetch_futures_json = fake_fetch
        ma._futures_provider_order = lambda: ["BINANCE_FUTURES", "BYBIT", "OKX", "KUCOIN_FUTURES"]
        for timeframe in ["15m", "30m", "1h", "4h"]:
            df = ma.get_futures_market_data("BTCUSDT", timeframe, limit=5)
            if df is None or df.empty:
                raise AssertionError(f"expected OKX dataframe for {timeframe}")
            provider = str(df.get("futures_data_provider", [""])[0])
            if provider != "OKX":
                raise AssertionError(f"expected OKX provider for {timeframe}, got {provider}")
        locked = ma.FUTURES_PROVIDER_CYCLE_LOCK.get("diagnostic-cycle", {}).get("provider")
        if locked != "OKX":
            raise AssertionError(f"expected cycle lock OKX, got {locked}")
        print("FUTURES_PROVIDER_SELECTION_SELF_TEST_OK")
    finally:
        ma._fetch_futures_json = original_fetch
        ma._futures_provider_order = original_order
        ma.FUTURES_PROVIDER_CYCLE_LOCK.clear()
        ma.FUTURES_PROVIDER_HEALTH_CACHE.clear()
        ma.MARKET_CONTEXT_CACHE.clear()
        ma.SIGNAL_SCAN_DIAGNOSTICS.clear()


def main():
    _run_provider_selection_self_test()
    symbol = "BTCUSDT"
    interval = "15m"
    limit = 5
    for provider in ["BINANCE_FUTURES", "BYBIT", "OKX", "KUCOIN_FUTURES"]:
        meta = ma._futures_provider_metadata(provider, symbol)
        exchange_payload, exchange_status, _body, exchange_exc = ma._fetch_futures_json(
            provider,
            "exchangeInfo",
            meta["exchange_info_url"],
            fallback_used=provider != "BINANCE_FUTURES",
        )
        ticker_payload, ticker_status, _body, ticker_exc = ma._fetch_futures_json(
            provider,
            "ticker/24hr",
            meta["ticker_url"],
            fallback_used=provider != "BINANCE_FUTURES",
        )
        klines_payload, klines_status, _body, klines_exc = ma._fetch_futures_json(
            provider,
            "klines",
            ma._futures_klines_url(provider, meta["symbol"], interval, limit),
            fallback_used=provider != "BINANCE_FUTURES",
        )
        rows = ma._extract_futures_klines(provider, klines_payload)
        print(
            "FUTURES_PROVIDER_DIAGNOSTIC "
            f"provider={provider} "
            f"symbol={meta['symbol']} "
            f"exchange_status={exchange_status} "
            f"ticker_status={ticker_status} "
            f"klines_status={klines_status} "
            f"symbols_loaded={ma._extract_futures_symbol_count(provider, exchange_payload)} "
            f"ticker_count={ma._extract_futures_ticker_count(provider, ticker_payload)} "
            f"klines_rows={0 if not rows else len(rows)} "
            f"exchange_exception={exchange_exc} "
            f"ticker_exception={ticker_exc} "
            f"klines_exception={klines_exc}"
        )
    print("FUTURES_DATA_PROVIDER_DIAGNOSTICS_OK")


if __name__ == "__main__":
    main()
