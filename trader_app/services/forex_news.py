"""Economic-calendar protection for the Forex signal engine.

The service is deliberately fail-closed when real news protection is required.
No synthetic calendar events are generated. Production must provide an approved
calendar provider and credentials before signals are allowed around news.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests

from trader_app.services.forex_providers import tradingeconomics


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.environ.get(name, "true" if default else "false")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0, maximum: int = 1440) -> int:
    try:
        value = int(str(os.environ.get(name, default)).strip())
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


NEWS_PROVIDER = os.environ.get("FOREX_NEWS_PROVIDER", "tradingeconomics").strip().lower()
NEWS_PROVIDERS = os.environ.get("FOREX_NEWS_PROVIDERS", "").strip()
NEWS_API_KEY = os.environ.get("TRADING_ECONOMICS_API_KEY", os.environ.get("FOREX_NEWS_API_KEY", "")).strip()
NEWS_API_SECRET = os.environ.get("TRADING_ECONOMICS_API_SECRET", os.environ.get("FOREX_NEWS_API_SECRET", "")).strip()
NEWS_REQUIRE_REAL = _env_bool("FOREX_REQUIRE_NEWS_CALENDAR", True)
NEWS_LOOKAHEAD_MINUTES = _env_int("FOREX_NEWS_LOOKAHEAD_MINUTES", 45, 5, 360)
NEWS_LOOKBACK_MINUTES = _env_int("FOREX_NEWS_LOOKBACK_MINUTES", 20, 0, 180)
NEWS_CACHE_SECONDS = _env_int("FOREX_NEWS_CACHE_SECONDS", 300, 30, 3600)
NEWS_TIMEOUT_SECONDS = _env_int("FOREX_NEWS_TIMEOUT_SECONDS", 8, 2, 30)
NEWS_MIN_IMPORTANCE = _env_int("FOREX_NEWS_MIN_IMPORTANCE", 2, 1, 3)
NEWS_HIGH_BEFORE_MINUTES = _env_int("FOREX_NEWS_HIGH_BEFORE_MINUTES", 45, 5, 360)
NEWS_HIGH_AFTER_MINUTES = _env_int("FOREX_NEWS_HIGH_AFTER_MINUTES", 30, 5, 360)
NEWS_MEDIUM_BEFORE_MINUTES = _env_int("FOREX_NEWS_MEDIUM_BEFORE_MINUTES", 20, 5, 360)
NEWS_MEDIUM_AFTER_MINUTES = _env_int("FOREX_NEWS_MEDIUM_AFTER_MINUTES", 15, 5, 360)

_CACHE: Dict[str, Tuple[float, List[dict], Optional[str]]] = {}

CURRENCY_COUNTRIES = {
    "USD": {"United States"},
    "EUR": {"Euro Area", "European Union", "Germany", "France", "Italy", "Spain"},
    "GBP": {"United Kingdom"},
    "JPY": {"Japan"},
    "CHF": {"Switzerland"},
    "AUD": {"Australia"},
    "CAD": {"Canada"},
    "NZD": {"New Zealand"},
}


@dataclass
class NewsDecision:
    ok: bool
    blocked: bool
    configured: bool
    provider: str
    reason: str
    event: Optional[dict] = None
    checked_at: Optional[str] = None


def _provider_candidates() -> List[str]:
    raw = NEWS_PROVIDERS or NEWS_PROVIDER or "tradingeconomics"
    values = [p.strip().lower() for p in raw.split(",") if p.strip()]
    for provider in ("tradingeconomics", "finnhub", "financialmodelingprep"):
        if provider not in values:
            values.append(provider)
    return values


def _provider_status(provider: str) -> dict:
    provider = str(provider or "").strip().lower()
    if provider == "tradingeconomics":
        status = tradingeconomics.configuration_status()
        configured = bool(status.get("configured"))
        return {
            "provider": provider,
            "supported": True,
            "configured": configured,
            "reason": "OK" if configured else "NEWS_PROVIDER_NOT_CONFIGURED",
        }
    if provider == "finnhub":
        configured = bool(os.environ.get("FINNHUB_API_KEY") or os.environ.get("FOREX_NEWS_FINNHUB_API_KEY"))
        return {
            "provider": provider,
            "supported": True,
            "configured": configured,
            "reason": "OK" if configured else "NEWS_PROVIDER_NOT_CONFIGURED",
        }
    if provider in {"financialmodelingprep", "fmp"}:
        configured = bool(os.environ.get("FMP_API_KEY") or os.environ.get("FOREX_NEWS_FMP_API_KEY"))
        return {
            "provider": "financialmodelingprep",
            "supported": True,
            "configured": configured,
            "reason": "OK" if configured else "NEWS_PROVIDER_NOT_CONFIGURED",
        }
    return {
        "provider": provider,
        "supported": False,
        "configured": False,
        "reason": "PROVIDER_NOT_SUPPORTED",
    }


def configuration_status() -> dict:
    tried = []
    supported = False
    for provider in _provider_candidates():
        status = _provider_status(provider)
        tried.append(status["provider"])
        supported = supported or bool(status.get("supported"))
        if status.get("supported") and status.get("configured"):
            return {
                "provider": status["provider"],
                "providers_tried": tried,
                "supported": True,
                "configured": True,
                "required": NEWS_REQUIRE_REAL,
                "reason": "OK",
            }
    return {
        "provider": ",".join(tried) or NEWS_PROVIDER,
        "providers_tried": tried,
        "supported": supported,
        "configured": False,
        "required": NEWS_REQUIRE_REAL,
        "reason": "NO_TRUSTED_NEWS_PROVIDER",
    }


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def _importance(row: dict) -> int:
    raw = row.get("Importance", row.get("importance", row.get("importanceValue", 0)))
    try:
        return int(raw or 0)
    except Exception:
        label = str(raw or "").lower()
        if "high" in label:
            return 3
        if "medium" in label:
            return 2
        if "low" in label:
            return 1
        return 0


def _fetch_events() -> Tuple[List[dict], Optional[str]]:
    status = configuration_status()
    if not status["configured"]:
        return [], status["reason"]
    provider = str(status.get("provider") or "").lower()
    if provider == "tradingeconomics":
        result = tradingeconomics.load_events()
        if not result.ok:
            return [], result.error or "PROVIDER_UNAVAILABLE"
        events = []
        for row in result.events:
            events.append({
                "event_id": row.get("event_id"),
                "datetime": row.get("scheduled_utc"),
                "country": row.get("country"),
                "currency": row.get("currency"),
                "event": row.get("title"),
                "category": row.get("category"),
                "importance": row.get("importance"),
                "actual": row.get("actual"),
                "forecast": row.get("forecast"),
                "previous": row.get("previous"),
            })
        return events, None
    now = datetime.now(timezone.utc)
    cache_key = f"{provider}:{now.strftime('%Y-%m-%d')}"
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] <= NEWS_CACHE_SECONDS:
        return list(cached[1]), cached[2]

    start = (now - timedelta(days=1)).date().isoformat()
    end = (now + timedelta(days=1)).date().isoformat()
    if provider == "finnhub":
        url = "https://finnhub.io/api/v1/calendar/economic"
        params = {"token": os.environ.get("FINNHUB_API_KEY") or os.environ.get("FOREX_NEWS_FINNHUB_API_KEY"), "from": start, "to": end}
    elif provider == "financialmodelingprep":
        url = "https://financialmodelingprep.com/api/v3/economic_calendar"
        params = {"apikey": os.environ.get("FMP_API_KEY") or os.environ.get("FOREX_NEWS_FMP_API_KEY"), "from": start, "to": end}
    else:
        return [], "PROVIDER_NOT_SUPPORTED"
    try:
        response = requests.get(url, params=params, timeout=NEWS_TIMEOUT_SECONDS)
        if response.status_code in {401, 403}:
            error = "AUTH_FAILED"
            _CACHE[cache_key] = (time.time(), [], error)
            return [], error
        if response.status_code == 429:
            error = "RATE_LIMITED"
            _CACHE[cache_key] = (time.time(), [], error)
            return [], error
        if response.status_code != 200:
            error = f"HTTP_{response.status_code}"
            _CACHE[cache_key] = (time.time(), [], error)
            return [], error
        payload = response.json()
        if provider == "finnhub":
            rows = payload.get("economicCalendar") if isinstance(payload, dict) else []
        else:
            rows = payload if isinstance(payload, list) else []
        events = []
        for row in rows:
            if not isinstance(row, dict) or _importance(row) < NEWS_MIN_IMPORTANCE:
                continue
            dt = _parse_dt(row.get("Date") or row.get("date") or row.get("datetime") or row.get("time"))
            if not dt:
                continue
            events.append({
                "datetime": dt.isoformat(),
                "country": str(row.get("Country") or row.get("country") or "").strip(),
                "currency": str(row.get("currency") or row.get("Currency") or "").strip().upper(),
                "event": str(row.get("Event") or row.get("event") or row.get("Category") or row.get("title") or "Economic event").strip(),
                "importance": _importance(row),
                "actual": row.get("Actual") or row.get("actual"),
                "forecast": row.get("Forecast") or row.get("forecast"),
                "previous": row.get("Previous") or row.get("previous"),
            })
        _CACHE[cache_key] = (time.time(), events, None)
        return events, None
    except requests.exceptions.Timeout:
        return [], "TIMEOUT"
    except Exception:
        return [], "PARSE_ERROR"


def currencies_for_symbol(symbol: str) -> List[str]:
    clean = str(symbol or "").upper().replace("/", "").replace("-", "")
    if clean in {"XAUUSD", "XAGUSD", "USOIL", "UKOIL", "US30", "NAS100", "SPX500"}:
        return ["USD"]
    if len(clean) >= 6:
        return [clean[:3], clean[3:6]]
    return []


def news_decision(symbol: str, now: Optional[datetime] = None) -> NewsDecision:
    now = now or datetime.now(timezone.utc)
    status = configuration_status()
    checked = now.isoformat()
    if not status["configured"]:
        if NEWS_REQUIRE_REAL:
            return NewsDecision(False, True, False, str(status.get("provider") or NEWS_PROVIDER), status["reason"], checked_at=checked)
        return NewsDecision(True, False, False, str(status.get("provider") or NEWS_PROVIDER), "NEWS_CALENDAR_OPTIONAL_NOT_CONFIGURED", checked_at=checked)

    events, error = _fetch_events()
    if error:
        if NEWS_REQUIRE_REAL:
            return NewsDecision(False, True, True, str(status.get("provider") or NEWS_PROVIDER), error, checked_at=checked)
        return NewsDecision(True, False, True, str(status.get("provider") or NEWS_PROVIDER), f"NEWS_PROVIDER_DEGRADED:{error}", checked_at=checked)

    currencies = currencies_for_symbol(symbol)
    relevant_countries = set()
    for currency in currencies:
        relevant_countries.update(CURRENCY_COUNTRIES.get(currency, set()))
    candidates = []
    for event in events:
        dt = _parse_dt(event.get("datetime"))
        country = str(event.get("country") or "")
        importance = _importance(event)
        if importance >= 3:
            before_minutes = NEWS_HIGH_BEFORE_MINUTES
            after_minutes = NEWS_HIGH_AFTER_MINUTES
        elif importance >= 2:
            before_minutes = NEWS_MEDIUM_BEFORE_MINUTES
            after_minutes = NEWS_MEDIUM_AFTER_MINUTES
        else:
            continue
        window_start = dt - timedelta(minutes=before_minutes)
        window_end = dt + timedelta(minutes=after_minutes)
        if not dt or not (window_start <= now <= window_end):
            continue
        currency = str(event.get("currency") or "").upper()
        if currency:
            relevant = currency in currencies
        else:
            relevant = (not relevant_countries) or country in relevant_countries
        if not relevant:
            continue
        candidates.append((abs((dt - now).total_seconds()), event))
    if candidates:
        event = sorted(candidates, key=lambda item: item[0])[0][1]
        label = "HIGH" if _importance(event) >= 3 else "MEDIUM"
        return NewsDecision(False, True, True, str(status.get("provider") or NEWS_PROVIDER), f"{label}_IMPACT_NEWS_WINDOW", event=event, checked_at=checked)
    return NewsDecision(True, False, True, str(status.get("provider") or NEWS_PROVIDER), "NO_RELEVANT_HIGH_IMPACT_NEWS", checked_at=checked)
