from datetime import datetime

import numpy as np
import pandas as pd


AI_PERFORMANCE = {
    "signals_analyzed": 0,
    "signals_approved": 0,
    "risk_rejections": 0,
    "last_signal_at": None,
    "last_risk_score": None,
    "last_confidence_score": None,
}


def _safe_float(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value, low=0, high=100):
    return max(low, min(high, int(round(value))))


def _ema(df, period):
    return df["close"].ewm(span=period, adjust=False).mean()


def _atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(period).mean()


def detect_trend_profile(df):
    if df is None or len(df) < 100:
        return {
            "trend": "UNKNOWN",
            "trend_strength": "WEAK",
            "trend_score": 40,
            "ema_alignment": "UNKNOWN",
        }

    ema20 = _ema(df, 20).iloc[-1]
    ema50 = _ema(df, 50).iloc[-1]
    ema100 = _ema(df, 100).iloc[-1]
    close = _safe_float(df["close"].iloc[-1])

    if close <= 0:
        return {
            "trend": "UNKNOWN",
            "trend_strength": "WEAK",
            "trend_score": 35,
            "ema_alignment": "UNKNOWN",
        }

    if ema20 > ema50 > ema100:
        trend = "UP"
        strength = "STRONG_BULL"
        alignment = "BULLISH_STACK"
    elif ema20 < ema50 < ema100:
        trend = "DOWN"
        strength = "STRONG_BEAR"
        alignment = "BEARISH_STACK"
    elif ema20 > ema50:
        trend = "UP"
        strength = "MIXED"
        alignment = "BULLISH_SHORT_TERM"
    elif ema20 < ema50:
        trend = "DOWN"
        strength = "MIXED"
        alignment = "BEARISH_SHORT_TERM"
    else:
        trend = "RANGE"
        strength = "WEAK"
        alignment = "FLAT"

    ema_gap = abs(ema20 - ema50) / close
    score = 50 + min(30, ema_gap * 9000)
    if strength in ["STRONG_BULL", "STRONG_BEAR"]:
        score += 12
    elif strength == "MIXED":
        score -= 5

    return {
        "trend": trend,
        "trend_strength": strength,
        "trend_score": _clamp(score),
        "ema_alignment": alignment,
    }


def _volume_series(df):
    try:
        if df is not None and "quote_volume" in df.columns:
            qv = df["quote_volume"].astype(float)
            if qv.dropna().tail(20).sum() > 0:
                return qv
        return df["volume"].astype(float)
    except Exception:
        return np.array([])


def analyze_volume(df):
    if df is None or len(df) < 25:
        return {"volume_state": "UNKNOWN", "volume_score": 45, "volume_ratio": 0}

    try:
        series = _volume_series(df)
        if len(series) < 10:
            return {"volume_state": "UNKNOWN", "volume_score": 45, "volume_ratio": 0}
        current_volume = _safe_float(series.iloc[-1])
        history = series.iloc[-25:-1] if len(series) >= 25 else series.iloc[:-1]
        history = history[history > 0]
        if current_volume <= 0 or len(history) == 0:
            return {"volume_state": "THIN", "volume_score": 38, "volume_ratio": 0}
        median_ref = _safe_float(history.median())
        mean_ref = _safe_float(history.mean())
        reference = max(median_ref, min(mean_ref, median_ref * 2.5 if median_ref > 0 else mean_ref))
        ratio = current_volume / reference if reference > 0 else 0
    except Exception:
        ratio = 0

    if ratio >= 1.35:
        state = "EXPANSION"
        score = 82
    elif ratio >= 1.05:
        state = "STRONG"
        score = 72
    elif ratio >= 0.55:
        state = "NORMAL"
        score = 58
    else:
        state = "THIN"
        score = 38

    return {
        "volume_state": state,
        "volume_score": _clamp(score),
        "volume_ratio": round(ratio, 3),
    }


def detect_volatility(df):
    if df is None or len(df) < 30:
        return {"volatility_state": "UNKNOWN", "volatility_score": 45, "atr_ratio": 0}

    atr_value = _safe_float(_atr(df).iloc[-1])
    close = _safe_float(df["close"].iloc[-1])
    atr_ratio = atr_value / close if close > 0 else 0

    if atr_ratio < 0.0007:
        state = "TOO_QUIET"
        score = 35
    elif atr_ratio <= 0.018:
        state = "TRADEABLE"
        score = 78
    elif atr_ratio <= 0.04:
        state = "HIGH"
        score = 60
    else:
        state = "EXTREME"
        score = 30

    return {
        "volatility_state": state,
        "volatility_score": _clamp(score),
        "atr_ratio": round(atr_ratio, 5),
    }


def analyze_market_structure(df):
    if df is None or len(df) < 40:
        return {
            "market_structure": "UNKNOWN",
            "structure_score": 42,
            "range_position": 0.5,
        }

    close = _safe_float(df["close"].iloc[-1])
    recent_high = _safe_float(df["high"].tail(30).max())
    recent_low = _safe_float(df["low"].tail(30).min())
    spread = recent_high - recent_low
    position = (close - recent_low) / spread if spread > 0 else 0.5

    highs = df["high"].tail(6).tolist()
    lows = df["low"].tail(6).tolist()
    higher_highs = highs[-1] > highs[-3] > highs[-5]
    higher_lows = lows[-1] > lows[-3] > lows[-5]
    lower_highs = highs[-1] < highs[-3] < highs[-5]
    lower_lows = lows[-1] < lows[-3] < lows[-5]

    if higher_highs and higher_lows:
        structure = "BULLISH_STRUCTURE"
        score = 78
    elif lower_highs and lower_lows:
        structure = "BEARISH_STRUCTURE"
        score = 78
    elif position >= 0.86:
        structure = "NEAR_BREAKOUT_HIGH"
        score = 70
    elif position <= 0.14:
        structure = "NEAR_BREAKOUT_LOW"
        score = 70
    else:
        structure = "MID_RANGE"
        score = 52

    return {
        "market_structure": structure,
        "structure_score": _clamp(score),
        "range_position": round(position, 3),
    }


