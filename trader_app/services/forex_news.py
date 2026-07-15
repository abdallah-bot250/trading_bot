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
NEWS_API_KEY = os.environ.get("FOREX_NEWS_API_KEY", "").strip()
NEWS_API_SECRET = os.environ.get("FOREX_NEWS_API_SECRET", "").strip()
NEWS_REQUIRE_REAL = _env_bool("FOREX_REQUIRE_NEWS_CALENDAR", True)
NEWS_LOOKAHEAD_MINUTES = _env_int("FOREX_NEWS_LOOKAHEAD_MINUTES", 45, 5, 360)
NEWS_LOOKBACK_MINUTES = _env_int("FOREX_NEWS_LOOKBACK_MINUTES", 20, 0, 180)
NEWS_CACHE_SECONDS = _env_int("FOREX_NEWS_CACHE_SECONDS", 300, 30, 3600)
NEWS_TIMEOUT_SECONDS = _env_int("FOREX_NEWS_TIMEOUT_SECONDS", 8, 2, 30)
NEWS_MIN_IMPORTANCE = _env_int("FOREX_NEWS_MIN_IMPORTANCE", 2, 1, 3)

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


def configuration_status() -> dict:
    supported = NEWS_PROVIDER == "tradingeconomics"
    configured = bool(supported and NEWS_API_KEY and NEWS_API_SECRET)
    return {
        "provider": NEWS_PROVIDER,
        "supported": supported,
        "configured": configured,
        "required": NEWS_REQUIRE_REAL,
        "reason": "OK" if configured else ("PROVIDER_NOT_SUPPORTED" if not supported else "API_KEY_MISSING"),
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
    now = datetime.now(timezone.utc)
    cache_key = now.strftime("%Y-%m-%d")
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] <= NEWS_CACHE_SECONDS:
        return list(cached[1]), cached[2]

    start = (now - timedelta(days=1)).date().isoformat()
    end = (now + timedelta(days=1)).date().isoformat()
    url = "https://api.tradingeconomics.com/calendar"
    params = {"c": f"{NEWS_API_KEY}:{NEWS_API_SECRET}", "d1": start, "d2": end, "importance": NEWS_MIN_IMPORTANCE}
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
        rows = payload if isinstance(payload, list) else []
        events = []
        for row in rows:
            if not isinstance(row, dict) or _importance(row) < NEWS_MIN_IMPORTANCE:
                continue
            dt = _parse_dt(row.get("Date") or row.get("date"))
            if not dt:
                continue
            events.append({
                "datetime": dt.isoformat(),
                "country": str(row.get("Country") or row.get("country") or "").strip(),
                "event": str(row.get("Event") or row.get("event") or row.get("Category") or "Economic event").strip(),
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
            return NewsDecision(False, True, False, NEWS_PROVIDER, status["reason"], checked_at=checked)
        return NewsDecision(True, False, False, NEWS_PROVIDER, "NEWS_CALENDAR_OPTIONAL_NOT_CONFIGURED", checked_at=checked)

    events, error = _fetch_events()
    if error:
        if NEWS_REQUIRE_REAL:
            return NewsDecision(False, True, True, NEWS_PROVIDER, error, checked_at=checked)
        return NewsDecision(True, False, True, NEWS_PROVIDER, f"NEWS_PROVIDER_DEGRADED:{error}", checked_at=checked)

    currencies = currencies_for_symbol(symbol)
    relevant_countries = set()
    for currency in currencies:
        relevant_countries.update(CURRENCY_COUNTRIES.get(currency, set()))
    window_start = now - timedelta(minutes=NEWS_LOOKBACK_MINUTES)
    window_end = now + timedelta(minutes=NEWS_LOOKAHEAD_MINUTES)
    candidates = []
    for event in events:
        dt = _parse_dt(event.get("datetime"))
        country = str(event.get("country") or "")
        if not dt or not (window_start <= dt <= window_end):
            continue
        if relevant_countries and country not in relevant_countries:
            continue
        candidates.append((abs((dt - now).total_seconds()), event))
    if candidates:
        event = sorted(candidates, key=lambda item: item[0])[0][1]
        return NewsDecision(False, True, True, NEWS_PROVIDER, "HIGH_IMPACT_NEWS_WINDOW", event=event, checked_at=checked)
    return NewsDecision(True, False, True, NEWS_PROVIDER, "NO_RELEVANT_HIGH_IMPACT_NEWS", checked_at=checked)
