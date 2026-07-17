"""Multi-provider Forex market-data manager.

Provider priority:
1. Twelve Data (default/global)
2. Finnhub (optional)
3. OANDA v20 (optional enhancement)

No provider fabricates bid/ask or spread. If the selected provider has last
price only, spread is reported as unavailable and signal validation can still
continue when configured to allow that.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

from trader_app.services.forex_providers import oanda


FOREX_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "EURJPY", "GBPJPY", "XAUUSD", "XAGUSD", "USOIL", "UKOIL", "US30",
    "NAS100", "SPX500",
]

FOREX_TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h"]

TWELVEDATA_SYMBOL_MAP = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "USDCHF": "USD/CHF",
    "AUDUSD": "AUD/USD",
    "USDCAD": "USD/CAD",
    "NZDUSD": "NZD/USD",
    "EURJPY": "EUR/JPY",
    "GBPJPY": "GBP/JPY",
    "XAUUSD": "XAU/USD",
    "XAGUSD": "XAG/USD",
    "USOIL": "WTI/USD",
    "UKOIL": "BRENT/USD",
    "US30": "DJI",
    "NAS100": "NDX",
    "SPX500": "SPX",
}

TWELVEDATA_INTERVAL_MAP = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
}

FINNHUB_SYMBOL_MAP = {
    "EURUSD": "OANDA:EUR_USD",
    "GBPUSD": "OANDA:GBP_USD",
    "USDJPY": "OANDA:USD_JPY",
    "USDCHF": "OANDA:USD_CHF",
    "AUDUSD": "OANDA:AUD_USD",
    "USDCAD": "OANDA:USD_CAD",
    "NZDUSD": "OANDA:NZD_USD",
    "EURJPY": "OANDA:EUR_JPY",
    "GBPJPY": "OANDA:GBP_JPY",
    "XAUUSD": "OANDA:XAU_USD",
    "XAGUSD": "OANDA:XAG_USD",
}

ASSET_CLASS = {
    "XAUUSD": "metal",
    "XAGUSD": "metal",
    "USOIL": "oil",
    "UKOIL": "oil",
    "US30": "index",
    "NAS100": "index",
    "SPX500": "index",
}


@dataclass
class ProviderCandlesResult:
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
class ProviderQuoteResult:
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


_CANDLE_CACHE: Dict[Tuple[str, str, str, int], Tuple[float, ProviderCandlesResult]] = {}
_QUOTE_CACHE: Dict[Tuple[str, str], Tuple[float, ProviderQuoteResult]] = {}
_REQUEST_BUDGET = {
    "window_started": time.time(),
    "minute_used": 0,
    "day_started": datetime.now(timezone.utc).date().isoformat(),
    "day_used": 0,
    "rate_limit_hits": 0,
    "symbols_deferred": 0,
}
_LAST_STATUS = {
    "selected_provider": None,
    "provider_health": {},
    "fallback_used": False,
    "last_error": "",
    "checked_at": None,
}
_LAST_PRICING_STATUS = {
    "provider": None,
    "ok": False,
    "last_success_at": None,
    "last_error": "",
    "last_symbol": "",
}


def _env_int(name: str, default: int, minimum: int = 0, maximum: int = 3600) -> int:
    try:
        value = int(str(os.environ.get(name, default)).strip())
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


def _timeout() -> int:
    return _env_int("FOREX_REQUEST_TIMEOUT_SECONDS", 8, 2, 30)


def _cache_seconds() -> int:
    return _env_int("FOREX_CACHE_SECONDS", 180, 10, 3600)


def _cache_seconds_for_timeframe(timeframe: str) -> int:
    tf = str(timeframe or "").strip().lower()
    defaults = {
        "4h": 21600,
        "1h": 3600,
        "30m": 900,
        "15m": 300,
        "5m": 300,
    }
    env_names = {
        "4h": "FOREX_CACHE_SECONDS_4H",
        "1h": "FOREX_CACHE_SECONDS_1H",
        "30m": "FOREX_CACHE_SECONDS_30M",
        "15m": "FOREX_CACHE_SECONDS_15M",
        "5m": "FOREX_CACHE_SECONDS_5M",
    }
    return _env_int(env_names.get(tf, "FOREX_CACHE_SECONDS"), defaults.get(tf, _cache_seconds()), 30, 86400)


def _quote_cache_seconds() -> int:
    return _env_int("FOREX_QUOTE_CACHE_SECONDS", 15, 1, 300)


def _budget_limit_per_minute() -> int:
    return _env_int("FOREX_TWELVEDATA_REQUESTS_PER_MINUTE", 8, 1, 120)


def _budget_limit_per_day() -> int:
    return _env_int("FOREX_TWELVEDATA_REQUESTS_PER_DAY", 800, 1, 100000)


def _budget_daily_reserve() -> int:
    return _env_int("FOREX_TWELVEDATA_DAILY_RESERVE", 25, 0, 100000)


def _reset_budget_windows() -> None:
    now = time.time()
    if now - float(_REQUEST_BUDGET.get("window_started") or 0) >= 60:
        _REQUEST_BUDGET["window_started"] = now
        _REQUEST_BUDGET["minute_used"] = 0
    today = datetime.now(timezone.utc).date().isoformat()
    if _REQUEST_BUDGET.get("day_started") != today:
        _REQUEST_BUDGET["day_started"] = today
        _REQUEST_BUDGET["day_used"] = 0
        _REQUEST_BUDGET["rate_limit_hits"] = 0
        _REQUEST_BUDGET["symbols_deferred"] = 0


def request_budget_status() -> dict:
    _reset_budget_windows()
    minute_limit = _budget_limit_per_minute()
    day_limit = _budget_limit_per_day()
    reserve = _budget_daily_reserve()
    minute_used = int(_REQUEST_BUDGET.get("minute_used") or 0)
    day_used = int(_REQUEST_BUDGET.get("day_used") or 0)
    safe_daily_remaining = max(0, day_limit - reserve - day_used)
    return {
        "requests_used": day_used,
        "minute_used": minute_used,
        "requests_remaining_estimate": max(0, day_limit - day_used),
        "safe_daily_remaining": safe_daily_remaining,
        "minute_remaining": max(0, minute_limit - minute_used),
        "symbols_deferred": int(_REQUEST_BUDGET.get("symbols_deferred") or 0),
        "rate_limit_hits": int(_REQUEST_BUDGET.get("rate_limit_hits") or 0),
        "minute_limit": minute_limit,
        "daily_limit": day_limit,
        "daily_reserve": reserve,
    }


def _request_allowed(provider: str) -> Tuple[bool, str]:
    if str(provider or "").lower() != "twelvedata":
        return True, "OK"
    status = request_budget_status()
    if status["minute_remaining"] <= 0:
        _REQUEST_BUDGET["rate_limit_hits"] = int(_REQUEST_BUDGET.get("rate_limit_hits") or 0) + 1
        return False, "REQUEST_BUDGET_MINUTE_EXHAUSTED"
    if status["safe_daily_remaining"] <= 0:
        _REQUEST_BUDGET["rate_limit_hits"] = int(_REQUEST_BUDGET.get("rate_limit_hits") or 0) + 1
        return False, "REQUEST_BUDGET_DAILY_NEAR_LIMIT"
    return True, "OK"


def _record_request(provider: str, error: str = "") -> None:
    if str(provider or "").lower() != "twelvedata":
        return
    _reset_budget_windows()
    _REQUEST_BUDGET["minute_used"] = int(_REQUEST_BUDGET.get("minute_used") or 0) + 1
    _REQUEST_BUDGET["day_used"] = int(_REQUEST_BUDGET.get("day_used") or 0) + 1
    if str(error or "").upper() == "RATE_LIMITED":
        _REQUEST_BUDGET["rate_limit_hits"] = int(_REQUEST_BUDGET.get("rate_limit_hits") or 0) + 1
    status = request_budget_status()
    try:
        print(
            "FOREX_REQUEST_BUDGET "
            f"requests_used={status['requests_used']} "
            f"requests_remaining_estimate={status['requests_remaining_estimate']} "
            f"symbols_deferred={status['symbols_deferred']} "
            f"rate_limit_hits={status['rate_limit_hits']}"
        )
    except Exception:
        pass


def forex_symbols_for_cycle(symbols: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:
    base = list(symbols or FOREX_SYMBOLS)
    if not base:
        return [], []
    per_cycle = _env_int("FOREX_SYMBOLS_PER_CYCLE", 2, 1, len(base))
    slot_seconds = _env_int("FOREX_SYMBOL_ROTATION_SECONDS", 300, 60, 86400)
    slot = int(time.time() // slot_seconds)
    start = (slot * per_cycle) % len(base)
    selected = [base[(start + idx) % len(base)] for idx in range(min(per_cycle, len(base)))]
    selected_set = set(selected)
    deferred = [symbol for symbol in base if symbol not in selected_set]
    _REQUEST_BUDGET["symbols_deferred"] = len(deferred)
    return selected, deferred


def pricing_provider_priority() -> List[str]:
    """Providers that can validate executable pricing.

    Twelve Data and Finnhub can be excellent candle/last-price sources, but they
    often do not provide real bid/ask. They stay out of the production pricing
    lane unless a future integration explicitly adds bid/ask support.
    """
    configured = str(os.environ.get("FOREX_PRICING_PROVIDER") or "").strip().lower()
    base = []
    if configured in {"oanda", "finnhub", "twelvedata"}:
        base.append(configured)
    for provider in ["oanda"]:
        if provider not in base:
            base.append(provider)
    return base


def normalize_forex_symbol(symbol: str) -> str:
    clean = str(symbol or "").upper().replace("/", "").replace("-", "").strip()
    aliases = {"WTIUSD": "USOIL", "BRENTUSD": "UKOIL", "DJI": "US30", "NDX": "NAS100", "SPX": "SPX500"}
    return aliases.get(clean, clean)


def pip_size(symbol: str) -> float:
    normalized = normalize_forex_symbol(symbol)
    if normalized.endswith("JPY"):
        return 0.01
    if normalized in {"XAUUSD", "XAGUSD", "USOIL", "UKOIL"}:
        return 0.01
    if normalized in {"US30", "NAS100", "SPX500"}:
        return 1.0
    return 0.0001


def asset_class_for_symbol(symbol: str) -> str:
    return ASSET_CLASS.get(normalize_forex_symbol(symbol), "forex")


def provider_symbol(symbol: str, provider: Optional[str] = None) -> str:
    provider = (provider or selected_provider()).strip().lower()
    normalized = normalize_forex_symbol(symbol)
    if provider == "twelvedata":
        return TWELVEDATA_SYMBOL_MAP.get(normalized, normalized)
    if provider == "finnhub":
        return FINNHUB_SYMBOL_MAP.get(normalized, normalized)
    if provider == "oanda":
        return oanda.OANDA_SYMBOL_MAP.get(normalized, normalized)
    return normalized


def provider_interval(timeframe: str, provider: Optional[str] = None) -> str:
    provider = (provider or selected_provider()).strip().lower()
    tf = str(timeframe or "").strip()
    if provider == "twelvedata":
        return TWELVEDATA_INTERVAL_MAP.get(tf, tf)
    if provider == "oanda":
        return oanda.OANDA_TIMEFRAME_MAP.get(tf, tf)
    return tf


def _twelvedata_key() -> str:
    return str(os.environ.get("TWELVEDATA_API_KEY") or os.environ.get("FOREX_DATA_API_KEY") or "").strip()


def _finnhub_key() -> str:
    return str(os.environ.get("FINNHUB_API_KEY") or "").strip()


def provider_priority() -> List[str]:
    configured = str(os.environ.get("FOREX_DATA_PROVIDER") or "twelvedata").strip().lower()
    if configured in {"auto", "multi", ""}:
        base = ["twelvedata", "finnhub", "oanda"]
    elif configured == "oanda":
        base = ["oanda", "twelvedata", "finnhub"]
    elif configured == "finnhub":
        base = ["finnhub", "twelvedata", "oanda"]
    else:
        base = ["twelvedata", "finnhub", "oanda"]
    result = []
    for provider in base + ["twelvedata", "finnhub", "oanda"]:
        if provider not in result:
            result.append(provider)
    return result


def provider_configured(provider: str) -> Tuple[bool, str]:
    provider = str(provider or "").lower()
    if provider == "twelvedata":
        return bool(_twelvedata_key()), "OK" if _twelvedata_key() else "TWELVEDATA_API_KEY_MISSING"
    if provider == "finnhub":
        return bool(_finnhub_key()), "OK" if _finnhub_key() else "FINNHUB_API_KEY_MISSING"
    if provider == "oanda":
        status = oanda.configuration_status()
        if status.get("configured"):
            return True, "OK"
        return False, "OANDA_PROVIDER_DISABLED"
    return False, "PROVIDER_NOT_SUPPORTED"


def selected_provider() -> str:
    for provider in provider_priority():
        ok, _reason = provider_configured(provider)
        if ok:
            return provider
    return provider_priority()[0]


def provider_configuration_status() -> dict:
    health = {}
    for provider in ["twelvedata", "finnhub", "oanda"]:
        configured, reason = provider_configured(provider)
        health[provider] = {"configured": configured, "reason": reason, "optional": provider == "oanda"}
    selected = selected_provider()
    selected_configured, selected_reason = provider_configured(selected)
    return {
        "provider": selected,
        "selected_provider": selected,
        "configured": bool(selected_configured),
        "reason": selected_reason,
        "supported": selected in {"twelvedata", "finnhub", "oanda"},
        "priority": provider_priority(),
        "providers": health,
        "primary": "twelvedata",
        "secondary": "oanda_optional",
    }


def provider_health_status() -> dict:
    status = dict(_LAST_STATUS)
    status.update(provider_configuration_status())
    return status


def pricing_provider_health_status() -> dict:
    providers = {}
    for provider in pricing_provider_priority():
        configured, reason = provider_configured(provider)
        providers[provider] = {"configured": configured, "reason": reason}
    healthy = bool(_LAST_PRICING_STATUS.get("ok") and _LAST_PRICING_STATUS.get("last_success_at"))
    return {
        "pricing_provider": _LAST_PRICING_STATUS.get("provider") if healthy else next((p for p in pricing_provider_priority() if provider_configured(p)[0]), None),
        "providers": providers,
        "requires_real_bid_ask": True,
        "healthy": healthy,
        "last_success_at": _LAST_PRICING_STATUS.get("last_success_at"),
        "last_error": _LAST_PRICING_STATUS.get("last_error"),
        "last_symbol": _LAST_PRICING_STATUS.get("last_symbol"),
    }


def _parse_timestamp(value) -> Optional[datetime]:
    if value in (None, ""):
        return None
    text = str(value).replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _timeframe_seconds(timeframe: Optional[str]) -> int:
    return {"5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}.get(str(timeframe or "").lower(), 1800)


def _is_stale(data_timestamp: Optional[str], timeframe: Optional[str] = None) -> bool:
    """Timeframe-aware freshness check for the latest *closed* candle.

    A single 30-minute limit incorrectly marks healthy 1H/4H candles stale.
    Keep the configured floor, while allowing up to roughly two candle periods
    plus a small provider/clock buffer.
    """
    dt = _parse_timestamp(data_timestamp)
    if not dt:
        return True
    configured = _env_int("FOREX_MAX_CANDLE_STALE_SECONDS", 1800, 60, 86400)
    interval_allowance = (_timeframe_seconds(timeframe) * 2) + 300
    max_age = max(configured, interval_allowance)
    return (datetime.now(timezone.utc) - dt).total_seconds() > max_age


def _cache_get(cache, key, max_seconds):
    cached = cache.get(key)
    if not cached:
        return None
    cached_at, result = cached
    if time.time() - cached_at <= max_seconds:
        return result
    cache.pop(key, None)
    return None


def _remember(provider: str, ok: bool, fallback_used: bool, error: str = "") -> None:
    _LAST_STATUS.update({
        "selected_provider": provider,
        "fallback_used": bool(fallback_used),
        "last_error": error or "",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    })
    provider_health = _LAST_STATUS.setdefault("provider_health", {})
    provider_health[provider] = {"ok": bool(ok), "last_error": error or "", "checked_at": _LAST_STATUS["checked_at"]}


def _twelvedata_quote(symbol: str) -> ProviderQuoteResult:
    key = _twelvedata_key()
    if not key:
        return ProviderQuoteResult(False, symbol, "twelvedata", error="TWELVEDATA_API_KEY_MISSING")
    try:
        allowed, reason = _request_allowed("twelvedata")
        if not allowed:
            return ProviderQuoteResult(False, symbol, "twelvedata", error=reason)
        response = requests.get(
            "https://api.twelvedata.com/quote",
            params={"symbol": provider_symbol(symbol, "twelvedata"), "apikey": key},
            timeout=_timeout(),
        )
        status = response.status_code
        _record_request("twelvedata", "RATE_LIMITED" if status == 429 else "")
        data = response.json() if response.content else {}
        if status in {401, 403}:
            return ProviderQuoteResult(False, symbol, "twelvedata", error="AUTH_FAILED", status_code=status)
        if status == 429:
            return ProviderQuoteResult(False, symbol, "twelvedata", error="RATE_LIMITED", status_code=status)
        if status != 200 or str(data.get("status", "")).lower() == "error":
            return ProviderQuoteResult(False, symbol, "twelvedata", error="HTTP_ERROR", status_code=status)
        def num(*keys):
            for key_name in keys:
                value = data.get(key_name)
                if value not in (None, ""):
                    try:
                        return float(value)
                    except Exception:
                        pass
            return None
        bid = num("bid", "bid_price")
        ask = num("ask", "ask_price")
        price = num("close", "price", "last")
        timestamp = str(data.get("datetime") or data.get("timestamp") or "") or None
        if bid is not None and ask is not None and ask > bid:
            return ProviderQuoteResult(True, symbol, "twelvedata", bid=bid, ask=ask, price=price or ((bid + ask) / 2), spread=ask - bid, timestamp=timestamp, spread_available=True, status_code=status)
        if price is not None:
            return ProviderQuoteResult(True, symbol, "twelvedata", price=price, timestamp=timestamp, spread_available=False, error="SPREAD_UNAVAILABLE", status_code=status)
        return ProviderQuoteResult(False, symbol, "twelvedata", error="PRICE_UNAVAILABLE", status_code=status)
    except requests.exceptions.Timeout:
        return ProviderQuoteResult(False, symbol, "twelvedata", error="TIMEOUT")
    except Exception:
        return ProviderQuoteResult(False, symbol, "twelvedata", error="PARSE_ERROR")


def _finnhub_quote(symbol: str) -> ProviderQuoteResult:
    key = _finnhub_key()
    if not key:
        return ProviderQuoteResult(False, symbol, "finnhub", error="FINNHUB_API_KEY_MISSING")
    mapped = provider_symbol(symbol, "finnhub")
    if mapped == symbol:
        return ProviderQuoteResult(False, symbol, "finnhub", error="SYMBOL_NOT_SUPPORTED")
    try:
        response = requests.get("https://finnhub.io/api/v1/quote", params={"symbol": mapped, "token": key}, timeout=_timeout())
        status = response.status_code
        data = response.json() if response.content else {}
        if status in {401, 403}:
            return ProviderQuoteResult(False, symbol, "finnhub", error="AUTH_FAILED", status_code=status)
        if status == 429:
            return ProviderQuoteResult(False, symbol, "finnhub", error="RATE_LIMITED", status_code=status)
        if status != 200:
            return ProviderQuoteResult(False, symbol, "finnhub", error="HTTP_ERROR", status_code=status)
        price = data.get("c")
        if price in (None, "", 0):
            return ProviderQuoteResult(False, symbol, "finnhub", error="PRICE_UNAVAILABLE", status_code=status)
        timestamp = data.get("t")
        ts_text = datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat() if timestamp else None
        return ProviderQuoteResult(True, symbol, "finnhub", price=float(price), timestamp=ts_text, spread_available=False, error="SPREAD_UNAVAILABLE", status_code=status)
    except requests.exceptions.Timeout:
        return ProviderQuoteResult(False, symbol, "finnhub", error="TIMEOUT")
    except Exception:
        return ProviderQuoteResult(False, symbol, "finnhub", error="PARSE_ERROR")


def _oanda_quote(symbol: str) -> ProviderQuoteResult:
    quote = oanda.get_pricing(symbol)
    if not quote.ok:
        return ProviderQuoteResult(False, symbol, "oanda", bid=quote.bid, ask=quote.ask, price=quote.price, timestamp=quote.timestamp, error=quote.error or "OANDA_UNAVAILABLE", status_code=quote.status_code)
    return ProviderQuoteResult(True, symbol, "oanda", bid=quote.bid, ask=quote.ask, price=quote.price, spread=quote.spread, timestamp=quote.timestamp, spread_available=True, status_code=quote.status_code)


def get_quote(symbol: str) -> ProviderQuoteResult:
    symbol = normalize_forex_symbol(symbol)
    if symbol not in FOREX_SYMBOLS:
        return ProviderQuoteResult(False, symbol, selected_provider(), error="SYMBOL_NOT_SUPPORTED")
    errors = {}
    for index, provider in enumerate(provider_priority()):
        configured, reason = provider_configured(provider)
        if not configured:
            errors[provider] = reason
            continue
        cache_key = (provider, symbol)
        cached = _cache_get(_QUOTE_CACHE, cache_key, _quote_cache_seconds())
        result = cached
        if not result:
            if provider == "twelvedata":
                result = _twelvedata_quote(symbol)
            elif provider == "finnhub":
                result = _finnhub_quote(symbol)
            elif provider == "oanda":
                result = _oanda_quote(symbol)
            else:
                result = ProviderQuoteResult(False, symbol, provider, error="PROVIDER_NOT_SUPPORTED")
            _QUOTE_CACHE[cache_key] = (time.time(), result)
        if result.ok:
            result.fallback_used = index > 0
            _remember(provider, True, result.fallback_used)
            return result
        errors[provider] = result.error or "PROVIDER_FAILED"
        _remember(provider, False, index > 0, errors[provider])
    error_text = ";".join(f"{k}:{v}" for k, v in errors.items()) or "NO_PROVIDER_CONFIGURED"
    return ProviderQuoteResult(False, symbol, selected_provider(), error=error_text)


def get_pricing_quote(symbol: str) -> ProviderQuoteResult:
    """Return a quote only from providers with real bid/ask support.

    This is used for production delivery validation. It intentionally does not
    accept price-only Twelve Data/Finnhub quotes as executable spread data.
    """
    symbol = normalize_forex_symbol(symbol)
    if symbol not in FOREX_SYMBOLS:
        return ProviderQuoteResult(False, symbol, "", error="SYMBOL_NOT_SUPPORTED")
    errors = {}
    for index, provider in enumerate(pricing_provider_priority()):
        configured, reason = provider_configured(provider)
        if not configured:
            errors[provider] = reason
            continue
        cache_key = (f"pricing:{provider}", symbol)
        cached = _cache_get(_QUOTE_CACHE, cache_key, _quote_cache_seconds())
        result = cached
        if not result:
            result = _oanda_quote(symbol) if provider == "oanda" else ProviderQuoteResult(False, symbol, provider, error="REAL_BID_ASK_UNAVAILABLE")
            _QUOTE_CACHE[cache_key] = (time.time(), result)
        if result.ok and result.spread_available and result.bid is not None and result.ask is not None and result.spread is not None:
            result.fallback_used = index > 0
            _remember(provider, True, result.fallback_used)
            _LAST_PRICING_STATUS.update({
                "provider": provider,
                "ok": True,
                "last_success_at": datetime.now(timezone.utc).isoformat(),
                "last_error": "",
                "last_symbol": symbol,
            })
            return result
        errors[provider] = result.error or "REAL_BID_ASK_UNAVAILABLE"
        _LAST_PRICING_STATUS.update({
            "provider": provider,
            "ok": False,
            "last_error": errors[provider],
            "last_symbol": symbol,
        })
        _remember(provider, False, index > 0, errors[provider])
    error_text = ";".join(f"{k}:{v}" for k, v in errors.items()) or "REAL_SPREAD_UNAVAILABLE"
    return ProviderQuoteResult(False, symbol, pricing_provider_priority()[0] if pricing_provider_priority() else "", error=error_text)


def _twelvedata_candles(symbol: str, timeframe: str, outputsize: int) -> ProviderCandlesResult:
    key = _twelvedata_key()
    if not key:
        return ProviderCandlesResult(False, symbol, timeframe, "twelvedata", [], error="TWELVEDATA_API_KEY_MISSING")
    params = {
        "symbol": provider_symbol(symbol, "twelvedata"),
        "interval": provider_interval(timeframe, "twelvedata"),
        "outputsize": int(outputsize),
        "apikey": key,
        "format": "JSON",
    }
    try:
        allowed, reason = _request_allowed("twelvedata")
        if not allowed:
            return ProviderCandlesResult(False, symbol, timeframe, "twelvedata", [], error=reason)
        response = requests.get("https://api.twelvedata.com/time_series", params=params, timeout=_timeout())
        status = response.status_code
        _record_request("twelvedata", "RATE_LIMITED" if status == 429 else "")
        data = response.json() if response.content else {}
        if status in {401, 403}:
            return ProviderCandlesResult(False, symbol, timeframe, "twelvedata", [], error="AUTH_FAILED", status_code=status)
        if status == 429:
            return ProviderCandlesResult(False, symbol, timeframe, "twelvedata", [], error="RATE_LIMITED", status_code=status)
        if status != 200 or str(data.get("status", "")).lower() == "error":
            return ProviderCandlesResult(False, symbol, timeframe, "twelvedata", [], error="HTTP_ERROR", status_code=status)
        candles = []
        for row in reversed(data.get("values") or []):
            try:
                candles.append({
                    "time": str(row.get("datetime")),
                    "open": float(row.get("open")),
                    "high": float(row.get("high")),
                    "low": float(row.get("low")),
                    "close": float(row.get("close")),
                    "volume": float(row.get("volume") or 0),
                    "complete": True,
                })
            except Exception:
                continue
        if len(candles) < 60:
            return ProviderCandlesResult(False, symbol, timeframe, "twelvedata", candles, error="EMPTY_CANDLES", status_code=status)
        timestamp = candles[-1].get("time")
        stale = _is_stale(timestamp, timeframe)
        return ProviderCandlesResult(not stale, symbol, timeframe, "twelvedata", candles, error="STALE_DATA" if stale else None, data_timestamp=timestamp, stale=stale, status_code=status)
    except requests.exceptions.Timeout:
        return ProviderCandlesResult(False, symbol, timeframe, "twelvedata", [], error="TIMEOUT")
    except Exception:
        return ProviderCandlesResult(False, symbol, timeframe, "twelvedata", [], error="PARSE_ERROR")


def _oanda_candles(symbol: str, timeframe: str, outputsize: int) -> ProviderCandlesResult:
    result = oanda.get_candles(symbol, timeframe, outputsize)
    return ProviderCandlesResult(result.ok, symbol, timeframe, "oanda", result.candles, error=result.error, data_timestamp=result.data_timestamp, stale=_is_stale(result.data_timestamp, timeframe) if result.data_timestamp else False, status_code=result.status_code)


def get_ohlcv(symbol: str, timeframe: str, outputsize: int = 120) -> ProviderCandlesResult:
    symbol = normalize_forex_symbol(symbol)
    timeframe = str(timeframe or "").strip()
    if symbol not in FOREX_SYMBOLS:
        return ProviderCandlesResult(False, symbol, timeframe, selected_provider(), [], error="SYMBOL_NOT_SUPPORTED")
    if timeframe not in FOREX_TIMEFRAMES:
        return ProviderCandlesResult(False, symbol, timeframe, selected_provider(), [], error="TIMEFRAME_NOT_SUPPORTED")
    errors = {}
    for index, provider in enumerate(provider_priority()):
        configured, reason = provider_configured(provider)
        if not configured:
            errors[provider] = reason
            continue
        if provider == "finnhub":
            errors[provider] = "OHLC_NOT_ENABLED"
            continue
        cache_key = (provider, symbol, timeframe, int(outputsize))
        cached = _cache_get(_CANDLE_CACHE, cache_key, _cache_seconds_for_timeframe(timeframe))
        result = cached
        if not result:
            result = _oanda_candles(symbol, timeframe, outputsize) if provider == "oanda" else _twelvedata_candles(symbol, timeframe, outputsize)
            _CANDLE_CACHE[cache_key] = (time.time(), result)
        if result.ok:
            result.fallback_used = index > 0
            _remember(provider, True, result.fallback_used)
            return result
        errors[provider] = result.error or "PROVIDER_FAILED"
        _remember(provider, False, index > 0, errors[provider])
    error_text = ";".join(f"{k}:{v}" for k, v in errors.items()) or "NO_PROVIDER_CONFIGURED"
    return ProviderCandlesResult(False, symbol, timeframe, selected_provider(), [], error=error_text)


def supported_symbols() -> List[str]:
    selected = selected_provider()
    if selected == "oanda":
        return [s for s in FOREX_SYMBOLS if s in oanda.OANDA_SYMBOL_MAP]
    if selected == "finnhub":
        return []
    verified = [s for s in FOREX_SYMBOLS if s in TWELVEDATA_SYMBOL_MAP and asset_class_for_symbol(s) in {"forex", "metal"}]
    if str(os.environ.get("FOREX_ENABLE_UNVERIFIED_CFD_SYMBOLS", "false")).strip().lower() in {"1", "true", "yes", "on"}:
        verified = [s for s in FOREX_SYMBOLS if s in TWELVEDATA_SYMBOL_MAP]
    return verified


def unsupported_symbols() -> List[str]:
    selected = selected_provider()
    if selected == "oanda":
        return [s for s in FOREX_SYMBOLS if s not in oanda.OANDA_SYMBOL_MAP]
    if selected == "finnhub":
        return list(FOREX_SYMBOLS)
    supported = set(supported_symbols())
    return [s for s in FOREX_SYMBOLS if s not in supported]


def diagnostic_status() -> dict:
    config = provider_configuration_status()
    return {
        "provider_selected": config.get("selected_provider"),
        "provider_health": provider_health_status(),
        "pricing_health": pricing_provider_health_status(),
        "fallback_used": bool(_LAST_STATUS.get("fallback_used")),
        "news_health": {},
        "supported_symbols": supported_symbols(),
        "unsupported_symbols": unsupported_symbols(),
        "priority": provider_priority(),
        "request_budget": request_budget_status(),
    }
