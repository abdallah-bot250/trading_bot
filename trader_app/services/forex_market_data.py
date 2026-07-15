import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests


FOREX_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "EURJPY", "GBPJPY", "XAUUSD", "XAGUSD", "USOIL", "UKOIL", "US30",
    "NAS100", "SPX500",
]

FOREX_TIMEFRAMES = ["5m", "15m", "1h", "4h"]

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
    "1h": "1h",
    "4h": "4h",
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

_CACHE: Dict[Tuple[str, str, str], Tuple[float, "ForexCandlesResult"]] = {}
_HEALTH = {"provider": None, "ok": False, "last_error": "not_checked", "checked_at": None}

FOREX_FAILURE_CODES = {
    "unsupported_provider": "PROVIDER_NOT_CONFIGURED",
    "unsupported_symbol": "SYMBOL_NOT_SUPPORTED",
    "unsupported_timeframe": "TIMEFRAME_NOT_SUPPORTED",
    "missing_forex_api_key": "API_KEY_MISSING",
    "not_enough_candles": "EMPTY_CANDLES",
    "stale_data": "STALE_DATA",
    "timeout": "TIMEOUT",
}


def _env_int(name: str, default: int, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    try:
        value = int(str(os.environ.get(name, default)).strip())
    except Exception:
        value = int(default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_float(name: str, default: float, minimum: Optional[float] = None) -> float:
    try:
        value = float(str(os.environ.get(name, default)).strip())
    except Exception:
        value = float(default)
    if minimum is not None:
        value = max(minimum, value)
    return value


FOREX_PROVIDER = os.environ.get("FOREX_DATA_PROVIDER", "twelvedata").strip().lower()
FOREX_API_KEY = os.environ.get("FOREX_DATA_API_KEY", "").strip()
FOREX_REQUEST_TIMEOUT = _env_int("FOREX_REQUEST_TIMEOUT_SECONDS", 8, minimum=2, maximum=30)
FOREX_REQUEST_RETRIES = _env_int("FOREX_REQUEST_RETRIES", 2, minimum=0, maximum=5)
FOREX_CACHE_SECONDS = _env_int("FOREX_CACHE_SECONDS", 180, minimum=10, maximum=3600)
FOREX_MAX_CANDLE_STALE_SECONDS = _env_int("FOREX_MAX_CANDLE_STALE_SECONDS", 1800, minimum=60)


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


def normalize_forex_symbol(symbol: str) -> str:
    clean = str(symbol or "").upper().replace("/", "").replace("-", "").strip()
    aliases = {"WTIUSD": "USOIL", "BRENTUSD": "UKOIL", "DJI": "US30", "NDX": "NAS100", "SPX": "SPX500"}
    return aliases.get(clean, clean)


def provider_symbol(symbol: str, provider: Optional[str] = None) -> str:
    provider = (provider or FOREX_PROVIDER).strip().lower()
    normalized = normalize_forex_symbol(symbol)
    if provider == "twelvedata":
        return TWELVEDATA_SYMBOL_MAP.get(normalized, normalized)
    return normalized


def provider_interval(timeframe: str, provider: Optional[str] = None) -> str:
    provider = (provider or FOREX_PROVIDER).strip().lower()
    tf = str(timeframe or "").strip()
    if provider == "twelvedata":
        return TWELVEDATA_INTERVAL_MAP.get(tf, tf)
    return tf


def asset_class_for_symbol(symbol: str) -> str:
    normalized = normalize_forex_symbol(symbol)
    return ASSET_CLASS.get(normalized, "forex")


def pip_size(symbol: str) -> float:
    normalized = normalize_forex_symbol(symbol)
    if normalized.endswith("JPY"):
        return 0.01
    if normalized in {"XAUUSD", "XAGUSD", "USOIL", "UKOIL"}:
        return 0.01
    if normalized in {"US30", "NAS100", "SPX500"}:
        return 1.0
    return 0.0001


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


def _is_stale(data_timestamp: Optional[str]) -> bool:
    dt = _parse_timestamp(data_timestamp)
    if not dt:
        return True
    return (datetime.now(timezone.utc) - dt).total_seconds() > FOREX_MAX_CANDLE_STALE_SECONDS


def _set_health(ok: bool, error: Optional[str] = None):
    _HEALTH.update({
        "provider": FOREX_PROVIDER,
        "ok": bool(ok),
        "last_error": error or "",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    })


def provider_health_status() -> dict:
    return dict(_HEALTH)


def forex_failure_code(error: Optional[str], status_code: Optional[int] = None) -> str:
    text = str(error or "").strip()
    lower = text.lower()
    if status_code == 401 or status_code == 403 or "api key" in lower or "apikey" in lower:
        return "AUTH_FAILED" if "missing" not in lower else "API_KEY_MISSING"
    if status_code == 429 or "rate limit" in lower:
        return "RATE_LIMITED"
    if status_code and int(status_code) >= 400:
        return "HTTP_ERROR"
    if lower.startswith("provider_exception"):
        return "PARSE_ERROR"
    if lower.startswith("http_"):
        return "HTTP_ERROR"
    return FOREX_FAILURE_CODES.get(lower, "PARSE_ERROR" if text else "DATA_SOURCE_FAILURE")


def provider_configuration_status() -> dict:
    provider = FOREX_PROVIDER
    supported = provider == "twelvedata"
    configured = bool(supported and FOREX_API_KEY)
    reason = "OK" if configured else ("PROVIDER_NOT_CONFIGURED" if not supported else "API_KEY_MISSING")
    return {
        "provider": provider,
        "configured": configured,
        "reason": reason,
        "supported": supported,
    }


def _result_from_cache(key):
    cached = _CACHE.get(key)
    if not cached:
        return None
    cached_at, result = cached
    if time.time() - cached_at <= FOREX_CACHE_SECONDS:
        return result
    _CACHE.pop(key, None)
    return None



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
    error: Optional[str] = None
    status_code: Optional[int] = None


def get_quote(symbol: str) -> ForexQuoteResult:
    """Load a live provider quote. Never synthesizes bid/ask values."""
    symbol = normalize_forex_symbol(symbol)
    provider = FOREX_PROVIDER
    if symbol not in FOREX_SYMBOLS:
        return ForexQuoteResult(False, symbol, provider, error="SYMBOL_NOT_SUPPORTED")
    if provider != "twelvedata":
        return ForexQuoteResult(False, symbol, provider, error="PROVIDER_NOT_CONFIGURED")
    if not FOREX_API_KEY:
        return ForexQuoteResult(False, symbol, provider, error="API_KEY_MISSING")
    try:
        response = requests.get(
            "https://api.twelvedata.com/quote",
            params={"symbol": provider_symbol(symbol, provider), "apikey": FOREX_API_KEY},
            timeout=FOREX_REQUEST_TIMEOUT,
        )
        status_code = response.status_code
        data = response.json() if response.content else {}
        if status_code in {401, 403}:
            return ForexQuoteResult(False, symbol, provider, error="AUTH_FAILED", status_code=status_code)
        if status_code == 429:
            return ForexQuoteResult(False, symbol, provider, error="RATE_LIMITED", status_code=status_code)
        if status_code != 200 or str(data.get("status", "")).lower() == "error":
            return ForexQuoteResult(False, symbol, provider, error="HTTP_ERROR", status_code=status_code)
        def number(*keys):
            for key in keys:
                value = data.get(key)
                if value not in (None, ""):
                    try:
                        return float(value)
                    except Exception:
                        continue
            return None
        bid = number("bid", "bid_price")
        ask = number("ask", "ask_price")
        price = number("close", "price", "last")
        timestamp = str(data.get("datetime") or data.get("timestamp") or "") or None
        if bid is None or ask is None or ask <= bid:
            return ForexQuoteResult(False, symbol, provider, price=price, timestamp=timestamp, error="REAL_SPREAD_UNAVAILABLE", status_code=status_code)
        return ForexQuoteResult(True, symbol, provider, bid=bid, ask=ask, price=price or ((bid + ask) / 2), spread=ask-bid, timestamp=timestamp, status_code=status_code)
    except requests.exceptions.Timeout:
        return ForexQuoteResult(False, symbol, provider, error="TIMEOUT")
    except Exception:
        return ForexQuoteResult(False, symbol, provider, error="PARSE_ERROR")


def get_ohlcv(symbol: str, timeframe: str, outputsize: int = 120) -> ForexCandlesResult:
    symbol = normalize_forex_symbol(symbol)
    timeframe = str(timeframe or "").strip()
    provider = FOREX_PROVIDER
    key = (provider, symbol, timeframe)
    cached = _result_from_cache(key)
    if cached:
        return cached

    if symbol not in FOREX_SYMBOLS:
        result = ForexCandlesResult(False, symbol, timeframe, provider, [], "SYMBOL_NOT_SUPPORTED")
        _set_health(False, result.error)
        return result
    if timeframe not in FOREX_TIMEFRAMES:
        result = ForexCandlesResult(False, symbol, timeframe, provider, [], "TIMEFRAME_NOT_SUPPORTED")
        _set_health(False, result.error)
        return result
    if provider != "twelvedata":
        result = ForexCandlesResult(False, symbol, timeframe, provider, [], "PROVIDER_NOT_CONFIGURED")
        _set_health(False, result.error)
        return result
    if not FOREX_API_KEY:
        result = ForexCandlesResult(False, symbol, timeframe, provider, [], "API_KEY_MISSING")
        _set_health(False, result.error)
        return result

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": provider_symbol(symbol, provider),
        "interval": provider_interval(timeframe, provider),
        "outputsize": int(outputsize),
        "apikey": FOREX_API_KEY,
        "format": "JSON",
    }
    last_error = None
    status_code = None
    for attempt in range(FOREX_REQUEST_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=FOREX_REQUEST_TIMEOUT)
            status_code = response.status_code
            if status_code in {429, 500, 502, 503, 504} and attempt < FOREX_REQUEST_RETRIES:
                time.sleep(0.5 * (attempt + 1))
                continue
            data = response.json()
            if status_code != 200:
                last_error = forex_failure_code(f"http_{status_code}", status_code)
                break
            if str(data.get("status", "")).lower() == "error":
                last_error = forex_failure_code(str(data.get("message") or data.get("code") or "provider_error")[:120], status_code)
                break
            rows = data.get("values") or []
            candles = []
            for row in reversed(rows):
                try:
                    candles.append({
                        "time": str(row.get("datetime")),
                        "open": float(row.get("open")),
                        "high": float(row.get("high")),
                        "low": float(row.get("low")),
                        "close": float(row.get("close")),
                        "volume": float(row.get("volume") or 0),
                    })
                except Exception:
                    continue
            if len(candles) < 60:
                last_error = "EMPTY_CANDLES"
                break
            data_timestamp = candles[-1].get("time")
            stale = _is_stale(data_timestamp)
            result = ForexCandlesResult(
                ok=not stale,
                symbol=symbol,
                timeframe=timeframe,
                provider=provider,
                candles=candles,
                error="STALE_DATA" if stale else None,
                data_timestamp=data_timestamp,
                stale=stale,
                status_code=status_code,
            )
            _CACHE[key] = (time.time(), result)
            _set_health(result.ok, result.error)
            return result
        except requests.exceptions.Timeout:
            last_error = "TIMEOUT"
        except Exception as exc:
            last_error = "PARSE_ERROR"
        if attempt < FOREX_REQUEST_RETRIES:
            time.sleep(0.5 * (attempt + 1))

    result = ForexCandlesResult(False, symbol, timeframe, provider, [], last_error or "provider_failed", status_code=status_code)
    _set_health(False, result.error)
    return result
