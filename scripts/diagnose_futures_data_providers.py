import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from market_analyzer import (  # noqa: E402
    _extract_futures_klines,
    _extract_futures_symbol_count,
    _extract_futures_ticker_count,
    _fetch_futures_json,
    _futures_klines_url,
    _futures_provider_metadata,
)


def main():
    symbol = "BTCUSDT"
    interval = "15m"
    limit = 5
    for provider in ["BINANCE_FUTURES", "BYBIT", "OKX", "KUCOIN_FUTURES"]:
        meta = _futures_provider_metadata(provider, symbol)
        exchange_payload, exchange_status, _body, exchange_exc = _fetch_futures_json(
            provider,
            "exchangeInfo",
            meta["exchange_info_url"],
            fallback_used=provider != "BINANCE_FUTURES",
        )
        ticker_payload, ticker_status, _body, ticker_exc = _fetch_futures_json(
            provider,
            "ticker/24hr",
            meta["ticker_url"],
            fallback_used=provider != "BINANCE_FUTURES",
        )
        klines_payload, klines_status, _body, klines_exc = _fetch_futures_json(
            provider,
            "klines",
            _futures_klines_url(provider, meta["symbol"], interval, limit),
            fallback_used=provider != "BINANCE_FUTURES",
        )
        rows = _extract_futures_klines(provider, klines_payload)
        print(
            "FUTURES_PROVIDER_DIAGNOSTIC "
            f"provider={provider} "
            f"symbol={meta['symbol']} "
            f"exchange_status={exchange_status} "
            f"ticker_status={ticker_status} "
            f"klines_status={klines_status} "
            f"symbols_loaded={_extract_futures_symbol_count(provider, exchange_payload)} "
            f"ticker_count={_extract_futures_ticker_count(provider, ticker_payload)} "
            f"klines_rows={0 if not rows else len(rows)} "
            f"exchange_exception={exchange_exc} "
            f"ticker_exception={ticker_exc} "
            f"klines_exception={klines_exc}"
        )
    print("FUTURES_DATA_PROVIDER_DIAGNOSTICS_OK")


if __name__ == "__main__":
    main()
