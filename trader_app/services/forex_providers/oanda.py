"""OANDA v20 market-data adapter for Nexora Forex signals.

This module never logs credentials and never fabricates bid/ask prices. If real
OANDA data is unavailable, callers get a failed result and the Forex engine can
fail closed.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests


OANDA_SYMBOL_MAP = {
    "EURUSD": "EUR_USD",
    "GBPUSD": "GBP_USD",
    "USDJPY": "USD_JPY",
    "USDCHF": "USD_CHF",
    "AUDUSD": "AUD_USD",
    "USDCAD": "USD_CAD",
    "NZDUSD": "NZD_USD",
    "EURJPY": "EUR_JPY",
    "GBPJPY": "GBP_JPY",
    "XAUUSD": "XAU_USD",
    "XAGUSD": "XAG_USD",
}

OANDA_TIMEFRAME_MAP = {
    "5m": "M5",
    "15m": "M15",
    "1h": "H1",
    "4h": "H4",
}


def _env_int(name: str, default: int, minimum: int = 0, maximum: int = 3600) -> int:
    try:
        value = int(str(os.environ.get(name, default)).strip())
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


def _base_url() -> str:
    explicit = str(os.environ.get("OANDA_API_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    env = str(os.environ.get("OANDA_ENVIRONMENT") or "practice").strip().lower()
    return "https://api-fxtrade.oanda.com" if env == "live" else "https://api-fxpractice.oanda.com"


def _token() -> str:
    return str(os.environ.get("OANDA_API_TOKEN") or "").strip()


def _account_id() -> str:
    return str(os.environ.get("OANDA_ACCOUNT_ID") or "").strip()


def configured() -> bool:
    return bool(_token() and _account_id() and _base_url())


def configuration_status() -> dict:
    if not _token():
        reason = "OANDA_API_TOKEN_MISSING"
    elif not _account_id():
        reason = "OANDA_ACCOUNT_ID_MISSING"
    else:
        reason = "OK"
    return {
        "provider": "oanda",
        "configured": reason == "OK",
        "reason": reason,
        "environment": str(os.environ.get("OANDA_ENVIRONMENT") or "practice").strip().lower(),
        "base_url": _base_url(),
    }


@dataclass
class OandaCandles:
    ok: bool
    instrument: str
    timeframe: str
    candles: List[dict]
    data_timestamp: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


@dataclass
class OandaPricing:
    ok: bool
    instrument: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    price: Optional[float] = None
    spread: Optional[float] = None
    timestamp: Optional[str] = None
    tradeable: Optional[bool] = None
    status: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


_INSTRUMENT_CACHE: Tuple[float, Dict[str, dict], Optional[str]] = (0.0, {}, None)
_CANDLE_CACHE: Dict[Tuple[str, str, int], Tuple[float, OandaCandles]] = {}
_PRICE_CACHE: Dict[str, Tuple[float, OandaPricing]] = {}
_FAILURES: List[float] = []
_LAST_HEALTH = {"ok": False, "last_error": "not_checked", "checked_at": None}


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}"}


def _cache_seconds() -> int:
    return _env_int("FOREX_CACHE_SECONDS", 180, 10, 3600)


def _timeout() -> int:
    return _env_int("FOREX_REQUEST_TIMEOUT_SECONDS", 8, 2, 30)


def _retries() -> int:
    return _env_int("FOREX_REQUEST_RETRIES", 2, 0, 5)


def _circuit_open() -> bool:
    window = _env_int("OANDA_CIRCUIT_WINDOW_SECONDS", 120, 10, 900)
    threshold = _env_int("OANDA_CIRCUIT_FAILURES", 5, 1, 50)
    now = time.time()
    while _FAILURES and now - _FAILURES[0] > window:
        _FAILURES.pop(0)
    return len(_FAILURES) >= threshold


def _mark_failure(error: str) -> None:
    _FAILURES.append(time.time())
    _LAST_HEALTH.update({"ok": False, "last_error": error, "checked_at": datetime.now(timezone.utc).isoformat()})


def _mark_success() -> None:
    _LAST_HEALTH.update({"ok": True, "last_error": "", "checked_at": datetime.now(timezone.utc).isoformat()})


def health_status() -> dict:
    data = dict(_LAST_HEALTH)
    data.update(configuration_status())
    data["circuit_open"] = _circuit_open()
    return data


def _request(path: str, params: Optional[dict] = None) -> Tuple[Optional[dict], Optional[str], Optional[int]]:
    if not configured():
        return None, configuration_status()["reason"], None
    if _circuit_open():
        return None, "OANDA_CIRCUIT_OPEN", None
    url = f"{_base_url()}{path}"
    last_error = None
    status_code = None
    for attempt in range(_retries() + 1):
        try:
            response = requests.get(url, headers=_headers(), params=params or {}, timeout=_timeout())
            status_code = response.status_code
            if status_code in {429, 500, 502, 503, 504} and attempt < _retries():
                time.sleep(0.5 * (attempt + 1))
                continue
            if status_code in {401, 403}:
                last_error = "AUTH_FAILED"
                break
            if status_code != 200:
                last_error = f"HTTP_{status_code}"
                break
            payload = response.json() if response.content else {}
            _mark_success()
            return payload, None, status_code
        except requests.exceptions.Timeout:
            last_error = "TIMEOUT"
        except Exception:
            last_error = "PARSE_ERROR"
        if attempt < _retries():
            time.sleep(0.5 * (attempt + 1))
    _mark_failure(last_error or "REQUEST_FAILED")
    return None, last_error or "REQUEST_FAILED", status_code


def account_instruments(force: bool = False) -> Tuple[Dict[str, dict], Optional[str]]:
    global _INSTRUMENT_CACHE
    cached_at, cached, cached_error = _INSTRUMENT_CACHE
    if not force and cached and time.time() - cached_at <= _env_int("OANDA_INSTRUMENT_CACHE_SECONDS", 3600, 60, 86400):
        return dict(cached), cached_error
    account_id = _account_id()
    payload, error, _status = _request(f"/v3/accounts/{account_id}/instruments")
    if error:
        _INSTRUMENT_CACHE = (time.time(), {}, error)
        return {}, error
    rows = payload.get("instruments") if isinstance(payload, dict) else []
    instruments = {}
    for row in rows or []:
        name = str(row.get("name") or "").strip()
        if name:
            instruments[name] = row
    _INSTRUMENT_CACHE = (time.time(), instruments, None)
    return dict(instruments), None


def supported_instrument(symbol: str) -> Tuple[Optional[str], Optional[str]]:
    mapped = OANDA_SYMBOL_MAP.get(str(symbol or "").upper().replace("/", "").replace("-", ""))
    if not mapped:
        return None, "SYMBOL_NOT_SUPPORTED"
    instruments, error = account_instruments()
    if error:
        return None, error
    if mapped not in instruments:
        return None, "SYMBOL_NOT_SUPPORTED"
    return mapped, None


def get_candles(symbol: str, timeframe: str, count: int = 120) -> OandaCandles:
    mapped, error = supported_instrument(symbol)
    granularity = OANDA_TIMEFRAME_MAP.get(str(timeframe or "").strip())
    if error:
        return OandaCandles(False, mapped or str(symbol), timeframe, [], error=error)
    if not granularity:
        return OandaCandles(False, mapped or str(symbol), timeframe, [], error="TIMEFRAME_NOT_SUPPORTED")
    key = (mapped, granularity, int(count))
    cached = _CANDLE_CACHE.get(key)
    if cached and time.time() - cached[0] <= _cache_seconds():
        return cached[1]
    payload, request_error, status_code = _request(
        f"/v3/instruments/{mapped}/candles",
        params={"granularity": granularity, "count": int(count), "price": "M"},
    )
    if request_error:
        return OandaCandles(False, mapped, timeframe, [], error=request_error, status_code=status_code)
    candles = []
    for row in payload.get("candles", []) if isinstance(payload, dict) else []:
        if not row.get("complete"):
            continue
        mid = row.get("mid") or {}
        try:
            candles.append({
                "time": str(row.get("time")),
                "open": float(mid.get("o")),
                "high": float(mid.get("h")),
                "low": float(mid.get("l")),
                "close": float(mid.get("c")),
                "volume": float(row.get("volume") or 0),
                "complete": True,
            })
        except Exception:
            continue
    if len(candles) < 60:
        result = OandaCandles(False, mapped, timeframe, candles, error="EMPTY_CANDLES", status_code=status_code)
    else:
        result = OandaCandles(True, mapped, timeframe, candles, data_timestamp=candles[-1].get("time"), status_code=status_code)
    _CANDLE_CACHE[key] = (time.time(), result)
    return result


def get_pricing(symbol: str) -> OandaPricing:
    mapped, error = supported_instrument(symbol)
    if error:
        return OandaPricing(False, mapped or str(symbol), error=error)
    cached = _PRICE_CACHE.get(mapped)
    if cached and time.time() - cached[0] <= _env_int("OANDA_PRICE_CACHE_SECONDS", 10, 1, 120):
        return cached[1]
    payload, request_error, status_code = _request(
        f"/v3/accounts/{_account_id()}/pricing",
        params={"instruments": mapped},
    )
    if request_error:
        return OandaPricing(False, mapped, error=request_error, status_code=status_code)
    prices = payload.get("prices") if isinstance(payload, dict) else []
    row = prices[0] if prices else {}
    status = str(row.get("status") or "").lower()
    tradeable = bool(row.get("tradeable", False))
    if not tradeable or status not in {"tradeable", ""}:
        result = OandaPricing(False, mapped, tradeable=tradeable, status=status, error="MARKET_NOT_TRADEABLE", status_code=status_code)
        _PRICE_CACHE[mapped] = (time.time(), result)
        return result
    try:
        bid = float(row.get("closeoutBid") or (row.get("bids") or [{}])[0].get("price"))
        ask = float(row.get("closeoutAsk") or (row.get("asks") or [{}])[0].get("price"))
    except Exception:
        result = OandaPricing(False, mapped, tradeable=tradeable, status=status, error="REAL_BID_ASK_MISSING", status_code=status_code)
        _PRICE_CACHE[mapped] = (time.time(), result)
        return result
    if ask <= bid:
        result = OandaPricing(False, mapped, bid=bid, ask=ask, tradeable=tradeable, status=status, error="INVALID_BID_ASK", status_code=status_code)
    else:
        result = OandaPricing(
            True,
            mapped,
            bid=bid,
            ask=ask,
            price=(bid + ask) / 2,
            spread=ask - bid,
            timestamp=str(row.get("time") or ""),
            tradeable=tradeable,
            status=status or "tradeable",
            status_code=status_code,
        )
    _PRICE_CACHE[mapped] = (time.time(), result)
    return result
