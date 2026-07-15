import math
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd

from trader_app.services.forex_market_data import (
    FOREX_SYMBOLS,
    FOREX_TIMEFRAMES,
    asset_class_for_symbol,
    forex_failure_code,
    get_ohlcv,
    pip_size,
    provider_configuration_status,
    provider_health_status,
)


FOREX_ENABLED = os.environ.get("FOREX_SIGNAL_ENGINE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
FOREX_AUTO_TRADE_ENABLED = os.environ.get("FOREX_AUTO_TRADE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
FOREX_MIN_RR = float(os.environ.get("FOREX_MIN_RISK_REWARD", "1.5"))
FOREX_MIN_CONFIDENCE = float(os.environ.get("FOREX_MIN_CONFIDENCE", "72"))
FOREX_MAX_SPREAD_PIPS = float(os.environ.get("FOREX_MAX_SPREAD_PIPS", "2.5"))
FOREX_MAX_SIGNALS_PER_CYCLE = int(os.environ.get("FOREX_MAX_SIGNALS_PER_CYCLE", "2"))
FOREX_NEWS_BLACKOUT_ENABLED = os.environ.get("FOREX_NEWS_BLACKOUT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
FOREX_NEWS_BLACKOUT_ACTIVE = os.environ.get("FOREX_NEWS_BLACKOUT_ACTIVE", "false").strip().lower() in {"1", "true", "yes", "on"}

FOREX_SCAN_SUMMARY = {}


def _reset_summary():
    FOREX_SCAN_SUMMARY.clear()
    FOREX_SCAN_SUMMARY.update({
        "symbols_requested": len(FOREX_SYMBOLS),
        "symbols_scanned": 0,
        "symbols_with_data": 0,
        "timeframes_scanned": 0,
        "data_failures": 0,
        "requests_failed": 0,
        "failure_reasons": {},
        "disabled": False,
        "disabled_reason": "",
        "rejected_volatility": 0,
        "rejected_spread": 0,
        "rejected_news": 0,
        "rejected_quality": 0,
        "passed_candidates": 0,
        "final_signals": 0,
        "deliveries": 0,
        "provider": provider_health_status().get("provider"),
    })


def _inc(key, amount=1):
    if not FOREX_SCAN_SUMMARY:
        _reset_summary()
    FOREX_SCAN_SUMMARY[key] = int(FOREX_SCAN_SUMMARY.get(key, 0) or 0) + amount


def _record_data_failure(result):
    if not FOREX_SCAN_SUMMARY:
        _reset_summary()
    code = forex_failure_code(getattr(result, "error", None), getattr(result, "status_code", None))
    reasons = FOREX_SCAN_SUMMARY.setdefault("failure_reasons", {})
    reasons[code] = int(reasons.get(code, 0) or 0) + 1
    _inc("data_failures")
    _inc("requests_failed")
    try:
        print(
            "FOREX_DATA_FAILURE "
            f"provider={getattr(result, 'provider', '') or provider_health_status().get('provider')} "
            f"symbol={getattr(result, 'symbol', '')} timeframe={getattr(result, 'timeframe', '')} "
            f"reason={code} status_code={getattr(result, 'status_code', None) or ''}"
        )
    except Exception:
        pass


def get_forex_scan_summary(final_signals: Optional[int] = None) -> dict:
    if not FOREX_SCAN_SUMMARY:
        _reset_summary()
    data = dict(FOREX_SCAN_SUMMARY)
    if final_signals is not None:
        data["final_signals"] = int(final_signals or 0)
    data["provider_health"] = provider_health_status()
    return data


def _df(candles: List[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(candles)
    for col in ("open", "high", "low", "close", "volume"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)


def _ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def _rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(length).mean()
    loss = (-delta.clip(upper=0)).rolling(length).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def _atr(frame, length=14):
    high_low = frame["high"] - frame["low"]
    high_close = (frame["high"] - frame["close"].shift()).abs()
    low_close = (frame["low"] - frame["close"].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return ranges.rolling(length).mean()


def _macd(series):
    fast = _ema(series, 12)
    slow = _ema(series, 26)
    macd = fast - slow
    signal = _ema(macd, 9)
    return macd, signal


def _session(now=None):
    now = now or datetime.now(timezone.utc)
    hour = now.hour
    if 0 <= hour < 7:
        return "Asia"
    if 7 <= hour < 12:
        return "London"
    if 12 <= hour < 16:
        return "London/New_York_Overlap"
    if 16 <= hour < 21:
        return "New_York"
    return "After_Hours"


def _spread_pips(symbol: str, frame: pd.DataFrame) -> float:
    pip = pip_size(symbol)
    last = frame.iloc[-1]
    proxy = max(float(last["high"]) - float(last["low"]), 0.0) * 0.08
    return round(proxy / pip, 2) if pip else 999.0


def _support_resistance(frame: pd.DataFrame) -> Tuple[float, float]:
    recent = frame.tail(40)
    return float(recent["low"].min()), float(recent["high"].max())


def _trend(frame: pd.DataFrame) -> str:
    close = frame["close"]
    e20 = _ema(close, 20).iloc[-1]
    e50 = _ema(close, 50).iloc[-1]
    e200 = _ema(close, 200).iloc[-1] if len(frame) >= 200 else _ema(close, 100).iloc[-1]
    price = close.iloc[-1]
    if price > e20 > e50 > e200:
        return "BULL"
    if price < e20 < e50 < e200:
        return "BEAR"
    return "MIXED"


def _volatility_ok(symbol: str, frame: pd.DataFrame) -> Tuple[bool, str, float]:
    atr = float(_atr(frame).iloc[-1] or 0)
    price = float(frame["close"].iloc[-1] or 0)
    if price <= 0 or atr <= 0:
        return False, "atr_unavailable", atr
    ratio = atr / price
    asset = asset_class_for_symbol(symbol)
    low, high = {
        "forex": (0.00035, 0.008),
        "metal": (0.0008, 0.018),
        "oil": (0.0012, 0.025),
        "index": (0.0007, 0.018),
    }.get(asset, (0.0005, 0.015))
    if ratio < low:
        return False, f"atr_too_low ratio={ratio:.5f}", atr
    if ratio > high:
        return False, f"atr_too_high ratio={ratio:.5f}", atr
    return True, "atr_ok", atr


def _news_ok() -> Tuple[bool, str]:
    if FOREX_NEWS_BLACKOUT_ENABLED and FOREX_NEWS_BLACKOUT_ACTIVE:
        return False, "high_impact_news_blackout_active"
    return True, "no_configured_news_blackout"


def _build_signal(symbol: str, tf: str, frames: Dict[str, pd.DataFrame]) -> Optional[dict]:
    h4_trend = _trend(frames["4h"])
    h1_trend = _trend(frames["1h"])
    if h4_trend != h1_trend or h4_trend not in {"BULL", "BEAR"}:
        return None

    entry_frame = frames[tf] if tf in frames else frames["15m"]
    ok_vol, vol_reason, atr = _volatility_ok(symbol, entry_frame)
    if not ok_vol:
        _inc("rejected_volatility")
        return None
    news_ok, news_reason = _news_ok()
    if not news_ok:
        _inc("rejected_news")
        return None
    spread = _spread_pips(symbol, entry_frame)
    if spread > FOREX_MAX_SPREAD_PIPS and asset_class_for_symbol(symbol) == "forex":
        _inc("rejected_spread")
        return None

    close = entry_frame["close"]
    price = float(close.iloc[-1])
    ema20 = float(_ema(close, 20).iloc[-1])
    ema50 = float(_ema(close, 50).iloc[-1])
    rsi = float(_rsi(close).iloc[-1])
    macd, macd_signal = _macd(close)
    support, resistance = _support_resistance(entry_frame)
    pip = pip_size(symbol)
    session = _session()

    direction = "LONG" if h4_trend == "BULL" else "SHORT"
    if direction == "LONG":
        pullback_ok = price >= ema50 and price <= max(ema20 * 1.002, ema20 + atr * 0.4)
        momentum_ok = rsi >= 48 and macd.iloc[-1] >= macd_signal.iloc[-1]
        entry = price
        sl = min(support, price - atr * 1.15)
        tp1 = price + (price - sl) * 1.5
    else:
        pullback_ok = price <= ema50 and price >= min(ema20 * 0.998, ema20 - atr * 0.4)
        momentum_ok = rsi <= 52 and macd.iloc[-1] <= macd_signal.iloc[-1]
        entry = price
        sl = max(resistance, price + atr * 1.15)
        tp1 = price - (sl - price) * 1.5

    if not pullback_ok:
        _inc("rejected_quality")
        return None
    if not momentum_ok:
        _inc("rejected_quality")
        return None

    risk = abs(entry - sl)
    reward = abs(tp1 - entry)
    rr = round(reward / risk, 2) if risk > 0 else 0
    if rr < FOREX_MIN_RR:
        _inc("rejected_quality")
        return None

    confidence = 72
    confidence += 8 if h4_trend == h1_trend else 0
    confidence += 5 if momentum_ok else 0
    confidence += 4 if session in {"London", "London/New_York_Overlap", "New_York"} else 0
    confidence += 3 if spread <= FOREX_MAX_SPREAD_PIPS else 0
    confidence = min(92, confidence)
    if confidence < FOREX_MIN_CONFIDENCE:
        _inc("rejected_quality")
        return None

    tp2 = entry + (tp1 - entry) * 1.45
    signal = {
        "pair": symbol,
        "symbol": symbol,
        "type": "FOREX",
        "market_type": "forex",
        "asset_class": asset_class_for_symbol(symbol),
        "provider": "twelvedata",
        "direction": direction,
        "timeframe": tf,
        "entry": round(entry, 5 if pip < 0.01 else 2),
        "tp": round(tp1, 5 if pip < 0.01 else 2),
        "tp1": round(tp1, 5 if pip < 0.01 else 2),
        "tp2": round(tp2, 5 if pip < 0.01 else 2),
        "tp3": None,
        "sl": round(sl, 5 if pip < 0.01 else 2),
        "confidence": confidence,
        "display_confidence": confidence,
        "engine_confidence": confidence,
        "final_score": confidence,
        "risk_reward": rr,
        "risk_score": 42,
        "score": 7,
        "quality_tier": "A" if confidence >= 80 else "B_PLUS",
        "opportunity_tier": "A" if confidence >= 80 else "B_PLUS",
        "strategy_name": "Forex Trend Pullback",
        "setup_type": "trend_pullback_continuation",
        "market_regime": "FOREX_TREND",
        "session": session,
        "spread": spread,
        "pip_size": pip,
        "data_timestamp": str(entry_frame.iloc[-1].get("time") or ""),
        "reason": f"{h4_trend} 4H/1H alignment + pullback + momentum confirmation + {news_reason}",
        "target_basis": "ATR + support/resistance",
        "auto_trade_allowed": False,
    }
    _inc("passed_candidates")
    return signal


def get_forex_signals(limit: Optional[int] = None) -> List[dict]:
    _reset_summary()
    if not FOREX_ENABLED:
        FOREX_SCAN_SUMMARY["disabled"] = True
        FOREX_SCAN_SUMMARY["disabled_reason"] = "FOREX_SIGNAL_ENGINE_DISABLED"
        return []
    config = provider_configuration_status()
    FOREX_SCAN_SUMMARY["provider"] = config.get("provider")
    FOREX_SCAN_SUMMARY["provider_configured"] = bool(config.get("configured"))
    if not config.get("configured"):
        FOREX_SCAN_SUMMARY["disabled"] = True
        FOREX_SCAN_SUMMARY["disabled_reason"] = config.get("reason") or "PROVIDER_NOT_CONFIGURED"
        print(f"FOREX_PROVIDER_STATUS provider={config.get('provider')} configured=false reason={FOREX_SCAN_SUMMARY['disabled_reason']}")
        return []
    print(f"FOREX_PROVIDER_STATUS provider={config.get('provider')} configured=true")
    limit = limit or FOREX_MAX_SIGNALS_PER_CYCLE
    signals: List[dict] = []
    for symbol in FOREX_SYMBOLS:
        _inc("symbols_scanned")
        frames = {}
        failed = False
        for tf in FOREX_TIMEFRAMES:
            _inc("timeframes_scanned")
            result = get_ohlcv(symbol, tf)
            if not result.ok:
                _record_data_failure(result)
                failed = True
                break
            frames[tf] = _df(result.candles)
        if failed:
            continue
        _inc("symbols_with_data")
        for tf in ("15m", "5m"):
            candidate = _build_signal(symbol, tf, frames)
            if candidate:
                signals.append(candidate)
                break
    signals = sorted(signals, key=lambda s: (float(s.get("display_confidence") or 0), float(s.get("risk_reward") or 0)), reverse=True)
    final = signals[:limit]
    FOREX_SCAN_SUMMARY["final_signals"] = len(final)
    return final


def forex_auto_trade_status() -> str:
    return "FOREX_AUTO_TRADE_DISABLED" if not FOREX_AUTO_TRADE_ENABLED else "FOREX_AUTO_TRADE_DISABLED broker_adapter_not_verified"
