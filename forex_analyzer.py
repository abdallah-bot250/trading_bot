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
    get_pricing_quote,
    get_quote,
    get_twelvedata_reference_price,
    forex_symbols_for_cycle,
    pip_size,
    provider_configuration_status,
    provider_health_status,
    pricing_provider_health_status,
    request_budget_status,
    unsupported_symbols,
)
from trader_app.services.forex_news import news_decision, configuration_status as news_configuration_status


FOREX_ENABLED = os.environ.get("FOREX_SIGNAL_ENGINE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
FOREX_AUTO_TRADE_ENABLED = os.environ.get("FOREX_AUTO_TRADE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
FOREX_MIN_RR = float(os.environ.get("FOREX_MIN_RISK_REWARD", "1.5"))
FOREX_MIN_CONFIDENCE = float(os.environ.get("FOREX_MIN_CONFIDENCE", "72"))
FOREX_MAX_SPREAD_PIPS = float(os.environ.get("FOREX_MAX_SPREAD_PIPS", "2.5"))
FOREX_MAX_SIGNALS_PER_CYCLE = int(os.environ.get("FOREX_MAX_SIGNALS_PER_CYCLE", "2"))
FOREX_NEWS_BLACKOUT_ENABLED = os.environ.get("FOREX_NEWS_BLACKOUT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
FOREX_NEWS_BLACKOUT_ACTIVE = os.environ.get("FOREX_NEWS_BLACKOUT_ACTIVE", "false").strip().lower() in {"1", "true", "yes", "on"}
FOREX_REQUIRE_REAL_SPREAD = os.environ.get("FOREX_REQUIRE_REAL_SPREAD", "true").strip().lower() in {"1", "true", "yes", "on"}
FOREX_PRODUCTION_MODE = os.environ.get("FOREX_PRODUCTION_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
FOREX_SHADOW_MODE = os.environ.get("FOREX_SHADOW_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}
FOREX_REQUIRE_DATA_RECONCILIATION = os.environ.get("FOREX_REQUIRE_DATA_RECONCILIATION", "false").strip().lower() in {"1", "true", "yes", "on"}
FOREX_PRICE_DIVERGENCE_THRESHOLD_PIPS = float(os.environ.get("FOREX_PRICE_DIVERGENCE_THRESHOLD_PIPS", "3.0") or 3.0)

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
        "rejected_news_provider": 0,
        "rejected_real_spread": 0,
        "rejected_data_freshness": 0,
        "rejected_divergence": 0,
        "rejected_quality": 0,
        "passed_candidates": 0,
        "shadow_candidates": 0,
        "final_signals": 0,
        "deliveries": 0,
        "requests_used": 0,
        "requests_remaining_estimate": 0,
        "symbols_deferred": 0,
        "rate_limit_hits": 0,
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
    if str(getattr(result, "error", "") or "").startswith("REQUEST_BUDGET_"):
        code = "RATE_LIMITED"
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
    data["pricing_health"] = pricing_provider_health_status()
    budget = request_budget_status()
    data["requests_used"] = budget.get("requests_used", 0)
    data["requests_remaining_estimate"] = budget.get("requests_remaining_estimate", 0)
    data["symbols_deferred"] = budget.get("symbols_deferred", 0)
    data["rate_limit_hits"] = budget.get("rate_limit_hits", 0)
    data["request_budget"] = budget
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


def _parse_utc(value) -> Optional[datetime]:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _timestamp_fresh(value, max_age_seconds: Optional[int] = None) -> bool:
    dt = _parse_utc(value)
    if not dt:
        return False
    max_age = max_age_seconds or int(os.environ.get("FOREX_MAX_PRICE_STALE_SECONDS", "90") or 90)
    return (datetime.now(timezone.utc) - dt).total_seconds() <= max_age


def _spread_pips(symbol: str) -> Tuple[Optional[float], dict]:
    quote = get_pricing_quote(symbol)
    if not quote.ok:
        return None, {"ok": False, "reason": quote.error or "REAL_SPREAD_UNAVAILABLE", "provider": quote.provider}
    if not _timestamp_fresh(quote.timestamp):
        return None, {"ok": False, "reason": "STALE_PRICE", "provider": quote.provider, "quote_timestamp": quote.timestamp}
    if not getattr(quote, "spread_available", False) or quote.spread in (None, ""):
        return None, {
            "ok": True,
            "reason": "SPREAD_UNAVAILABLE",
            "provider": quote.provider,
            "bid": quote.bid,
            "ask": quote.ask,
            "price": quote.price,
            "quote_timestamp": quote.timestamp,
        }
    pip = pip_size(symbol)
    spread_pips = round(float(quote.spread or 0) / pip, 2) if pip else None
    return spread_pips, {
        "ok": spread_pips is not None,
        "reason": "REAL_BID_ASK",
        "provider": quote.provider,
        "bid": quote.bid,
        "ask": quote.ask,
        "quote_timestamp": quote.timestamp,
    }


def _production_requires_real_spread() -> bool:
    return bool(FOREX_REQUIRE_REAL_SPREAD and FOREX_PRODUCTION_MODE and not FOREX_SHADOW_MODE)


def _unsafe_production_configuration() -> bool:
    return bool(FOREX_PRODUCTION_MODE and not FOREX_REQUIRE_REAL_SPREAD)


def _real_spread_missing_blocks_delivery(spread: Optional[float], quote_meta: dict) -> bool:
    if not _production_requires_real_spread():
        return False
    if spread is None:
        return True
    return not (quote_meta.get("bid") is not None and quote_meta.get("ask") is not None and quote_meta.get("quote_timestamp"))


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


def _news_ok(symbol: str) -> Tuple[bool, str, Optional[dict]]:
    if FOREX_NEWS_BLACKOUT_ENABLED and FOREX_NEWS_BLACKOUT_ACTIVE:
        return False, "MANUAL_HIGH_IMPACT_NEWS_BLACKOUT", None
    decision = news_decision(symbol)
    return bool(decision.ok and not decision.blocked), decision.reason, decision.event


def _data_reconciliation_ok(symbol: str, quote_meta: dict) -> Tuple[bool, str, Optional[float]]:
    provider = str(quote_meta.get("provider") or "").lower()
    bid = quote_meta.get("bid")
    ask = quote_meta.get("ask")
    if provider != "oanda" or bid in (None, "") or ask in (None, ""):
        return True, "not_required_for_provider", None
    reference = get_twelvedata_reference_price(symbol)
    if not reference.ok or reference.price in (None, ""):
        if FOREX_REQUIRE_DATA_RECONCILIATION:
            return False, reference.error or "REFERENCE_PRICE_UNAVAILABLE", None
        return True, reference.error or "REFERENCE_PRICE_OPTIONAL_UNAVAILABLE", None
    mid = (float(bid) + float(ask)) / 2
    diff_pips = abs(mid - float(reference.price)) / pip_size(symbol)
    if diff_pips > FOREX_PRICE_DIVERGENCE_THRESHOLD_PIPS:
        return False, "DATA_PROVIDER_DIVERGENCE", round(diff_pips, 2)
    return True, "DATA_PROVIDER_MATCH", round(diff_pips, 2)


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
    news_ok, news_reason, news_event = _news_ok(symbol)
    if not news_ok:
        _inc("rejected_news")
        if news_reason in {"API_KEY_MISSING", "AUTH_FAILED", "RATE_LIMITED", "TIMEOUT", "PARSE_ERROR", "PROVIDER_NOT_SUPPORTED"}:
            _inc("rejected_news_provider")
        return None
    spread, quote_meta = _spread_pips(symbol)
    spread_display = spread
    spread_status = "Available" if spread is not None else "Unavailable"
    spread_for_calc = spread if spread is not None else 0.0
    if spread is None:
        if quote_meta.get("reason") == "STALE_PRICE":
            _inc("rejected_data_freshness")
            return None
        if _real_spread_missing_blocks_delivery(spread, quote_meta):
            _inc("rejected_real_spread")
            print(f"FOREX_PRODUCTION_REJECTED symbol={symbol} reason=REAL_SPREAD_UNAVAILABLE")
            return None
    if spread_for_calc > FOREX_MAX_SPREAD_PIPS and asset_class_for_symbol(symbol) == "forex":
        _inc("rejected_spread")
        return None
    recon_ok, recon_reason, divergence_pips = _data_reconciliation_ok(symbol, quote_meta)
    if not recon_ok:
        _inc("rejected_divergence")
        print(f"DATA_PROVIDER_DIVERGENCE symbol={symbol} diff_pips={divergence_pips} threshold={FOREX_PRICE_DIVERGENCE_THRESHOLD_PIPS}")
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
    confidence += 3 if spread_display is not None and spread_display <= FOREX_MAX_SPREAD_PIPS else 0
    confidence = min(92, confidence)
    if confidence < FOREX_MIN_CONFIDENCE:
        _inc("rejected_quality")
        return None

    tp2 = entry + (tp1 - entry) * 1.45
    tp3 = entry + (tp1 - entry) * 1.85
    signal_id = f"FX-{symbol}-{tf}-{int(datetime.now(timezone.utc).timestamp())}"
    signal = {
        "pair": symbol,
        "symbol": symbol,
        "type": "FOREX",
        "market_type": "forex",
        "asset_class": asset_class_for_symbol(symbol),
        "provider": quote_meta.get("provider") or provider_health_status().get("provider") or "twelvedata",
        "candle_provider": provider_health_status().get("provider") or "twelvedata",
        "pricing_provider": quote_meta.get("provider") if spread_status == "Available" else None,
        "market_data_provider": "OANDA" if str(quote_meta.get("provider")).lower() == "oanda" else "Twelve Data",
        "news_provider": "Trading Economics",
        "direction": direction,
        "timeframe": tf,
        "entry": round(entry, 5 if pip < 0.01 else 2),
        "tp": round(tp1, 5 if pip < 0.01 else 2),
        "tp1": round(tp1, 5 if pip < 0.01 else 2),
        "tp2": round(tp2, 5 if pip < 0.01 else 2),
        "tp3": round(tp3, 5 if pip < 0.01 else 2),
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
        "spread": spread_display,
        "spread_status": spread_status,
        "real_bid_ask_available": spread_status == "Available",
        "spread_source": quote_meta.get("reason"),
        "bid": quote_meta.get("bid"),
        "ask": quote_meta.get("ask"),
        "quote_timestamp": quote_meta.get("quote_timestamp"),
        "price_timestamp_utc": quote_meta.get("quote_timestamp"),
        "data_reconciliation": recon_reason,
        "data_divergence_pips": divergence_pips,
        "pip_size": pip,
        "data_timestamp": str(entry_frame.iloc[-1].get("time") or ""),
        "data_timestamp_utc": str(entry_frame.iloc[-1].get("time") or ""),
        "trend_4h": h4_trend,
        "trend_1h": h1_trend,
        "setup": "Pullback / Retest",
        "rsi": round(rsi, 2),
        "macd": round(float(macd.iloc[-1]), 6),
        "macd_signal": round(float(macd_signal.iloc[-1]), 6),
        "atr": round(float(atr), 6),
        "support": round(support, 6),
        "resistance": round(resistance, 6),
        "news_status": news_reason,
        "nearest_news_event": news_event,
        "signal_id": signal_id,
        "entry_range": f"{round(entry - spread_for_calc * pip, 5 if pip < 0.01 else 2)} - {round(entry + spread_for_calc * pip, 5 if pip < 0.01 else 2)}",
        "stop_loss_reason": "Stop is placed beyond recent structure and ATR buffer.",
        "cancel_condition": "Cancel if price breaks the opposite structure level, spread widens above limit, or high-impact news enters the block window.",
        "reason": (
            f"{direction} because 4H and 1H trends are {h4_trend}; price returned to the EMA20/EMA50 pullback zone; "
            f"RSI={rsi:.1f} and MACD confirms momentum; session={session}; spread={spread_display if spread_display is not None else 'Unavailable'}; "
            f"news_check={news_reason}; SL is beyond structure/ATR and TP starts at RR={rr}."
        ),
        "analysis_components": {
            "trend_4h": h4_trend,
            "trend_1h": h1_trend,
            "ema20": round(ema20, 6),
            "ema50": round(ema50, 6),
            "rsi14": round(rsi, 2),
            "macd": round(float(macd.iloc[-1]), 6),
            "macd_signal": round(float(macd_signal.iloc[-1]), 6),
            "atr14": round(float(atr), 6),
            "support": round(support, 6),
            "resistance": round(resistance, 6),
            "session": session,
            "news_reason": news_reason,
            "news_event": news_event,
        },
        "target_basis": "real market candles + ATR + support/resistance + fixed minimum risk/reward",
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
    if _unsafe_production_configuration():
        FOREX_SCAN_SUMMARY["disabled"] = True
        FOREX_SCAN_SUMMARY["disabled_reason"] = "UNSAFE_PRODUCTION_CONFIGURATION"
        print("FOREX_DELIVERY_DISABLED reason=UNSAFE_PRODUCTION_CONFIGURATION")
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
    news_config = news_configuration_status()
    FOREX_SCAN_SUMMARY["news_provider"] = news_config.get("provider")
    FOREX_SCAN_SUMMARY["news_provider_configured"] = bool(news_config.get("configured"))
    FOREX_SCAN_SUMMARY["real_spread_required"] = bool(FOREX_REQUIRE_REAL_SPREAD)
    if news_config.get("required") and not news_config.get("configured"):
        FOREX_SCAN_SUMMARY["disabled"] = True
        FOREX_SCAN_SUMMARY["disabled_reason"] = "FOREX_DISABLED_NO_NEWS_PROVIDER"
        print(f"FOREX_DISABLED_NO_NEWS_PROVIDER provider={news_config.get('provider')} configured=false required=true reason={news_config.get('reason')}")
        return []
    print(f"FOREX_NEWS_PROVIDER_STATUS provider={news_config.get('provider')} configured={str(bool(news_config.get('configured'))).lower()} required={str(bool(news_config.get('required'))).lower()}")
    limit = limit or FOREX_MAX_SIGNALS_PER_CYCLE
    signals: List[dict] = []
    scan_symbols, deferred_symbols = forex_symbols_for_cycle(FOREX_SYMBOLS)
    FOREX_SCAN_SUMMARY["symbols_requested"] = len(FOREX_SYMBOLS)
    FOREX_SCAN_SUMMARY["symbols_deferred"] = len(deferred_symbols)
    timeframes_for_cycle = ["4h", "1h", "30m", "15m"]
    for symbol in scan_symbols:
        _inc("symbols_scanned")
        frames = {}
        failed = False
        for tf in timeframes_for_cycle:
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
        for tf in ("15m",):
            candidate = _build_signal(symbol, tf, frames)
            if candidate:
                signals.append(candidate)
                break
    signals = sorted(signals, key=lambda s: (float(s.get("display_confidence") or 0), float(s.get("risk_reward") or 0)), reverse=True)
    final = signals[:limit]
    FOREX_SCAN_SUMMARY["shadow_candidates"] = len(final)
    FOREX_SCAN_SUMMARY["forex_production_mode"] = bool(FOREX_PRODUCTION_MODE)
    FOREX_SCAN_SUMMARY["forex_shadow_mode"] = bool(FOREX_SHADOW_MODE)
    if FOREX_SHADOW_MODE or not FOREX_PRODUCTION_MODE:
        FOREX_SCAN_SUMMARY["final_signals"] = 0
        FOREX_SCAN_SUMMARY["last_shadow_candidate"] = final[0] if final else None
        if final:
            print(f"FOREX_SHADOW_SIGNAL_RECORDED pair={final[0].get('pair')} direction={final[0].get('direction')} rr={final[0].get('risk_reward')}")
        return []
    if FOREX_REQUIRE_REAL_SPREAD:
        allowed = []
        for signal in final:
            if signal.get("real_bid_ask_available") and signal.get("pricing_provider") and signal.get("spread") not in (None, "", "N/A"):
                allowed.append(signal)
            else:
                _inc("rejected_real_spread")
                print(f"FOREX_PRODUCTION_REJECTED symbol={signal.get('symbol')} reason=REAL_SPREAD_UNAVAILABLE")
        final = allowed
    FOREX_SCAN_SUMMARY["final_signals"] = len(final)
    return final


def forex_auto_trade_status() -> str:
    return "FOREX_AUTO_TRADE_DISABLED" if not FOREX_AUTO_TRADE_ENABLED else "FOREX_AUTO_TRADE_DISABLED broker_adapter_not_verified"


def forex_readiness_status() -> dict:
    provider = provider_configuration_status()
    news = news_configuration_status()
    summary = get_forex_scan_summary()
    provider_health = provider_health_status()
    pricing_health = pricing_provider_health_status()
    provider_configured = bool(provider.get("configured"))
    provider_selected = provider.get("selected_provider") or provider.get("provider")
    pricing_provider = pricing_health.get("pricing_provider")
    real_bid_ask_available = bool(pricing_health.get("healthy"))
    candles_fresh = bool(summary.get("symbols_with_data", 0))
    news_healthy = bool(news.get("configured"))
    telegram_healthy = bool(os.environ.get("TELEGRAM_TOKEN") and os.environ.get("BASE_URL"))
    subscription_delivery_healthy = True
    unsafe_production = _unsafe_production_configuration()
    shadow_ready = bool(provider_configured and FOREX_SHADOW_MODE and not FOREX_PRODUCTION_MODE)
    production_ready = bool(
        FOREX_PRODUCTION_MODE
        and not FOREX_SHADOW_MODE
        and provider_configured
        and candles_fresh
        and FOREX_REQUIRE_REAL_SPREAD
        and real_bid_ask_available
        and news_healthy
        and telegram_healthy
        and subscription_delivery_healthy
        and not unsafe_production
        and not FOREX_AUTO_TRADE_ENABLED
    )
    delivery_allowed = bool(production_ready)
    block_reason = ""
    if unsafe_production:
        block_reason = "UNSAFE_PRODUCTION_CONFIGURATION"
    elif not provider_configured:
        block_reason = provider.get("reason") or "CANDLE_PROVIDER_NOT_CONFIGURED"
    elif FOREX_PRODUCTION_MODE and FOREX_SHADOW_MODE:
        block_reason = "SHADOW_MODE_ENABLED"
    elif FOREX_REQUIRE_REAL_SPREAD and not real_bid_ask_available:
        block_reason = "REAL_SPREAD_UNAVAILABLE"
    elif news.get("required") and not news.get("configured"):
        block_reason = news.get("reason") or "NEWS_PROVIDER_NOT_CONFIGURED"
    elif FOREX_PRODUCTION_MODE and not telegram_healthy:
        block_reason = "TELEGRAM_NOT_HEALTHY"
    ready_checks = {
        "primary_provider": "twelvedata",
        "candle_provider_configured": provider_configured,
        "candle_provider_healthy": bool(candles_fresh or provider.get("reason") == "OK"),
        "fresh_candles": candles_fresh,
        "pricing_provider_configured": bool(pricing_provider),
        "pricing_provider_healthy": real_bid_ask_available,
        "real_bid_ask_available": real_bid_ask_available,
        "forex_delivery_allowed": delivery_allowed,
        "oanda_optional": True,
        "oanda_configured": bool((provider.get("providers") or {}).get("oanda", {}).get("configured")),
        "candles_working": bool(summary.get("symbols_with_data", 0)),
        "real_spread_required": bool(FOREX_REQUIRE_REAL_SPREAD),
        "spread_warning": not FOREX_REQUIRE_REAL_SPREAD,
        "news_provider_configured": news_healthy,
        "news_calendar_working": news_healthy,
        "shadow_mode_enabled": bool(FOREX_SHADOW_MODE),
        "forex_production_mode": bool(FOREX_PRODUCTION_MODE),
        "forex_auto_trade_enabled": bool(FOREX_AUTO_TRADE_ENABLED),
        "telegram_healthy": telegram_healthy,
        "subscription_delivery_checks_healthy": subscription_delivery_healthy,
        "unsafe_production_configuration": unsafe_production,
    }
    readiness_level = "PRODUCTION_READY" if production_ready else ("SHADOW_READY" if shadow_ready else "NOT_READY")
    return {
        "ready": bool(production_ready),
        "checks": ready_checks,
        "provider": provider,
        "provider_health": provider_health,
        "pricing_health": pricing_health,
        "news": news,
        "summary": summary,
        "supported_symbols": list(FOREX_SYMBOLS),
        "unsupported_symbols": unsupported_symbols(),
        "primary_provider": "Twelve Data",
        "secondary_provider": "OANDA (optional)",
        "selected_provider": provider_selected,
        "pricing_provider": pricing_provider or "Unavailable",
        "readiness_level": readiness_level,
        "shadow_ready": shadow_ready,
        "production_ready": production_ready,
        "forex_delivery_allowed": delivery_allowed,
        "delivery_block_reason": block_reason,
        "last_candidate": summary.get("last_shadow_candidate"),
        "last_rejected_reason": summary.get("disabled_reason") or next(iter((summary.get("failure_reasons") or {}).keys()), ""),
        "auto_trade_status": forex_auto_trade_status(),
    }
