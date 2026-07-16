"""Trading Economics calendar adapter for Forex news protection."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests


def _env_int(name: str, default: int, minimum: int = 0, maximum: int = 1440) -> int:
    try:
        value = int(str(os.environ.get(name, default)).strip())
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


def _api_key() -> str:
    return str(os.environ.get("TRADING_ECONOMICS_API_KEY") or os.environ.get("FOREX_NEWS_API_KEY") or "").strip()


def _api_secret() -> str:
    return str(os.environ.get("TRADING_ECONOMICS_API_SECRET") or os.environ.get("FOREX_NEWS_API_SECRET") or "").strip()


def configured() -> bool:
    return bool(_api_key() and _api_secret())


def configuration_status() -> dict:
    return {
        "provider": "tradingeconomics",
        "configured": configured(),
        "supported": True,
        "reason": "OK" if configured() else "API_KEY_MISSING",
        "required": str(os.environ.get("FOREX_REQUIRE_NEWS_CALENDAR", "true")).strip().lower() in {"1", "true", "yes", "on"},
    }


@dataclass
class CalendarResult:
    ok: bool
    events: List[dict]
    error: Optional[str] = None
    fetched_at: Optional[str] = None
    status_code: Optional[int] = None


_CACHE: Dict[str, Tuple[float, CalendarResult]] = {}
_HEALTH = {"ok": False, "last_error": "not_checked", "checked_at": None, "events_loaded": 0}


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
    raw = row.get("Importance", row.get("importance", row.get("importanceValue", row.get("ImportanceValue", 0))))
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


def _event_id(row: dict, dt: datetime, title: str) -> str:
    return str(row.get("CalendarId") or row.get("Id") or row.get("id") or f"{dt.isoformat()}:{title}")[:160]


def load_events(now: Optional[datetime] = None) -> CalendarResult:
    now = now or datetime.now(timezone.utc)
    if not configured():
        result = CalendarResult(False, [], error="API_KEY_MISSING", fetched_at=now.isoformat())
        _HEALTH.update({"ok": False, "last_error": result.error, "checked_at": now.isoformat(), "events_loaded": 0})
        return result
    cache_key = now.strftime("%Y-%m-%d")
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] <= _env_int("FOREX_NEWS_CACHE_SECONDS", 300, 30, 3600):
        return cached[1]
    start = (now - timedelta(days=1)).date().isoformat()
    end = (now + timedelta(days=1)).date().isoformat()
    params = {
        "c": f"{_api_key()}:{_api_secret()}",
        "d1": start,
        "d2": end,
        "importance": 1,
    }
    try:
        response = requests.get("https://api.tradingeconomics.com/calendar", params=params, timeout=_env_int("FOREX_NEWS_TIMEOUT_SECONDS", 8, 2, 30))
        status_code = response.status_code
        if status_code in {401, 403}:
            result = CalendarResult(False, [], error="AUTH_FAILED", fetched_at=now.isoformat(), status_code=status_code)
        elif status_code == 429:
            result = CalendarResult(False, [], error="RATE_LIMITED", fetched_at=now.isoformat(), status_code=status_code)
        elif status_code != 200:
            result = CalendarResult(False, [], error=f"HTTP_{status_code}", fetched_at=now.isoformat(), status_code=status_code)
        else:
            payload = response.json()
            rows = payload if isinstance(payload, list) else []
            events = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                dt = _parse_dt(row.get("Date") or row.get("date"))
                if not dt:
                    continue
                title = str(row.get("Event") or row.get("event") or row.get("Category") or "Economic event").strip()
                events.append({
                    "event_id": _event_id(row, dt, title),
                    "country": str(row.get("Country") or row.get("country") or "").strip(),
                    "currency": str(row.get("Currency") or row.get("currency") or "").strip().upper(),
                    "title": title,
                    "category": str(row.get("Category") or row.get("category") or "").strip(),
                    "importance": _importance(row),
                    "scheduled_utc": dt.isoformat(),
                    "forecast": row.get("Forecast") or row.get("forecast"),
                    "previous": row.get("Previous") or row.get("previous"),
                    "actual": row.get("Actual") or row.get("actual"),
                })
            result = CalendarResult(True, events, fetched_at=now.isoformat(), status_code=status_code)
        _CACHE[cache_key] = (time.time(), result)
        _HEALTH.update({
            "ok": bool(result.ok),
            "last_error": result.error or "",
            "checked_at": now.isoformat(),
            "events_loaded": len(result.events),
        })
        return result
    except requests.exceptions.Timeout:
        result = CalendarResult(False, [], error="TIMEOUT", fetched_at=now.isoformat())
    except Exception:
        result = CalendarResult(False, [], error="PARSE_ERROR", fetched_at=now.isoformat())
    _CACHE[cache_key] = (time.time(), result)
    _HEALTH.update({"ok": False, "last_error": result.error, "checked_at": now.isoformat(), "events_loaded": 0})
    return result


def health_status() -> dict:
    status = dict(_HEALTH)
    status.update(configuration_status())
    return status