def analyze_multi_timeframe(current_profile, higher_tf_ok, interval):
    score = 68 if higher_tf_ok else 42

    if interval == "1h":
        score += 8
    elif interval == "15m":
        score += 4

    alignment = "CONFIRMED" if higher_tf_ok else "UNCONFIRMED"
    if current_profile.get("trend_strength") in ["STRONG_BULL", "STRONG_BEAR"] and higher_tf_ok:
        alignment = "STACKED_CONFIRMATION"
        score += 10

    return {
        "multi_timeframe": alignment,
        "multi_timeframe_score": _clamp(score),
    }


def calculate_risk_score(signal_context, volatility_profile, volume_profile, structure_profile):
    entry = _safe_float(signal_context.get("entry"))
    tp = _safe_float(signal_context.get("tp"))
    sl = _safe_float(signal_context.get("sl"))
    direction = signal_context.get("direction")

    risk = 50

    if entry <= 0 or tp <= 0 or sl <= 0:
        return 100

    if direction == "LONG":
        reward_distance = abs(tp - entry) / entry
        risk_distance = abs(entry - sl) / entry
    else:
        reward_distance = abs(entry - tp) / entry
        risk_distance = abs(sl - entry) / entry

    rr = reward_distance / risk_distance if risk_distance > 0 else 0
    if rr >= 2.4:
        risk -= 18
    elif rr >= 1.9:
        risk -= 10
    else:
        risk += 18

    volatility_state = volatility_profile.get("volatility_state")
    if volatility_state == "TRADEABLE":
        risk -= 10
    elif volatility_state == "HIGH":
        risk += 7
    elif volatility_state in ["EXTREME", "TOO_QUIET"]:
        risk += 18

    if volume_profile.get("volume_state") in ["STRONG", "EXPANSION"]:
        risk -= 8
    elif volume_profile.get("volume_state") == "THIN":
        risk += 12

    market_structure = structure_profile.get("market_structure")
    if market_structure == "MID_RANGE":
        risk += 8
    elif market_structure in ["BULLISH_STRUCTURE", "BEARISH_STRUCTURE", "NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        risk -= 6

    return _clamp(risk)


def calculate_engine_confidence(base_confidence, trend_profile, volume_profile, volatility_profile, structure_profile, mtf_profile, risk_score):
    confidence = _safe_float(base_confidence, 50)
    confidence += (trend_profile.get("trend_score", 50) - 50) * 0.18
    confidence += (volume_profile.get("volume_score", 50) - 50) * 0.16
    confidence += (volatility_profile.get("volatility_score", 50) - 50) * 0.14
    confidence += (structure_profile.get("structure_score", 50) - 50) * 0.14
    confidence += (mtf_profile.get("multi_timeframe_score", 50) - 50) * 0.18
    confidence -= max(0, risk_score - 45) * 0.22
    confidence += max(0, 38 - risk_score) * 0.12
    return _clamp(confidence, 1, 99)


def track_engine_performance(signal, approved=True):
    AI_PERFORMANCE["signals_analyzed"] += 1
    if approved:
        AI_PERFORMANCE["signals_approved"] += 1
    else:
        AI_PERFORMANCE["risk_rejections"] += 1

    AI_PERFORMANCE["last_signal_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    AI_PERFORMANCE["last_risk_score"] = signal.get("risk_score")
    AI_PERFORMANCE["last_confidence_score"] = signal.get("engine_confidence")

    analyzed = max(1, AI_PERFORMANCE["signals_analyzed"])
    approval_rate = AI_PERFORMANCE["signals_approved"] / analyzed

    return {
        "signals_analyzed": AI_PERFORMANCE["signals_analyzed"],
        "signals_approved": AI_PERFORMANCE["signals_approved"],
        "approval_rate": round(approval_rate, 3),
        "risk_rejections": AI_PERFORMANCE["risk_rejections"],
        "last_signal_at": AI_PERFORMANCE["last_signal_at"],
    }


def build_ai_engine_report(df, signal_context, higher_tf_ok=False):
    trend_profile = detect_trend_profile(df)
    volume_profile = analyze_volume(df)
    volatility_profile = detect_volatility(df)
    structure_profile = analyze_market_structure(df)
    mtf_profile = analyze_multi_timeframe(
        trend_profile,
        higher_tf_ok,
        signal_context.get("timeframe", "5m"),
    )

    risk_score = calculate_risk_score(
        signal_context,
        volatility_profile,
        volume_profile,
        structure_profile,
    )
    engine_confidence = calculate_engine_confidence(
        signal_context.get("confidence", 50),
        trend_profile,
        volume_profile,
        volatility_profile,
        structure_profile,
        mtf_profile,
        risk_score,
    )

    report = {
        **trend_profile,
        **volume_profile,
        **volatility_profile,
        **structure_profile,
        **mtf_profile,
        "risk_score": risk_score,
        "engine_confidence": engine_confidence,
        "risk_level": "LOW" if risk_score <= 35 else "MEDIUM" if risk_score <= 60 else "HIGH",
        "engine_version": "nexora-ai-engine-v1",
    }

    report["performance"] = track_engine_performance(report, approved=risk_score <= 72)
    return report
