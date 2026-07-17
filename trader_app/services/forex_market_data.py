"""Backward-compatible Forex market-data facade.

The rest of the project imports this module, so it intentionally preserves the
old public API while delegating provider selection/fallback to
forex_provider_manager.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from trader_app.services import forex_provider_manager as manager


FOREX_SYMBOLS = manager.FOREX_SYMBOLS
FOREX_TIMEFRAMES = manager.FOREX_TIMEFRAMES

normalize_forex_symbol = manager.normalize_forex_symbol
provider_symbol = manager.provider_symbol
provider_interval = manager.provider_interval
asset_class_for_symbol = manager.asset_class_for_symbol
pip_size = manager.pip_size


@dataclass
class ForexCandlesResult:
    ok: bool
    symbol: str
    timeframe: str
    provider: str
    candles: List[dict]
    error: Optional[str] = None
    data_timestamp: Optional[str] = None
    stale: bool = False
    status_code: Optional[int] = None
    fallback_used: bool = False


@dataclass
class ForexQuoteResult:
    ok: bool
    symbol: str
    provider: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    price: Optional[float] = None
    spread: Optional[float] = None
    timestamp: Optional[str] = None
    spread_available: bool = False
    error: Optional[str] = None
    status_code: Optional[int] = None
    fallback_used: bool = False


def forex_failure_code(error: Optional[str], status_code: Optional[int] = None) -> str:
    text = str(error or "").strip()
    lower = text.lower()
    if status_code in {401, 403} or "api key" in lower or "apikey" in lower or "auth" in lower:
        return "AUTH_FAILED" if "missing" not in lower else "API_KEY_MISSING"
    if status_code == 429 or "rate limit" in lower:
        return "RATE_LIMITED"
    if status_code and int(status_code) >= 400:
        return "HTTP_ERROR"
    mapping = {
        "twelvedata_api_key_missing": "API_KEY_MISSING",
        "finnhub_api_key_missing": "API_KEY_MISSING",
        "oanda_provider_disabled": "OANDA_PROVIDER_DISABLED",
        "symbol_not_supported": "SYMBOL_NOT_SUPPORTED",
        "timeframe_not_supported": "TIMEFRAME_NOT_SUPPORTED",
        "empty_candles": "EMPTY_CANDLES",
        "stale_data": "STALE_DATA",
        "timeout": "TIMEOUT",
        "spread_unavailable": "SPREAD_UNAVAILABLE",
        "price_unavailable": "PRICE_UNAVAILABLE",
        "provider_not_supported": "PROVIDER_NOT_SUPPORTED",
        "ohlc_not_enabled": "OHLC_NOT_ENABLED",
    }
    return mapping.get(lower, "PARSE_ERROR" if text else "DATA_SOURCE_FAILURE")


def _candles_from_manager(result: manager.ProviderCandlesResult) -> ForexCandlesResult:
    return ForexCandlesResult(
        ok=bool(result.ok),
        symbol=result.symbol,
        timeframe=result.timeframe,
        provider=result.provider,
        candles=result.candles,
        error=result.error,
        data_timestamp=result.data_timestamp,
        stale=bool(result.stale),
        status_code=result.status_code,
        fallback_used=bool(result.fallback_used),
    )


def _quote_from_manager(result: manager.ProviderQuoteResult) -> ForexQuoteResult:
    return ForexQuoteResult(
        ok=bool(result.ok),
        symbol=result.symbol,
        provider=result.provider,
        bid=result.bid,
        ask=result.ask,
        price=result.price,
        spread=result.spread,
        timestamp=result.timestamp,
        spread_available=bool(result.spread_available),
        error=result.error,
        status_code=result.status_code,
        fallback_used=bool(result.fallback_used),
    )


def provider_configuration_status() -> dict:
    return manager.provider_configuration_status()


def provider_health_status() -> dict:
    return manager.provider_health_status()


def get_quote(symbol: str) -> ForexQuoteResult:
    return _quote_from_manager(manager.get_quote(symbol))


def get_pricing_quote(symbol: str) -> ForexQuoteResult:
    return _quote_from_manager(manager.get_pricing_quote(symbol))


def pricing_provider_health_status() -> dict:
    return manager.pricing_provider_health_status()


def request_budget_status() -> dict:
    return manager.request_budget_status()


def forex_symbols_for_cycle(symbols=None):
    return manager.forex_symbols_for_cycle(symbols)


def get_twelvedata_reference_price(symbol: str) -> ForexQuoteResult:
    """Return a Twelve Data reference price without changing the active provider."""
    return _quote_from_manager(manager._twelvedata_quote(manager.normalize_forex_symbol(symbol)))


def get_ohlcv(symbol: str, timeframe: str, outputsize: int = 120) -> ForexCandlesResult:
    return _candles_from_manager(manager.get_ohlcv(symbol, timeframe, outputsize))


def supported_symbols() -> List[str]:
    return manager.supported_symbols()


def unsupported_symbols() -> List[str]:
    return manager.unsupported_symbols()
