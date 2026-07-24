import time
import requests
import pandas as pd
import numpy as np
import random
import json
import os
from datetime import datetime
from ai_model import predict_trade
from ai_engine import build_ai_engine_report
from spot_futures_engine import choose_trade_type, evaluate_trade_types, record_trade_type
from signal_quality_shared import (
    B_PLUS_CONFIRMED_SETUPS as SHARED_B_PLUS_CONFIRMED_SETUPS,
    B_PLUS_HARD_REJECT_MARKERS as SHARED_B_PLUS_HARD_REJECT_MARKERS,
    b_plus_setup_name as shared_b_plus_setup_name,
    safe_b_plus_eligibility,
)

# ================= SETTINGS =================
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "TRXUSDT", "TONUSDT", "LINKUSDT", "AVAXUSDT", "DOTUSDT",
    "LTCUSDT", "BCHUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT", "ARBUSDT",
    "OPUSDT", "INJUSDT", "RUNEUSDT", "FETUSDT", "HBARUSDT", "XLMUSDT",
    "ICPUSDT", "ETCUSDT", "FILUSDT", "AAVEUSDT", "UNIUSDT", "SUIUSDT"
]

TIMEFRAMES = ["15m", "30m", "1h"]

REQUEST_TIMEOUT = 12
MIN_SCORE_TO_TRADE = 5
MIN_CONFIDENCE = 70
MARKET_SOURCE_LOG_CACHE = {}
MARKET_SOURCE_LOG_TTL_SECONDS = 900
MARKET_CONTEXT_CACHE = {}
MARKET_CONTEXT_TTL_SECONDS = 180
SIGNAL_SKIP_LOG_CACHE = {}
SIGNAL_SKIP_LOG_TTL_SECONDS = 600
SIGNAL_BUILD_COOLDOWN_CACHE = {}
SIGNAL_BUILD_COOLDOWN_SECONDS = int(os.environ.get("SIGNAL_BUILD_COOLDOWN_SECONDS", "3600"))
LAST_DRY_RUN_SKIPS = []
SIGNAL_QUALITY_PROFILE = os.environ.get("SIGNAL_QUALITY_PROFILE", "conservative").strip().lower()
QUALITY_PROFILE_THRESHOLDS = {
    "conservative": {"spot": 88, "futures": 90, "expert": 90, "min_rr": 1.5},
    "balanced": {"spot": 84, "futures": 86, "expert": 86, "min_rr": 1.5},
    "strict": {"spot": 92, "futures": 94, "expert": 94, "min_rr": 1.7},
}
QUALITY_PROFILE = QUALITY_PROFILE_THRESHOLDS.get(SIGNAL_QUALITY_PROFILE, QUALITY_PROFILE_THRESHOLDS["conservative"])
MIN_SPOT_FINAL_SCORE = float(os.environ.get("MIN_SPOT_FINAL_SCORE", QUALITY_PROFILE["spot"]))
MIN_FUTURES_FINAL_SCORE = float(os.environ.get("MIN_FUTURES_FINAL_SCORE", QUALITY_PROFILE["futures"]))
SIGNAL_DEBUG_LOGS = os.environ.get("SIGNAL_DEBUG_LOGS", "").strip().lower() in {"1", "true", "yes", "debug"}
STRICT_VOLATILITY_FILTER = os.environ.get("STRICT_VOLATILITY_FILTER", "false").strip().lower() not in {"0", "false", "no", "off"}
EXPERT_QUALITY_MIN_PERCENT = float(os.environ.get("EXPERT_QUALITY_MIN_PERCENT", QUALITY_PROFILE["expert"]))
NEWS_BLACKOUT_MINUTES = int(os.environ.get("NEWS_BLACKOUT_MINUTES", "30"))
ENTRY_MANAGER_MAX_UPDATE_PERCENT = float(os.environ.get("ENTRY_MANAGER_MAX_UPDATE_PERCENT", "0.12"))
ENTRY_MANAGER_MAX_TP1_PROGRESS_PERCENT = float(os.environ.get("ENTRY_MANAGER_MAX_TP1_PROGRESS_PERCENT", "35"))
ENTRY_MANAGER_MIN_SL_ROOM_PERCENT = float(os.environ.get("ENTRY_MANAGER_MIN_SL_ROOM_PERCENT", "0.12"))
ENTRY_MANAGER_MIN_RR = float(os.environ.get("ENTRY_MANAGER_MIN_RR", "1.5"))
FUTURES_BIAS_TIMEFRAMES = [tf.strip().lower() for tf in os.environ.get("FUTURES_BIAS_TIMEFRAMES", "1h,4h").split(",") if tf.strip()]
FUTURES_SETUP_TIMEFRAME = os.environ.get("FUTURES_SETUP_TIMEFRAME", "30m").strip().lower() or "30m"
FUTURES_TRIGGER_TIMEFRAME = os.environ.get("FUTURES_TRIGGER_TIMEFRAME", "15m").strip().lower() or "15m"
FUTURES_MIN_RR = float(os.environ.get("FUTURES_MIN_RR", "1.5"))
FUTURES_ALLOW_COUNTER_TREND = os.environ.get("FUTURES_ALLOW_COUNTER_TREND", "false").strip().lower() in {"1", "true", "yes", "on"}
FUTURES_REQUIRE_RETEST = os.environ.get("FUTURES_REQUIRE_RETEST", "true").strip().lower() not in {"0", "false", "no", "off"}
FUTURES_REQUIRE_TRIGGER_CLOSE = os.environ.get("FUTURES_REQUIRE_TRIGGER_CLOSE", "true").strip().lower() not in {"0", "false", "no", "off"}
FUTURES_MAX_RECOMMENDED_LEVERAGE = int(os.environ.get("FUTURES_MAX_RECOMMENDED_LEVERAGE", "5"))
FUTURES_REJECT_CHASE_ENTRY = os.environ.get("FUTURES_REJECT_CHASE_ENTRY", "true").strip().lower() not in {"0", "false", "no", "off"}
FUTURES_MAX_ENTRY_ATR_DISTANCE = float(os.environ.get("FUTURES_MAX_ENTRY_ATR_DISTANCE", "0.75"))
FUTURES_MAX_IMPULSE_ATR = float(os.environ.get("FUTURES_MAX_IMPULSE_ATR", "1.85"))
FUTURES_MIN_TP1_ATR_ROOM = float(os.environ.get("FUTURES_MIN_TP1_ATR_ROOM", "0.65"))
FUTURES_SIGNAL_EXPIRY_MINUTES = int(os.environ.get("FUTURES_SIGNAL_EXPIRY_MINUTES", "45"))
def _env_int(name, default, minimum=None, maximum=None):
    try:
        value = int(str(os.environ.get(name, default)).strip())
    except Exception:
        value = int(default)
    if minimum is not None:
        value = max(int(minimum), value)
    if maximum is not None:
        value = min(int(maximum), value)
    return value


MAX_DYNAMIC_SYMBOLS = _env_int("MAX_DYNAMIC_SYMBOLS", 120, minimum=0, maximum=500)
MIN_DYNAMIC_SYMBOLS = _env_int("MIN_DYNAMIC_SYMBOLS", 20, minimum=1, maximum=500)
MIN_DYNAMIC_QUOTE_VOLUME = float(os.environ.get("MIN_DYNAMIC_QUOTE_VOLUME", "5000000"))
DYNAMIC_SYMBOLS_TTL_SECONDS = int(os.environ.get("DYNAMIC_SYMBOLS_TTL_SECONDS", "1800"))
DYNAMIC_SYMBOL_CACHE = {"time": 0, "symbols": None}
SINGLE_SYMBOL_MODE = os.environ.get("SINGLE_SYMBOL_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
SINGLE_SYMBOL = str(os.environ.get("SYMBOL") or os.environ.get("SCAN_SYMBOL") or "").strip().upper()
SYMBOL_FILTER_LOG_CACHE = {}
SYMBOL_FILTER_LOG_TTL_SECONDS = 1800
SIGNAL_SCAN_DIAGNOSTICS = {}
SIGNAL_SCAN_UNIQUE_SYMBOLS = set()
SIGNAL_SUPPLY_24H = {
    "started_at": time.time(),
    "scans": 0,
    "setups_confirmed": 0,
    "candidates": 0,
    "signals": 0,
    "rejections": {},
}
ENTRY_MANAGER_LOG_CACHE = {}
ENTRY_MANAGER_LOG_TTL_SECONDS = 300
ALLOWED_DYNAMIC_BASE_ASSETS = {
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "TON", "LINK",
    "AVAX", "DOT", "LTC", "BCH", "ATOM", "NEAR", "APT", "ARB", "OP", "INJ",
    "RUNE", "FET", "HBAR", "XLM", "ICP", "ETC", "FIL", "AAVE", "UNI", "SUI",
}
KNOWN_PROBLEMATIC_BASE_ASSETS = {
    "REKT", "MOG", "TROLL", "NOBODY", "MEME", "PEPE", "DOGS", "SHIB", "BONK",
    "S", "G",
}


def reset_signal_scan_diagnostics():
    SIGNAL_SCAN_DIAGNOSTICS.clear()
    SIGNAL_SCAN_UNIQUE_SYMBOLS.clear()
    SIGNAL_SCAN_DIAGNOSTICS.update({
        "scanned": 0,
        "scan_attempts": 0,
        "unique_symbols_scanned": 0,
        "playbooks_selected": 0,
        "setups_confirmed": 0,
        "entry_confirmations_passed": 0,
        "candidates_built": 0,
        "finalized_candidates": 0,
        "rejections_by_code": {},
        "mtf_hard_conflict": 0,
        "mtf_soft_conflict": 0,
        "entry_missing": 0,
        "entry_stale": 0,
        "liquidity_invalid": 0,
        "quality_score": 0,
        "late_entry": 0,
        "risk_reward": 0,
        "rejected_low_volatility": 0,
        "rejected_mtf": 0,
        "rejected_liquidity": 0,
        "rejected_fake_breakout": 0,
        "rejected_quality": 0,
        "rejected_entry": 0,
        "watchlist": 0,
        "qualified_b_plus": 0,
        "qualified_a": 0,
        "qualified_a_plus": 0,
        "rejected_opportunity": 0,
        "final_signals": 0,
    })


def _scan_diag_inc(key, amount=1):
    try:
        if not SIGNAL_SCAN_DIAGNOSTICS:
            reset_signal_scan_diagnostics()
        SIGNAL_SCAN_DIAGNOSTICS[key] = int(SIGNAL_SCAN_DIAGNOSTICS.get(key, 0) or 0) + amount
        if key in {"scan_attempts", "scanned"}:
            SIGNAL_SUPPLY_24H["scans"] = int(SIGNAL_SUPPLY_24H.get("scans", 0) or 0) + amount
        elif key == "setups_confirmed":
            SIGNAL_SUPPLY_24H["setups_confirmed"] = int(SIGNAL_SUPPLY_24H.get("setups_confirmed", 0) or 0) + amount
        elif key == "candidates_built":
            SIGNAL_SUPPLY_24H["candidates"] = int(SIGNAL_SUPPLY_24H.get("candidates", 0) or 0) + amount
    except Exception:
        pass


def _scan_diag_attempt(symbol=None):
    try:
        _scan_diag_inc("scan_attempts")
        _scan_diag_inc("scanned")
        if symbol:
            SIGNAL_SCAN_UNIQUE_SYMBOLS.add(str(symbol or "").upper())
            SIGNAL_SCAN_DIAGNOSTICS["unique_symbols_scanned"] = len(SIGNAL_SCAN_UNIQUE_SYMBOLS)
    except Exception:
        pass


def get_signal_scan_diagnostics(final_signals=None):
    if not SIGNAL_SCAN_DIAGNOSTICS:
        reset_signal_scan_diagnostics()
    data = dict(SIGNAL_SCAN_DIAGNOSTICS)
    data["unique_symbols_scanned"] = len(SIGNAL_SCAN_UNIQUE_SYMBOLS)
    if final_signals is not None:
        data["final_signals"] = int(final_signals or 0)
        try:
            SIGNAL_SUPPLY_24H["signals"] = int(final_signals or 0)
        except Exception:
            pass
    _maybe_log_supply_safety_guard()
    return data


REJECTION_REASON_CODES = {
    "HIGH_VOLATILITY": ("HIGH_VOLATILITY", "ATR TOO HIGH", "VOLATILITY HIGH"),
    "LOW_VOLATILITY": ("LOW_VOLATILITY", "ATR TOO LOW", "LOW VOLATILITY"),
    "FAKE_BREAKOUT": ("FAKE_BREAKOUT", "FAKE BREAKOUT"),
    "INVALID_ENTRY": ("INVALID_ENTRY", "INVALID ENTRY", "FRESHNESS", "NO RETEST", "MID_RANGE", "MID-RANGE", "ENTRY LOCATION"),
    "LOW_LIQUIDITY": ("LOW_LIQUIDITY", "LOW_VOLUME_CHOP", "LOW LIQUIDITY"),
    "MTF_CONFLICT": ("MTF_CONFLICT", "MULTI-TIMEFRAME", "4H/1H", "4H AND 1H", "MTF"),
    "LOW_RR": ("LOW_RR", "RR", "RISK/REWARD", "RISK REWARD"),
    "LOW_FINAL_SCORE": ("LOW_FINAL_SCORE", "FINAL SCORE", "SCORE BELOW", "CONFIDENCE"),
    "AI_REJECTED": ("AI_REJECTED", "AI MODEL REJECTED", "AI REJECTION"),
    "DUPLICATE": ("DUPLICATE",),
    "COOLDOWN": ("COOLDOWN",),
    "STALE_DATA": ("STALE", "EXPIRED"),
    "DATA_SOURCE_FAILURE": ("DATA_SOURCE", "DATA FAILURE", "NO LIVE PRICE", "UNAVAILABLE"),
}


def classify_scan_rejection_reason(reason):
    text = str(reason or "").upper()
    for code, markers in REJECTION_REASON_CODES.items():
        if any(marker in text for marker in markers):
            return code
    return "OTHER"


def _record_scan_rejection(reason):
    if not SIGNAL_SCAN_DIAGNOSTICS:
        reset_signal_scan_diagnostics()
    code = classify_scan_rejection_reason(reason)
    by_code = SIGNAL_SCAN_DIAGNOSTICS.setdefault("rejections_by_code", {})
    by_code[code] = int(by_code.get(code, 0) or 0) + 1
    if code == "LOW_VOLATILITY":
        _scan_diag_inc("rejected_low_volatility")
    elif code == "MTF_CONFLICT":
        _scan_diag_inc("rejected_mtf")
    elif code == "LOW_LIQUIDITY":
        _scan_diag_inc("rejected_liquidity")
    elif code == "FAKE_BREAKOUT":
        _scan_diag_inc("rejected_fake_breakout")
    elif code in {"LOW_FINAL_SCORE", "AI_REJECTED", "HIGH_VOLATILITY"}:
        _scan_diag_inc("rejected_quality")
    elif code in {"INVALID_ENTRY", "LOW_RR", "STALE_DATA", "DATA_SOURCE_FAILURE", "DUPLICATE", "COOLDOWN"}:
        _scan_diag_inc("rejected_entry")
    _record_fine_rejection(reason, code)
    return code


def _record_fine_rejection(reason, code=None):
    try:
        text = str(reason or "").upper()
        key = None
        if "HARD_CONFLICT" in text or "HARD MTF" in text or ("4H BULL" in text and "1H BEAR" in text) or ("4H BEAR" in text and "1H BULL" in text):
            key = "mtf_hard_conflict"
        elif "SOFT_CONFLICT" in text or ("4H BULL" in text and "1H RANGE" in text) or ("4H BEAR" in text and "1H RANGE" in text):
            key = "mtf_soft_conflict"
        elif "NO RETEST" in text or "NO ENTRY" in text or "TRIGGER NOT CONFIRMED" in text or "SETUP_ARMED" in text:
            key = "entry_missing"
        elif "STALE" in text or "EXPIRED" in text:
            key = "entry_stale"
        elif code == "LOW_LIQUIDITY" or "LIQUIDITY" in text or "VOLUME" in text:
            key = "liquidity_invalid"
        elif code in {"LOW_FINAL_SCORE", "AI_REJECTED", "HIGH_VOLATILITY"} or "QUALITY" in text or "CONFIDENCE" in text or "SCORE" in text:
            key = "quality_score"
        elif "LATE" in text or "CHASE" in text or "ENTRY_MOVED" in text or "MOVED" in text:
            key = "late_entry"
        elif code == "LOW_RR" or "RR" in text or "RISK/REWARD" in text:
            key = "risk_reward"
        if key:
            _scan_diag_inc(key)
            rejections = SIGNAL_SUPPLY_24H.setdefault("rejections", {})
            rejections[key] = int(rejections.get(key, 0) or 0) + 1
    except Exception:
        pass


def _maybe_log_supply_safety_guard():
    try:
        now = time.time()
        elapsed = now - float(SIGNAL_SUPPLY_24H.get("started_at", now) or now)
        if elapsed < 86400:
            return
        scans = int(SIGNAL_SUPPLY_24H.get("scans", 0) or 0)
        setups = int(SIGNAL_SUPPLY_24H.get("setups_confirmed", 0) or 0)
        candidates = int(SIGNAL_SUPPLY_24H.get("candidates", 0) or 0)
        signals = int(SIGNAL_SUPPLY_24H.get("signals", 0) or 0)
        rejections = dict(SIGNAL_SUPPLY_24H.get("rejections", {}) or {})
        dominant = sorted(rejections.items(), key=lambda item: item[1], reverse=True)[:4]
        print(
            "SIGNAL_SUPPLY_24H "
            f"scans_24h={scans} setups_confirmed_24h={setups} "
            f"candidates_24h={candidates} signals_24h={signals} "
            f"dominant_rejections={dominant}"
        )
        if scans > 500 and candidates == 0:
            print("SIGNAL_SUPPLY_CRITICAL_OVERFILTERING")
        SIGNAL_SUPPLY_24H.clear()
        SIGNAL_SUPPLY_24H.update({
            "started_at": now,
            "scans": 0,
            "setups_confirmed": 0,
            "candidates": 0,
            "signals": 0,
            "rejections": {},
        })
    except Exception:
        pass


def _large_cap_symbol(symbol):
    base = str(symbol or "").upper()
    if base.endswith("USDT"):
        base = base[:-4]
    return base in ALLOWED_DYNAMIC_BASE_ASSETS


def classify_opportunity_tier(signal):
    try:
        display_conf = _safe_float(signal.get("display_confidence", signal.get("confidence", 0)), 0)
        final_score = _safe_float(signal.get("final_score", display_conf), 0)
        rr = _safe_float(signal.get("risk_reward", 0), 0)
        checklist = _safe_float(signal.get("quality_checklist_score", final_score), final_score)
        soft_mtf = signal.get("b_plus_mtf_path") is True or signal.get("mtf_path") == "soft_alignment" or signal.get("mtf_soft_conflict") is True
        safe_bplus_ok, _ = safe_b_plus_eligibility(signal, allow_borderline_score=True)
        if soft_mtf:
            if display_conf >= 70 and final_score >= 78 and rr >= 1.5:
                return "B_PLUS"
            return "B_PLUS" if safe_bplus_ok else ("WATCHLIST" if display_conf >= 64 and rr >= 1.3 else "REJECTED")
        if display_conf >= 88 and final_score >= 92 and rr >= 1.8 and checklist >= 90:
            return "A_PLUS"
        if display_conf >= 80 and final_score >= 86 and rr >= 1.6:
            return "A"
        if signal.get("b_plus_calibrated") is True and safe_bplus_ok:
            return "B_PLUS"
        if display_conf >= 70 and final_score >= 78 and rr >= 1.5:
            return "B_PLUS"
        if display_conf >= 64 and rr >= 1.3:
            return "WATCHLIST"
        return "REJECTED"
    except Exception:
        return "REJECTED"


def mark_opportunity_tier(signal):
    tier = classify_opportunity_tier(signal)
    signal["quality_tier"] = tier
    signal["opportunity_tier"] = tier
    if tier == "A_PLUS":
        _scan_diag_inc("qualified_a_plus")
    elif tier == "A":
        _scan_diag_inc("qualified_a")
    elif tier == "B_PLUS":
        _scan_diag_inc("qualified_b_plus")
    elif tier == "WATCHLIST":
        _scan_diag_inc("watchlist")
    else:
        _scan_diag_inc("rejected_opportunity")
    return tier


B_PLUS_CONFIRMED_SETUPS = SHARED_B_PLUS_CONFIRMED_SETUPS
B_PLUS_HARD_REJECT_MARKERS = SHARED_B_PLUS_HARD_REJECT_MARKERS


def _b_plus_setup_name(signal):
    return shared_b_plus_setup_name(signal)


def b_plus_calibration_eligible(signal):
    try:
        setup = _b_plus_setup_name(signal)
        confidence = _safe_float(signal.get("display_confidence", signal.get("confidence", 0)), 0)
        rr = _safe_float(signal.get("risk_reward"), 0)
        risk_score = _safe_float(signal.get("risk_score"), 50)
        lifecycle = str(signal.get("setup_lifecycle") or "").upper()
        context = " ".join([
            str(signal.get("market_regime") or ""),
            str(signal.get("liquidity_context") or ""),
            str(signal.get("liquidity_reason") or ""),
            str(signal.get("entry_location_reason") or ""),
            str(signal.get("smart_money_reason") or ""),
            str(signal.get("signal_quality_reason") or ""),
            str(signal.get("final_score_reason") or ""),
            str(signal.get("self_review") or ""),
        ]).upper()

        if lifecycle != "CONFIRMED":
            return False, "setup_not_confirmed"
        if setup not in B_PLUS_CONFIRMED_SETUPS:
            return False, f"setup_not_allowed:{setup or 'unknown'}"
        if not (62 <= confidence <= 74):
            return False, f"confidence_outside_b_plus_band:{confidence}"
        if rr < 1.5:
            return False, f"bad_rr:{rr}"
        if risk_score >= 78:
            return False, f"risk_too_high:{risk_score}"
        if any(marker in context for marker in B_PLUS_HARD_REJECT_MARKERS):
            return False, "hard_reject_marker_present"
        if str(signal.get("structure") or "").upper() == "MID_RANGE":
            return False, "mid_range_structure"
        if not signal.get("entry") or not signal.get("tp") or not signal.get("sl"):
            return False, "missing_trade_levels"
        return True, "confirmed_setup_safe_rr"
    except Exception as e:
        return False, f"calibration_error:{e}"


def apply_b_plus_calibration(signal):
    ok, reason = b_plus_calibration_eligible(signal)
    symbol = signal.get("pair") or signal.get("symbol")
    setup = _b_plus_setup_name(signal)
    confidence = _safe_float(signal.get("display_confidence", signal.get("confidence", 0)), 0)
    rr = _safe_float(signal.get("risk_reward"), 0)
    if not ok:
        if 62 <= confidence <= 69:
            print(f"B_PLUS_CALIBRATION_REJECTED symbol={symbol} reason={reason}")
        return False, reason

    candidate = dict(signal)
    candidate["quality_tier"] = "B_PLUS"
    candidate["opportunity_tier"] = "B_PLUS"
    candidate["b_plus_calibrated"] = True
    safe_ok, safe_reason = safe_b_plus_eligibility(candidate, allow_borderline_score=True)
    if not safe_ok:
        if 62 <= confidence <= 69:
            print(f"B_PLUS_CALIBRATION_REJECTED symbol={symbol} reason={safe_reason}")
        return False, safe_reason

    signal.update({
        "quality_tier": "B_PLUS",
        "opportunity_tier": "B_PLUS",
        "b_plus_calibrated": True,
        "confidence_cap_reason": "b_plus_confirmed_setup_cap",
        "risk_warning": "B+ opportunity: confirmed setup with acceptable RR, but lower confidence. Manage risk carefully.",
    })
    if candidate.get("b_plus_borderline_score_rule"):
        signal["b_plus_borderline_score_rule"] = True
    if _safe_float(signal.get("risk_score"), 50) >= 70:
        signal["auto_trade_allowed"] = False
        signal["auto_trade_block_reason"] = "b_plus_risk_score_too_high"
    print(f"B_PLUS_CALIBRATION_APPLIED symbol={symbol} setup={setup} confidence={confidence} rr={rr}")
    return True, "b_plus_calibration_applied"


SUPPLY_SOFT_CHECKS = {"Volume", "Session"}
SUPPLY_HARD_CHECKS = {"Trend", "Momentum", "Liquidity", "MTF", "Risk", "RR", "Entry", "Structure", "News"}


def adaptive_supply_calibration(signal, checklist):
    """Allow confirmed B+ opportunities when only soft supply checks fail."""
    try:
        symbol = signal.get("pair") or signal.get("symbol")
        failed = checklist.get("failed", []) if isinstance(checklist, dict) else []
        failed_names = {str(item.get("name")) for item in failed if isinstance(item, dict)}
        hard_failed = failed_names.intersection(SUPPLY_HARD_CHECKS)
        soft_failed = failed_names.difference(SUPPLY_SOFT_CHECKS)
        percent = _safe_float(checklist.get("percent"), 0)
        rr = _safe_float(signal.get("risk_reward"), 0)
        risk_score = _safe_float(signal.get("risk_score"), 100)
        display_conf = _safe_float(signal.get("display_confidence", signal.get("confidence")), 0)
        setup = _b_plus_setup_name(signal)

        if "Volatility" in failed_names and signal.get("volatility_filter_relaxed") is True:
            failed_names.discard("Volatility")
            soft_failed.discard("Volatility")

        if hard_failed:
            return False, f"hard_check_failed:{','.join(sorted(hard_failed))}"
        if soft_failed:
            return False, f"non_soft_check_failed:{','.join(sorted(soft_failed))}"
        if percent < 83.0:
            return False, f"checklist_too_low:{percent}"
        if rr < 1.5:
            return False, f"bad_rr:{rr}"
        if risk_score >= 72:
            return False, f"risk_too_high:{risk_score}"
        if display_conf < 62:
            return False, f"display_conf_too_low:{display_conf}"
        if str(signal.get("setup_lifecycle") or "").upper() != "CONFIRMED":
            return False, "setup_not_confirmed"
        if setup not in B_PLUS_CONFIRMED_SETUPS:
            return False, f"setup_not_allowed:{setup or 'unknown'}"

        signal["quality_tier"] = "B_PLUS"
        signal["opportunity_tier"] = "B_PLUS"
        signal["b_plus_calibrated"] = True
        signal["supply_calibrated"] = True
        signal["confidence_cap_reason"] = "adaptive_supply_soft_checks_only"
        signal["risk_warning"] = "B+ opportunity: confirmed setup passed hard safety checks; manage risk carefully."
        print(
            f"SUPPLY_CALIBRATION_APPLIED symbol={symbol} setup={setup} "
            f"display_conf={display_conf} checklist={percent} soft_failed={','.join(sorted(failed_names)) or 'none'} rr={rr}"
        )
        return True, "adaptive_supply_calibration_applied"
    except Exception as e:
        return False, f"supply_calibration_error:{e}"


def evaluate_mtf_alignment(playbook_mtf, direction):
    """Return one canonical MTF classification used by every early/late gate."""
    try:
        mtf = playbook_mtf or {}
        direction = str(direction or "").upper()
        desired = "BULL" if direction == "LONG" else "BEAR" if direction == "SHORT" else "UNKNOWN"
        major = str(mtf.get("major") or "UNKNOWN").upper()
        confirm = str(mtf.get("confirm") or "UNKNOWN").upper()
        frames = mtf.get("frames") or {}
        setup_dir = str((frames.get(FUTURES_SETUP_TIMEFRAME) or {}).get("direction") or "UNKNOWN").upper()
        trigger_dir = str((frames.get(FUTURES_TRIGGER_TIMEFRAME) or {}).get("direction") or "UNKNOWN").upper()

        base = {
            "major": major,
            "confirm": confirm,
            "desired": desired,
            "setup_tf_direction": setup_dir,
            "trigger_tf_direction": trigger_dir,
        }
        if desired == "UNKNOWN" or major == "UNKNOWN" or confirm == "UNKNOWN":
            return {**base, "ok": False, "classification": "INVALID_ALIGNMENT", "reason": "MTF data unavailable"}
        if (major == "BULL" and confirm == "BEAR") or (major == "BEAR" and confirm == "BULL"):
            return {**base, "ok": False, "classification": "HARD_CONFLICT", "reason": f"HARD_CONFLICT 4H={major} 1H={confirm}"}
        if major == desired and confirm == desired:
            return {**base, "ok": True, "classification": "STRICT_ALIGNMENT", "reason": f"strict MTF alignment 4H={major} 1H={confirm}"}
        if major == desired and confirm == "RANGE":
            if setup_dir != desired:
                return {**base, "ok": False, "classification": "SOFT_ALIGNMENT", "reason": f"missing_30m_setup: 30m={setup_dir} expected={desired}"}
            if trigger_dir not in {desired, "RANGE"}:
                return {**base, "ok": False, "classification": "SOFT_ALIGNMENT", "reason": f"missing_15m_trigger: 15m={trigger_dir} expected={desired}/RANGE"}
            return {**base, "ok": True, "classification": "SOFT_ALIGNMENT", "reason": f"soft MTF alignment 4H={major} 1H=RANGE 30m={setup_dir} 15m={trigger_dir}"}
        if major == "RANGE" and confirm == desired:
            if setup_dir != desired or trigger_dir != desired:
                return {**base, "ok": False, "classification": "RANGE_ANCHOR", "reason": f"MTF_RANGE_ANCHOR_NOT_CONFIRMED 30m={setup_dir} 15m={trigger_dir} expected={desired}"}
            return {**base, "ok": True, "classification": "RANGE_ANCHOR", "reason": f"range-anchor B+ alignment 4H=RANGE 1H={confirm} 30m={setup_dir} 15m={trigger_dir}"}
        return {**base, "ok": False, "classification": "INVALID_ALIGNMENT", "reason": f"MTF does not support {direction}: 4H={major} 1H={confirm}"}
    except Exception as e:
        return {"ok": False, "classification": "INVALID_ALIGNMENT", "reason": f"MTF evaluation error: {e}"}


def b_plus_mtf_path_context(playbook_mtf, direction):
    """Separate B+ MTF allowance without weakening strict A/A+ confirmation."""
    result = evaluate_mtf_alignment(playbook_mtf, direction)
    if result.get("classification") not in {"SOFT_ALIGNMENT", "RANGE_ANCHOR"}:
        return {**result, "ok": False}
    if not result.get("ok"):
        return result
    return {
        **result,
        "ok": True,
        "state": "B_PLUS_MTF_CONFIRMED",
        "reason": f"B+ MTF path accepted: {result.get('reason')}",
    }
EXCLUDED_BASE_ASSETS = {
    "USD", "USDC", "BUSD", "FDUSD", "TUSD", "USDP", "DAI", "UST", "USTC",
    "EUR", "TRY", "GBP", "BRL", "AUD", "BIDR", "NGN", "RUB", "UAH",
}
EXCLUDED_BASE_KEYWORDS = {
    "USD", "USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "EUR", "TRY",
    "REKT", "MOG", "TROLL", "NOBODY", "MEME", "PEPE", "DOGS", "SHIB", "BONK",
    "UP", "DOWN", "BULL", "BEAR",
}
EXCLUDED_SYMBOL_PARTS = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")
SHORT_BASE_ALLOWLIST = {"BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "TRX", "TON", "DOT", "LTC", "BCH", "APT", "ARB", "FET", "SUI", "OP"}
SYMBOL_UNIVERSE_FILTER_STATS = {}


def _reset_symbol_universe_stats():
    SYMBOL_UNIVERSE_FILTER_STATS.clear()
    SYMBOL_UNIVERSE_FILTER_STATS.update({
        "total_exchange_symbols": 0,
        "eligible_before_volume_filter": 0,
        "filtered_by_reason": {},
        "liquid_symbols_count": 0,
        "selected_final_count": 0,
        "fallback_reason": "none",
        "missing_ticker_data": 0,
        "invalid_volume": 0,
        "below_min_quote_volume": 0,
        "symbol_match_failed": 0,
        "schema_warnings": [],
        "authoritative_universe_source": "none",
        "authoritative_universe_count": 0,
        "kucoin_symbols_with_ticker": 0,
        "kucoin_symbols_above_volume": 0,
        "symbols_dropped_due_to_cross_exchange_requirement": 0,
        "kucoin_volume_distribution": {},
        "kucoin_top_quote_turnover": [],
        "kucoin_invalid_volume_examples": [],
        "kucoin_below_min_quote_volume_examples": [],
        "kucoin_missing_ticker_data_examples": [],
    })


def _symbol_filter_stat(reason):
    try:
        if not SYMBOL_UNIVERSE_FILTER_STATS:
            _reset_symbol_universe_stats()
        reasons = SYMBOL_UNIVERSE_FILTER_STATS.setdefault("filtered_by_reason", {})
        reasons[reason] = int(reasons.get(reason, 0) or 0) + 1
    except Exception:
        pass


def _safe_market_json(url, timeout=REQUEST_TIMEOUT):
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None, response.status_code
        return response.json(), 200
    except Exception as e:
        return None, str(e)


def _normalize_exchange_symbol(symbol):
    """Normalize exchange symbols for matching while preserving raw symbols for API calls."""
    return str(symbol or "").upper().strip().replace("-", "").replace("_", "").replace("/", "")


def _quote_turnover_from_row(row, provider):
    """Return USDT quote turnover only; never estimate quote volume from base quantity."""
    keys = ("quoteVolume", "quote_volume", "volValue", "turnover", "quoteTurnover", "quoteVolume24h")
    for key in keys:
        if key in row:
            value = _safe_float(row.get(key), 0)
            if value > 0:
                return value, key
    return 0.0, "missing_quote_turnover"


def _record_symbol_universe_schema_warning(label, status, raw_count, sample):
    try:
        sample_keys = sorted(list((sample or {}).keys()))[:20] if isinstance(sample, dict) else []
        warning = {
            "label": label,
            "status": status,
            "raw_count": raw_count,
            "sample_keys": sample_keys,
        }
        SYMBOL_UNIVERSE_FILTER_STATS.setdefault("schema_warnings", []).append(warning)
        print(
            "DYNAMIC_SYMBOLS_SCHEMA_WARNING "
            f"label={label} status={status} raw_count={raw_count} "
            f"sample_keys={json.dumps(sample_keys)}"
        )
    except Exception:
        pass


def _append_symbol_universe_example(key, example, limit=10):
    try:
        items = SYMBOL_UNIVERSE_FILTER_STATS.setdefault(key, [])
        if len(items) < limit:
            items.append(example)
    except Exception:
        pass


def _kucoin_volume_diagnostics(candidates, invalid_examples=None, missing_examples=None):
    """Record KuCoin volume diagnostics without changing universe selection."""
    thresholds = [100_000, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000]
    distribution = {str(level): 0 for level in thresholds}
    sorted_candidates = sorted(candidates or [], key=lambda item: item.get("quote_turnover", 0), reverse=True)
    for item in sorted_candidates:
        quote_turnover = _safe_float(item.get("quote_turnover"), 0)
        for level in thresholds:
            if quote_turnover >= level:
                distribution[str(level)] += 1
    top30 = [
        {
            "symbol": item.get("symbol"),
            "original_symbol": item.get("original_symbol"),
            "volValue": item.get("volValue"),
            "last_price": item.get("last_price"),
            "quote_turnover": item.get("quote_turnover"),
        }
        for item in sorted_candidates[:30]
    ]
    SYMBOL_UNIVERSE_FILTER_STATS["kucoin_volume_distribution"] = distribution
    SYMBOL_UNIVERSE_FILTER_STATS["kucoin_top_quote_turnover"] = top30
    SYMBOL_UNIVERSE_FILTER_STATS["kucoin_invalid_volume_examples"] = list((invalid_examples or [])[:10])
    SYMBOL_UNIVERSE_FILTER_STATS["kucoin_missing_ticker_data_examples"] = list((missing_examples or [])[:10])
    try:
        print(
            "KUCOIN_VOLUME_DISTRIBUTION "
            f"counts={json.dumps(distribution, sort_keys=True)} "
            f"top30={json.dumps(top30, sort_keys=True)} "
            f"invalid_volume_examples={json.dumps(SYMBOL_UNIVERSE_FILTER_STATS.get('kucoin_invalid_volume_examples', []), sort_keys=True)} "
            f"below_min_quote_volume_examples={json.dumps(SYMBOL_UNIVERSE_FILTER_STATS.get('kucoin_below_min_quote_volume_examples', []), sort_keys=True)} "
            f"missing_ticker_data_examples={json.dumps(SYMBOL_UNIVERSE_FILTER_STATS.get('kucoin_missing_ticker_data_examples', []), sort_keys=True)} "
            "quote_currency_filter=USDT quote_turnover_source=volValue no_conversion=true"
        )
    except Exception:
        pass


def _log_symbol_filtered(symbol, reason):
    try:
        now = time.time()
        key = (str(symbol or "").upper(), str(reason or "unknown"))
        last_seen = SYMBOL_FILTER_LOG_CACHE.get(key, 0)
        if now - last_seen >= SYMBOL_FILTER_LOG_TTL_SECONDS:
            SYMBOL_FILTER_LOG_CACHE[key] = now
            if SIGNAL_DEBUG_LOGS:
                print(f"SYMBOL_FILTERED symbol={key[0]} reason={key[1]}")
    except Exception:
        pass


def _symbol_filter_reason(symbol):
    symbol = str(symbol or "").upper().strip()
    if not symbol.endswith("USDT"):
        return "not_usdt_pair"
    if any(part in symbol for part in EXCLUDED_SYMBOL_PARTS):
        return "leveraged_token_suffix"
    base = symbol[:-4]
    if not base:
        return "empty_base"
    if base.startswith("1000"):
        return "starts_with_1000"
    if base in EXCLUDED_BASE_ASSETS:
        return "stable_or_fiat_base"
    if base in KNOWN_PROBLEMATIC_BASE_ASSETS:
        return "known_problematic_base"
    if any(ch in base for ch in ["_", "-", "/"]):
        return "invalid_base_characters"
    for keyword in EXCLUDED_BASE_KEYWORDS:
        if base == keyword or keyword in base:
            return f"excluded_keyword_{keyword}"
    if len(base) <= 1 and base not in SHORT_BASE_ALLOWLIST:
        return "base_too_short"
    return None


def _is_tradeable_usdt_symbol(symbol):
    try:
        reason = _symbol_filter_reason(symbol)
        if reason:
            _symbol_filter_stat(reason)
            _log_symbol_filtered(symbol, reason)
            return False
        return True
    except Exception as e:
        _log_symbol_filtered(symbol, f"filter_error_{type(e).__name__}")
        return False


def _ticker_volume_map(url, label="UNKNOWN_TICKER"):
    if not SYMBOL_UNIVERSE_FILTER_STATS:
        _reset_symbol_universe_stats()
    data, status = _safe_market_json(url)
    volumes = {}
    rows = data if isinstance(data, list) else []
    raw_count = len(rows)
    parsed_count = 0
    if not rows:
        SYMBOL_UNIVERSE_FILTER_STATS["missing_ticker_data"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("missing_ticker_data", 0) or 0) + 1
        return volumes, status, {"raw_count": raw_count, "parsed_count": parsed_count}
    for row in data:
        try:
            raw_symbol = row.get("symbol") if isinstance(row, dict) else ""
            symbol = _normalize_exchange_symbol(raw_symbol)
            if not symbol:
                _symbol_filter_stat("symbol_match_failed")
                SYMBOL_UNIVERSE_FILTER_STATS["symbol_match_failed"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("symbol_match_failed", 0) or 0) + 1
                continue
            if not _is_tradeable_usdt_symbol(symbol):
                continue
            quote_volume, _volume_key = _quote_turnover_from_row(row, label)
            if quote_volume <= 0:
                _symbol_filter_stat("invalid_volume")
                SYMBOL_UNIVERSE_FILTER_STATS["invalid_volume"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("invalid_volume", 0) or 0) + 1
                continue
            parsed_count += 1
            volumes[symbol] = max(volumes.get(symbol, 0), quote_volume)
        except Exception:
            _symbol_filter_stat("invalid_volume")
            continue
    if status == 200 and raw_count > 0 and parsed_count == 0:
        _record_symbol_universe_schema_warning(label, status, raw_count, rows[0] if rows else {})
    return volumes, status, {"raw_count": raw_count, "parsed_count": parsed_count}


def _exchange_symbols(url, market_type):
    if not SYMBOL_UNIVERSE_FILTER_STATS:
        _reset_symbol_universe_stats()
    data, status = _safe_market_json(url)
    symbols = set()
    if not isinstance(data, dict):
        return symbols, status, 0
    raw_count = len(data.get("symbols", []) or [])
    for row in data.get("symbols", []):
        try:
            symbol = _normalize_exchange_symbol(row.get("symbol"))
            SYMBOL_UNIVERSE_FILTER_STATS["total_exchange_symbols"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("total_exchange_symbols", 0) or 0) + 1
            if not _is_tradeable_usdt_symbol(symbol):
                continue
            if market_type == "spot":
                if row.get("status") != "TRADING":
                    _symbol_filter_stat("inactive_or_non_trading")
                    continue
                permissions = row.get("permissions") or []
                if permissions and "SPOT" not in permissions and "TRADING" not in permissions:
                    _symbol_filter_stat("spot_permission_missing")
                    continue
            else:
                if row.get("status") != "TRADING":
                    _symbol_filter_stat("inactive_or_non_trading")
                    continue
                if row.get("contractType") not in (None, "PERPETUAL"):
                    _symbol_filter_stat("non_perpetual_futures")
                    continue
            SYMBOL_UNIVERSE_FILTER_STATS["eligible_before_volume_filter"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("eligible_before_volume_filter", 0) or 0) + 1
            symbols.add(symbol)
        except Exception:
            continue
    return symbols, status, raw_count


def _rank_symbol_universe(symbols, volume_maps):
    ranked = []
    if not volume_maps:
        for _symbol in symbols:
            _symbol_filter_stat("missing_ticker_data")
            SYMBOL_UNIVERSE_FILTER_STATS["missing_ticker_data"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("missing_ticker_data", 0) or 0) + 1
        SYMBOL_UNIVERSE_FILTER_STATS["liquid_symbols_count"] = 0
        return ranked
    for symbol in symbols:
        matched_volumes = [volume_map[symbol] for volume_map in volume_maps if symbol in volume_map]
        if not matched_volumes:
            _symbol_filter_stat("missing_ticker_data")
            SYMBOL_UNIVERSE_FILTER_STATS["missing_ticker_data"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("missing_ticker_data", 0) or 0) + 1
            continue
        volume = max(matched_volumes)
        if volume >= MIN_DYNAMIC_QUOTE_VOLUME:
            ranked.append((symbol, volume))
        else:
            _symbol_filter_stat("below_min_quote_volume")
            SYMBOL_UNIVERSE_FILTER_STATS["below_min_quote_volume"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("below_min_quote_volume", 0) or 0) + 1
    ranked.sort(key=lambda item: item[1], reverse=True)
    SYMBOL_UNIVERSE_FILTER_STATS["liquid_symbols_count"] = len(ranked)

    pinned = [symbol for symbol in SYMBOLS if symbol in {item[0] for item in ranked}]
    ordered = []
    seen = set()
    for symbol in pinned + [item[0] for item in ranked]:
        if symbol in seen:
            continue
        seen.add(symbol)
        ordered.append(symbol)
        if MAX_DYNAMIC_SYMBOLS > 0 and len(ordered) >= MAX_DYNAMIC_SYMBOLS:
            break
    return ordered


def _alternative_exchange_universe():
    """Filtered non-Binance universe used only when Binance universe sources fail."""
    data, status = _safe_market_json("https://api.kucoin.com/api/v1/market/allTickers")
    ranked = []
    meta = {"raw_count": 0, "parsed_count": 0, "above_volume_count": 0}
    if not isinstance(data, dict):
        SYMBOL_UNIVERSE_FILTER_STATS["missing_ticker_data"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("missing_ticker_data", 0) or 0) + 1
        return [], f"KUCOIN={status}", meta
    rows = ((data.get("data") or {}).get("ticker") or [])
    meta["raw_count"] = len(rows)
    diagnostic_candidates = []
    invalid_examples = []
    missing_examples = []
    if not rows:
        SYMBOL_UNIVERSE_FILTER_STATS["missing_ticker_data"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("missing_ticker_data", 0) or 0) + 1
        _append_symbol_universe_example("kucoin_missing_ticker_data_examples", {"reason": "empty_ticker_list", "status": status})
        return [], f"KUCOIN={status}", meta
    for row in rows:
        try:
            raw_symbol = str(row.get("symbol") or "").upper()
            symbol = _normalize_exchange_symbol(raw_symbol)
            if not symbol.endswith("USDT"):
                continue
            SYMBOL_UNIVERSE_FILTER_STATS["total_exchange_symbols"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("total_exchange_symbols", 0) or 0) + 1
            if not _is_tradeable_usdt_symbol(symbol):
                continue
            SYMBOL_UNIVERSE_FILTER_STATS["eligible_before_volume_filter"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("eligible_before_volume_filter", 0) or 0) + 1
            quote_volume, _volume_key = _quote_turnover_from_row(row, "KUCOIN_TICKER")
            diagnostic_item = {
                "symbol": symbol,
                "original_symbol": raw_symbol,
                "volValue": row.get("volValue"),
                "last_price": row.get("last"),
                "quote_turnover": quote_volume,
            }
            if quote_volume <= 0:
                _symbol_filter_stat("invalid_volume")
                SYMBOL_UNIVERSE_FILTER_STATS["invalid_volume"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("invalid_volume", 0) or 0) + 1
                if len(invalid_examples) < 10:
                    invalid_examples.append(diagnostic_item)
                continue
            meta["parsed_count"] += 1
            diagnostic_candidates.append(diagnostic_item)
            if quote_volume >= MIN_DYNAMIC_QUOTE_VOLUME:
                meta["above_volume_count"] += 1
                ranked.append((symbol, quote_volume))
            else:
                _symbol_filter_stat("below_min_quote_volume")
                SYMBOL_UNIVERSE_FILTER_STATS["below_min_quote_volume"] = int(SYMBOL_UNIVERSE_FILTER_STATS.get("below_min_quote_volume", 0) or 0) + 1
                _append_symbol_universe_example("kucoin_below_min_quote_volume_examples", diagnostic_item)
        except Exception:
            _symbol_filter_stat("invalid_volume")
            if len(invalid_examples) < 10:
                invalid_examples.append({"original_symbol": row.get("symbol") if isinstance(row, dict) else None, "reason": "exception"})
            continue
    if status == 200 and meta["raw_count"] > 0 and meta["parsed_count"] == 0:
        _record_symbol_universe_schema_warning("KUCOIN_TICKER", status, meta["raw_count"], rows[0] if rows else {})
        missing_examples.append({"reason": "parsed_zero_from_non_empty_response", "sample_keys": sorted(list((rows[0] or {}).keys()))[:20] if rows and isinstance(rows[0], dict) else []})
    _kucoin_volume_diagnostics(diagnostic_candidates, invalid_examples, missing_examples)
    ranked.sort(key=lambda item: item[1], reverse=True)
    SYMBOL_UNIVERSE_FILTER_STATS["liquid_symbols_count"] = max(
        int(SYMBOL_UNIVERSE_FILTER_STATS.get("liquid_symbols_count", 0) or 0),
        len(ranked),
    )
    SYMBOL_UNIVERSE_FILTER_STATS["authoritative_universe_source"] = "KUCOIN"
    SYMBOL_UNIVERSE_FILTER_STATS["authoritative_universe_count"] = int(meta.get("parsed_count", 0) or 0)
    SYMBOL_UNIVERSE_FILTER_STATS["kucoin_symbols_with_ticker"] = int(meta.get("parsed_count", 0) or 0)
    SYMBOL_UNIVERSE_FILTER_STATS["kucoin_symbols_above_volume"] = int(meta.get("above_volume_count", 0) or 0)
    SYMBOL_UNIVERSE_FILTER_STATS["symbols_dropped_due_to_cross_exchange_requirement"] = 0
    pinned = [symbol for symbol in SYMBOLS if symbol in {item[0] for item in ranked}]
    selected = []
    seen = set()
    for symbol in pinned + [item[0] for item in ranked]:
        if symbol in seen:
            continue
        seen.add(symbol)
        selected.append(symbol)
        if MAX_DYNAMIC_SYMBOLS > 0 and len(selected) >= MAX_DYNAMIC_SYMBOLS:
            break
    return selected, "KUCOIN", meta


def _merge_min_dynamic_symbols(selected, supported_symbols):
    """Keep a conservative minimum universe when ticker data is incomplete."""
    selected = [s for s in selected if _is_tradeable_usdt_symbol(s)]
    supported = {str(s or "").upper() for s in (supported_symbols or []) if _is_tradeable_usdt_symbol(s)}
    if SINGLE_SYMBOL_MODE or len(selected) >= MIN_DYNAMIC_SYMBOLS:
        return selected, 0
    seen = set(selected)
    added = 0
    fallback_order = [s for s in SYMBOLS if s in supported] + sorted(supported)
    limit = MAX_DYNAMIC_SYMBOLS if MAX_DYNAMIC_SYMBOLS > 0 else max(MIN_DYNAMIC_SYMBOLS, len(fallback_order))
    for symbol in fallback_order:
        if symbol in seen:
            continue
        selected.append(symbol)
        seen.add(symbol)
        added += 1
        if len(selected) >= MIN_DYNAMIC_SYMBOLS or len(selected) >= limit:
            break
    return selected, added


def get_scan_symbols(force_refresh=False):
    """Load a broad Binance Spot/Futures USDT universe, then scan only liquid symbols.

    This keeps the bot from being locked to a tiny fixed list without choking the
    worker by scanning hundreds of weak pairs every cycle.
    """
    now = time.time()
    if SINGLE_SYMBOL_MODE and SINGLE_SYMBOL:
        reason = _symbol_filter_reason(SINGLE_SYMBOL)
        selected = [SINGLE_SYMBOL] if not reason else list(SYMBOLS)
        DYNAMIC_SYMBOL_CACHE["time"] = now
        DYNAMIC_SYMBOL_CACHE["symbols"] = selected
        print(f"DYNAMIC_SYMBOLS_SELECTED count={len(selected)} max=single single_symbol_mode=True fallback_reason={reason or 'none'}")
        return list(selected)

    cached = DYNAMIC_SYMBOL_CACHE.get("symbols")
    if cached and not force_refresh and now - DYNAMIC_SYMBOL_CACHE.get("time", 0) < DYNAMIC_SYMBOLS_TTL_SECONDS:
        return list(cached)

    _reset_symbol_universe_stats()
    all_symbols = set()
    exchange_info_symbols = set()
    volume_maps = []
    failures = []
    source_counts = {}
    source_raw_counts = {}
    ticker_meta = {}
    source_statuses = {}
    exchange_info_count = 0
    ticker_count = 0

    for url, market_type, label in [
        ("https://api.binance.com/api/v3/exchangeInfo", "spot", "BINANCE_SPOT"),
        ("https://api.binance.us/api/v3/exchangeInfo", "spot", "BINANCE_US_SPOT"),
        ("https://fapi.binance.com/fapi/v1/exchangeInfo", "futures", "BINANCE_FUTURES"),
    ]:
        symbols, status, raw_count = _exchange_symbols(url, market_type)
        source_statuses[label] = status
        source_raw_counts[label] = raw_count
        source_counts[label] = len(symbols or [])
        exchange_info_count += len(symbols or [])
        if symbols:
            all_symbols.update(symbols)
            exchange_info_symbols.update(symbols)
        else:
            failures.append(f"{label}={status}")

    for url, label in [
        ("https://api.binance.com/api/v3/ticker/24hr", "BINANCE_SPOT_TICKER"),
        ("https://api.binance.us/api/v3/ticker/24hr", "BINANCE_US_TICKER"),
        ("https://fapi.binance.com/fapi/v1/ticker/24hr", "BINANCE_FUTURES_TICKER"),
    ]:
        volume_map, status, meta = _ticker_volume_map(url, label)
        source_statuses[label] = status
        ticker_meta[label] = meta
        source_raw_counts[label] = int((meta or {}).get("raw_count", 0) or 0)
        source_counts[label] = len(volume_map or {})
        ticker_count += int((meta or {}).get("parsed_count", 0) or 0)
        if volume_map:
            volume_maps.append(volume_map)
            all_symbols.update(volume_map.keys())
        else:
            failures.append(f"{label}={status}")

    binance_global_unavailable = any(str(source_statuses.get(label)) == "451" for label in (
        "BINANCE_SPOT",
        "BINANCE_FUTURES",
        "BINANCE_SPOT_TICKER",
        "BINANCE_FUTURES_TICKER",
    ))
    selected = None
    if binance_global_unavailable:
        alt_selected, alt_status, alt_meta = _alternative_exchange_universe()
        source_raw_counts["KUCOIN"] = int((alt_meta or {}).get("raw_count", 0) or 0)
        source_counts["KUCOIN_TICKER"] = int((alt_meta or {}).get("parsed_count", 0) or 0)
        ticker_meta["KUCOIN_TICKER"] = alt_meta
        ticker_count += int((alt_meta or {}).get("parsed_count", 0) or 0)
        if alt_selected:
            selected = alt_selected
            failures.append(f"fallback=alternative_exchange_universe:{alt_status}")
            SYMBOL_UNIVERSE_FILTER_STATS["fallback_reason"] = f"alternative_exchange_universe:{alt_status}; global_binance_unavailable"
        else:
            failures.append(f"alternative_exchange_universe={alt_status}")

    if selected is None and all_symbols:
        SYMBOL_UNIVERSE_FILTER_STATS["authoritative_universe_source"] = "BINANCE_COMBINED"
        SYMBOL_UNIVERSE_FILTER_STATS["authoritative_universe_count"] = len(all_symbols)
        selected = _rank_symbol_universe(all_symbols, volume_maps)
    elif selected is None:
        selected, alt_status, alt_meta = _alternative_exchange_universe()
        source_raw_counts["KUCOIN"] = int((alt_meta or {}).get("raw_count", 0) or 0)
        source_counts["KUCOIN_TICKER"] = int((alt_meta or {}).get("parsed_count", 0) or 0)
        ticker_meta["KUCOIN_TICKER"] = alt_meta
        ticker_count += int((alt_meta or {}).get("parsed_count", 0) or 0)
        if selected:
            failures.append(f"fallback=alternative_exchange_universe:{alt_status}")
            SYMBOL_UNIVERSE_FILTER_STATS["fallback_reason"] = f"alternative_exchange_universe:{alt_status}"
        else:
            selected = list(SYMBOLS)
            failures.append(f"fallback=all_sources_empty; alternative={alt_status}")
            SYMBOL_UNIVERSE_FILTER_STATS["fallback_reason"] = f"all_sources_empty; alternative={alt_status}"

    if not selected:
        selected, alt_status, alt_meta = _alternative_exchange_universe()
        source_raw_counts["KUCOIN"] = int((alt_meta or {}).get("raw_count", 0) or 0)
        source_counts["KUCOIN_TICKER"] = int((alt_meta or {}).get("parsed_count", 0) or 0)
        ticker_meta["KUCOIN_TICKER"] = alt_meta
        ticker_count += int((alt_meta or {}).get("parsed_count", 0) or 0)
        if selected:
            failures.append(f"fallback=alternative_exchange_universe:{alt_status}")
            SYMBOL_UNIVERSE_FILTER_STATS["fallback_reason"] = f"alternative_exchange_universe:{alt_status}"
        else:
            selected = list(SYMBOLS)
            failures.append(f"fallback=ranked_empty; alternative={alt_status}")
            SYMBOL_UNIVERSE_FILTER_STATS["fallback_reason"] = f"ranked_empty; alternative={alt_status}"

    matched_count = len([symbol for symbol in selected if any(symbol in volume_map for volume_map in volume_maps)])
    if str(SYMBOL_UNIVERSE_FILTER_STATS.get("authoritative_universe_source", "")).upper() == "KUCOIN":
        matched_count = min(len(selected), int(SYMBOL_UNIVERSE_FILTER_STATS.get("kucoin_symbols_with_ticker", 0) or 0))
    fallback_added_count = 0
    if selected and selected != list(SYMBOLS):
        selected = selected[:MAX_DYNAMIC_SYMBOLS] if MAX_DYNAMIC_SYMBOLS > 0 else selected
    elif selected == list(SYMBOLS):
        limit = MAX_DYNAMIC_SYMBOLS if MAX_DYNAMIC_SYMBOLS > 0 else len(selected)
        selected = selected[:limit]

    DYNAMIC_SYMBOL_CACHE["time"] = now
    DYNAMIC_SYMBOL_CACHE["symbols"] = selected
    SYMBOL_UNIVERSE_FILTER_STATS["selected_final_count"] = len(selected)
    symbol_limit = MAX_DYNAMIC_SYMBOLS if MAX_DYNAMIC_SYMBOLS > 0 else "ALL"
    fallback_reason = SYMBOL_UNIVERSE_FILTER_STATS.get("fallback_reason", "none")
    if fallback_reason == "none" and failures:
        fallback_reason = "; ".join(failures)
    filter_reasons = SYMBOL_UNIVERSE_FILTER_STATS.get("filtered_by_reason", {})
    source_used = "legacy_fallback"
    if str(fallback_reason).startswith("alternative_exchange_universe"):
        source_used = "kucoin_fallback"
    elif selected != list(SYMBOLS):
        active_sources = [label for label, count in source_counts.items() if int(count or 0) > 0]
        source_used = "+".join(active_sources) if active_sources else "ranked_exchange_universe"
    print(
        "DYNAMIC_SYMBOLS_SELECTED "
        f"count={len(selected)} max={symbol_limit} configured_max={MAX_DYNAMIC_SYMBOLS} "
        f"min_quote_volume={MIN_DYNAMIC_QUOTE_VOLUME} source_used={source_used} "
        f"sources={json.dumps(source_counts, sort_keys=True)} "
        f"raw_binance_spot={source_raw_counts.get('BINANCE_SPOT', 0)} "
        f"raw_binance_futures={source_raw_counts.get('BINANCE_FUTURES', 0)} "
        f"raw_binance_us={source_raw_counts.get('BINANCE_US_SPOT', 0)} "
        f"raw_kucoin={source_raw_counts.get('KUCOIN', 0)} "
        f"authoritative_universe_source={SYMBOL_UNIVERSE_FILTER_STATS.get('authoritative_universe_source', 'none')} "
        f"authoritative_universe_count={SYMBOL_UNIVERSE_FILTER_STATS.get('authoritative_universe_count', 0)} "
        f"kucoin_symbols_with_ticker={SYMBOL_UNIVERSE_FILTER_STATS.get('kucoin_symbols_with_ticker', 0)} "
        f"kucoin_symbols_above_volume={SYMBOL_UNIVERSE_FILTER_STATS.get('kucoin_symbols_above_volume', 0)} "
        f"symbols_dropped_due_to_cross_exchange_requirement={SYMBOL_UNIVERSE_FILTER_STATS.get('symbols_dropped_due_to_cross_exchange_requirement', 0)} "
        f"total_exchange_symbols={SYMBOL_UNIVERSE_FILTER_STATS.get('total_exchange_symbols', 0)} "
        f"eligible_before_volume_filter={SYMBOL_UNIVERSE_FILTER_STATS.get('eligible_before_volume_filter', 0)} "
        f"excluded_stablecoin={filter_reasons.get('stable_or_fiat_base', 0)} "
        f"excluded_leveraged={filter_reasons.get('leveraged_token_suffix', 0) + sum(int(v or 0) for k, v in filter_reasons.items() if str(k).startswith('excluded_keyword_UP') or str(k).startswith('excluded_keyword_DOWN') or str(k).startswith('excluded_keyword_BULL') or str(k).startswith('excluded_keyword_BEAR'))} "
        f"excluded_inactive_non_perpetual={filter_reasons.get('inactive_or_non_trading', 0) + filter_reasons.get('non_perpetual_futures', 0)} "
        f"excluded_blocklist_problematic={filter_reasons.get('known_problematic_base', 0) + filter_reasons.get('starts_with_1000', 0)} "
        f"excluded_low_volume={filter_reasons.get('below_min_quote_volume', 0)} "
        f"missing_ticker_data={SYMBOL_UNIVERSE_FILTER_STATS.get('missing_ticker_data', 0)} "
        f"invalid_volume={SYMBOL_UNIVERSE_FILTER_STATS.get('invalid_volume', 0)} "
        f"below_min_quote_volume={SYMBOL_UNIVERSE_FILTER_STATS.get('below_min_quote_volume', 0)} "
        f"symbol_match_failed={SYMBOL_UNIVERSE_FILTER_STATS.get('symbol_match_failed', 0)} "
        f"filtered_by_reason={json.dumps(SYMBOL_UNIVERSE_FILTER_STATS.get('filtered_by_reason', {}), sort_keys=True)} "
        f"liquid_symbols_count={SYMBOL_UNIVERSE_FILTER_STATS.get('liquid_symbols_count', 0)} "
        f"exchange_info_count={exchange_info_count} ticker_count={ticker_count} "
        f"ticker_meta={json.dumps(ticker_meta, sort_keys=True)} "
        f"matched_count={matched_count} fallback_added_count={fallback_added_count} final_count={len(selected)} "
        f"fetch_failures={json.dumps(failures, sort_keys=True)} "
        f"fallback_reason={fallback_reason} "
        f"selected_first_20={json.dumps(selected[:20])}"
    )
    return list(selected)


def log_market_source_once(source, symbol, timeframe):
    now = time.time()
    key = (source, symbol, timeframe)
    last_seen = MARKET_SOURCE_LOG_CACHE.get(key, 0)
    if now - last_seen >= MARKET_SOURCE_LOG_TTL_SECONDS:
        MARKET_SOURCE_LOG_CACHE[key] = now
        if SIGNAL_DEBUG_LOGS:
            print(f"MARKET_DATA_SOURCE {source} symbol={symbol} timeframe={timeframe}")

# منع تكرار نفس الأزواج دايمًا
LAST_USED_PAIRS = []


# ================= MARKET DATA HELPERS =================
def interval_to_seconds(interval):
    mapping = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "6h": 21600,
        "8h": 28800,
        "12h": 43200,
        "1d": 86400,
    }
    return mapping.get(interval, 300)


def get_higher_tf(interval):
    mapping = {
        "5m": "15m",
        "15m": "1h",
        "30m": "4h",
        "1h": "4h",
        "4h": "1d"
    }
    return mapping.get(interval, "15m")


def parse_kucoin_klines_to_df(rows):
    try:
        if not rows or not isinstance(rows, list):
            return None

        parsed = []
        for row in rows:
            # KuCoin format:
            # [time, open, close, high, low, volume, turnover]
            if not isinstance(row, list) or len(row) < 6:
                continue

            parsed.append([
                int(row[0]) * 1000,
                float(row[1]),  # open
                float(row[3]),  # high
                float(row[4]),  # low
                float(row[2]),  # close
                float(row[5])   # volume
            ])

        if not parsed:
            return None

        df = pd.DataFrame(parsed, columns=["time", "open", "high", "low", "close", "volume"])
        df = df.sort_values("time").reset_index(drop=True)

        # Safety: Binance/Kline endpoints include the currently-forming candle.
        # Signals must be based on closed candles only; otherwise entries can
        # repaint during the candle and arrive after price has already moved.
        if len(df) > 2:
            df = df.iloc[:-1].reset_index(drop=True)

        return df
    except Exception as e:
        print(f"parse_kucoin_klines_to_df error: {e}")
        return None


def parse_binance_klines_to_df(data):
    try:
        if not isinstance(data, list) or len(data) == 0:
            return None

        df = pd.DataFrame(data)
        if df.empty:
            return None

        # Binance klines contain base volume at index 5 and quote volume at index 7.
        # Quote volume is more stable across assets and avoids false LOW_LIQUIDITY
        # decisions when comparing cheap coins with large caps.
        cols = [0, 1, 2, 3, 4, 5]
        has_quote_volume = df.shape[1] > 7
        if has_quote_volume:
            cols.append(7)
        df = df[cols]
        df.columns = ["time", "open", "high", "low", "close", "volume"] + (["quote_volume"] if has_quote_volume else [])

        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        if "quote_volume" in df.columns:
            df["quote_volume"] = df["quote_volume"].astype(float)

        df = df.sort_values("time").reset_index(drop=True)

        # Safety: Binance/Kline endpoints include the currently-forming candle.
        # Signals must be based on closed candles only; otherwise entries can
        # repaint during the candle and arrive after price has already moved.
        if len(df) > 2:
            df = df.iloc[:-1].reset_index(drop=True)

        return df
    except Exception as e:
        print(f"parse_binance_klines_to_df error: {e}")
        return None


# ================= MARKET DATA =================
def get_market_data(symbol, interval="5m", limit=250):
    """
    Priority:
    1) Binance
    2) Binance US
    3) KuCoin
    """

    KUCOIN_TF_MAP = {
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1hour",
        "2h": "2hour",
        "4h": "4hour",
        "6h": "6hour",
        "8h": "8hour",
        "12h": "12hour",
        "1d": "1day",
    }

    endpoints = [
        ("BINANCE", f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"),
        ("BINANCE_FUTURES", f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"),
        ("BINANCE_US", f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")
    ]

    failures = []
    binance_global_451 = False

    for source_name, url in endpoints:
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)

            if source_name == "BINANCE" and response.status_code == 451:
                binance_global_451 = True
                failures.append(f"{source_name}=451")
                continue

            if response.status_code != 200:
                failures.append(f"{source_name}={response.status_code}")
                continue

            try:
                data = response.json()
            except Exception as json_error:
                failures.append(f"{source_name}=invalid_json:{json_error}")
                continue

            if isinstance(data, dict):
                failures.append(f"{source_name}=api_error")
                continue

            df = parse_binance_klines_to_df(data)
            if df is not None and not df.empty:
                if source_name == "BINANCE_US" and binance_global_451:
                    log_market_source_once("BINANCE_US", symbol, interval)
                elif source_name == "BINANCE_FUTURES":
                    log_market_source_once("BINANCE_FUTURES", symbol, interval)
                return df

            failures.append(f"{source_name}=empty")

        except Exception as e:
            failures.append(f"{source_name}=request_failed:{e}")
            continue

    # ===================== FALLBACK TO KUCOIN =====================
    try:
        kucoin_interval = KUCOIN_TF_MAP.get(interval, interval)
        kucoin_symbol = symbol.replace("USDT", "-USDT")

        kucoin_url = f"https://api.kucoin.com/api/v1/market/candles?type={kucoin_interval}&symbol={kucoin_symbol}"
        response = requests.get(kucoin_url, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            failures.append(f"KUCOIN={response.status_code}")
            print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
            return None

        data = response.json()

        if not isinstance(data, dict) or "data" not in data:
            failures.append("KUCOIN=invalid_response")
            print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
            return None

        candles = data["data"]

        if not candles:
            failures.append("KUCOIN=empty")
            print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
            return None

        candles = candles[::-1]

        import pandas as pd

        df = pd.DataFrame(candles, columns=[
            "time", "open", "close", "high", "low", "volume", "turnover"
        ])

        df["time"] = pd.to_datetime(df["time"].astype(int), unit="s")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df[["time", "open", "high", "low", "close", "volume"]]
        df.dropna(inplace=True)

        # KuCoin can also return the currently-forming candle first/last after
        # normalization. Keep signal generation on closed candles only.
        if len(df) > 2:
            df = df.iloc[:-1].reset_index(drop=True)

        if df is not None and not df.empty:
            return df

        failures.append("KUCOIN=parsed_empty")
        print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
        return None

    except Exception as e:
        failures.append(f"KUCOIN=api_error:{e}")
        print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
        return None

# ================= RSI =================
def rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean().replace(0, np.nan)

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ================= MACD =================
def macd(df):
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()

    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()

    return macd_line, signal_line


# ================= EMA =================
def ema(df, period):
    return df["close"].ewm(span=period, adjust=False).mean()


# ================= ATR =================
def atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ================= TREND =================
def detect_trend(df):
    if len(df) < 50:
        return "UNKNOWN"

    ema20v = ema(df, 20)
    ema50v = ema(df, 50)

    if ema20v.iloc[-1] > ema50v.iloc[-1]:
        return "UP"
    return "DOWN"


def trend_strength(df):
    if len(df) < 100:
        return "WEAK"

    ema20v = ema(df, 20)
    ema50v = ema(df, 50)
    ema100v = ema(df, 100)

    if ema20v.iloc[-1] > ema50v.iloc[-1] > ema100v.iloc[-1]:
        return "STRONG_BULL"
    elif ema20v.iloc[-1] < ema50v.iloc[-1] < ema100v.iloc[-1]:
        return "STRONG_BEAR"
    return "MIXED"


# ================= VOLUME =================
def _volume_series(df):
    """Return the most reliable volume series for relative checks.

    Binance/Bybit klines expose both base volume and quote volume. Quote volume
    is better for cross-symbol liquidity quality, while base volume can make
    low-priced assets look artificially large or tiny.
    """
    try:
        if df is not None and "quote_volume" in df.columns:
            series = pd.to_numeric(df["quote_volume"], errors="coerce")
            if series.dropna().tail(20).sum() > 0:
                return series
        return pd.to_numeric(df["volume"], errors="coerce")
    except Exception:
        return pd.Series(dtype="float64")


def robust_volume_profile(df, lookback=24):
    """Robust relative-volume profile based on closed candles only.

    Uses the previous candles as the baseline and blends median/mean so a single
    huge spike does not make the next normal candle look like 0.02x liquidity.
    This prevents the engine from incorrectly rejecting large-cap pairs.
    """
    try:
        closed_df = closed_candle_frame(df)
        series = _volume_series(closed_df).dropna()
        if len(series) < 22:
            return {
                "volume_ratio": 0.0,
                "volume_state": "THIN",
                "volume_score": 38,
                "current_closed_volume": None,
                "average_volume_20": None,
                "data_source": "quote_volume" if df is not None and "quote_volume" in getattr(df, "columns", []) else "volume",
                "candle_closed": True,
                "fail_closed": True,
            }
        current = _safe_float(series.iloc[-1])
        history = series.iloc[-21:-1] if len(series) >= 21 else series.iloc[:-1]
        history = history[history > 0]
        if current <= 0 or history.empty:
            return {
                "volume_ratio": 0.0,
                "volume_state": "THIN",
                "volume_score": 38,
                "current_closed_volume": round(current, 6),
                "average_volume_20": 0,
                "data_source": "quote_volume" if df is not None and "quote_volume" in getattr(df, "columns", []) else "volume",
                "candle_closed": True,
            }
        median_ref = _safe_float(history.median())
        mean_ref = _safe_float(history.mean())
        avg20 = _safe_float(history.mean())
        # Use the larger stable reference, but cap extreme spike influence.
        ref = max(median_ref, min(mean_ref, median_ref * 2.5 if median_ref > 0 else mean_ref))
        ratio = current / ref if ref > 0 else 0.0
        if ratio >= 1.35:
            state, score = "EXPANSION", 82
        elif ratio >= 1.05:
            state, score = "STRONG", 72
        elif ratio >= 0.55:
            state, score = "NORMAL", 58
        else:
            state, score = "THIN", 38
        profile = {
            "volume_ratio": round(ratio, 3),
            "volume_state": state,
            "volume_score": score,
            "current_closed_volume": round(current, 6),
            "average_volume_20": round(avg20, 6),
            "data_source": "quote_volume" if df is not None and "quote_volume" in getattr(df, "columns", []) else "volume",
            "candle_closed": True,
        }
        if SIGNAL_DEBUG_LOGS:
            print(
                "VOLUME_PROFILE "
                f"current_closed_volume={profile['current_closed_volume']} "
                f"average_volume_20={profile['average_volume_20']} "
                f"volume_ratio={profile['volume_ratio']} "
                f"data_source={profile['data_source']} candle_closed=True"
            )
        return profile
    except Exception:
        return {"volume_ratio": 0.0, "volume_state": "UNKNOWN", "volume_score": 45}


def volume_strength(df):
    profile = robust_volume_profile(df)
    return "STRONG" if profile.get("volume_state") in ["STRONG", "EXPANSION"] else "WEAK"


# ================= SMART MONEY =================
def detect_smc(df):
    highs = df["high"].rolling(10).max()
    lows = df["low"].rolling(10).min()

    if len(df) < 12:
        return "RANGE"

    if pd.notna(highs.iloc[-2]) and df["close"].iloc[-1] > highs.iloc[-2]:
        return "LIQUIDITY_BREAK_UP"
    elif pd.notna(lows.iloc[-2]) and df["close"].iloc[-1] < lows.iloc[-2]:
        return "LIQUIDITY_BREAK_DOWN"

    return "RANGE"


# ================= STRUCTURE =================
def market_structure(df):
    if len(df) < 20:
        return "UNKNOWN"

    recent_high = df["high"].tail(20).max()
    recent_low = df["low"].tail(20).min()
    current = df["close"].iloc[-1]

    if current >= recent_high * 0.997:
        return "NEAR_BREAKOUT_HIGH"
    elif current <= recent_low * 1.003:
        return "NEAR_BREAKOUT_LOW"

    return "MID_RANGE"


# ================= CHOPPY MARKET FILTER =================
def is_choppy(df):
    try:
        if df is None or len(df) < 50:
            return True

        ema20v = ema(df, 20)
        ema50v = ema(df, 50)

        diff = abs(ema20v.iloc[-1] - ema50v.iloc[-1])
        price = df["close"].iloc[-1]

        if price <= 0:
            return True

        return (diff / price) < 0.0012
    except:
        return True


# ================= MOMENTUM FILTER =================
def strong_momentum(df):
    try:
        if df is None or len(df) < 5:
            return False

        last = df["close"].iloc[-1]
        prev = df["close"].iloc[-3]

        if prev <= 0:
            return False

        change = abs(last - prev) / prev

        return change > 0.0018
    except:
        return False


# ================= NEW: LATE ENTRY FILTER =================
def late_entry_filter(df, direction):
    try:
        if df is None or len(df) < 30:
            return False

        close = float(df["close"].iloc[-1])
        open_price = float(df["open"].iloc[-1])
        high = float(df["high"].iloc[-1])
        low = float(df["low"].iloc[-1])

        ema20v = ema(df, 20).iloc[-1]
        ema50v = ema(df, 50).iloc[-1]
        atr_val = atr(df).iloc[-1]

        if pd.isna(ema20v) or pd.isna(ema50v) or pd.isna(atr_val) or atr_val <= 0 or close <= 0:
            return False

        candle_body = abs(close - open_price)
        candle_range = abs(high - low)

        # شمعة انفجارية زيادة = غالبًا دخول متأخر
        if candle_range > (atr_val * 2.4):
            return True

        if candle_body > (atr_val * 1.6):
            return True

        # بعيد جدًا عن المتوسطات
        dist_ema20 = abs(close - ema20v) / close
        dist_ema50 = abs(close - ema50v) / close

        if dist_ema20 > 0.012:
            return True

        if dist_ema50 > 0.02:
            return True

        # داخل LONG بعد شدّة صعود / SHORT بعد شدّة هبوط
        if direction == "LONG":
            recent_push = (close - df["close"].iloc[-4]) / df["close"].iloc[-4]
            if recent_push > 0.012:
                return True

        if direction == "SHORT":
            recent_push = (df["close"].iloc[-4] - close) / df["close"].iloc[-4]
            if recent_push > 0.012:
                return True

        return False
    except Exception as e:
        print(f"late_entry_filter error: {e}")
        return False


# ================= NEW: SUPPORT / RESISTANCE FILTER =================
def support_resistance_filter(df, direction):
    try:
        if df is None or len(df) < 40:
            return True

        close = float(df["close"].iloc[-1])
        atr_val = atr(df).iloc[-1]

        if pd.isna(atr_val) or atr_val <= 0 or close <= 0:
            return True

        recent_high = float(df["high"].tail(25).max())
        recent_low = float(df["low"].tail(25).min())

        resistance_distance = abs(recent_high - close)
        support_distance = abs(close - recent_low)

        # LONG تحت مقاومة قريبة جدًا
        if direction == "LONG":
            if recent_high > close and resistance_distance < (atr_val * 1.15):
                return False

        # SHORT فوق دعم قريب جدًا
        if direction == "SHORT":
            if recent_low < close and support_distance < (atr_val * 1.15):
                return False

        return True
    except Exception as e:
        print(f"support_resistance_filter error: {e}")
        return True


# ================= NEW: PULLBACK ENTRY QUALITY =================
def pullback_entry_quality(df, direction):
    try:
        if df is None or len(df) < 25:
            return False

        close = float(df["close"].iloc[-1])
        ema20v = float(ema(df, 20).iloc[-1])

        if close <= 0 or ema20v <= 0:
            return False

        dist = abs(close - ema20v) / close

        # الدخول المثالي يكون قريب نسبيًا من المتوسط
        if dist > 0.0095:
            return False

        # نمنع الدخول لو آخر 3 شمعات كلها في نفس الاتجاه بقوة
        closes = df["close"].tail(4).tolist()

        if direction == "LONG":
            if closes[-1] > closes[-2] > closes[-3] > closes[-4]:
                if ((closes[-1] - closes[-4]) / closes[-4]) > 0.01:
                    return False

        if direction == "SHORT":
            if closes[-1] < closes[-2] < closes[-3] < closes[-4]:
                if ((closes[-4] - closes[-1]) / closes[-4]) > 0.01:
                    return False

        return True
    except Exception as e:
        print(f"pullback_entry_quality error: {e}")
        return False


# ================= NEW: REJECTION WICK FILTER =================
def rejection_wick_filter(df, direction):
    try:
        if df is None or len(df) < 5:
            return True

        last = df.iloc[-1]

        open_price = float(last["open"])
        close = float(last["close"])
        high = float(last["high"])
        low = float(last["low"])

        body = abs(close - open_price)
        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low

        if body <= 0:
            body = 0.0000001

        # LONG: لو فيه رفض علوي قوي جدًا → خطر
        if direction == "LONG":
            if upper_wick > body * 2.2 and close < high:
                return False

        # SHORT: لو فيه رفض سفلي قوي جدًا → خطر
        if direction == "SHORT":
            if lower_wick > body * 2.2 and close > low:
                return False

        return True
    except Exception as e:
        print(f"rejection_wick_filter error: {e}")
        return True


# ================= HIGHER TF CONFIRMATION =================
def higher_timeframe_confirmation(symbol, direction, current_interval):
    try:
        higher_tf = get_higher_tf(current_interval)
        df_htf = get_market_data(symbol, higher_tf, limit=200)

        if df_htf is None or len(df_htf) < 50:
            return False

        trend_htf = detect_trend(df_htf)
        trend_power_htf = trend_strength(df_htf)
        smc_htf = detect_smc(df_htf)

        if direction == "LONG":
            return (
                trend_htf == "UP"
                and trend_power_htf in ["STRONG_BULL", "MIXED"]
                and smc_htf != "LIQUIDITY_BREAK_DOWN"
            )

        elif direction == "SHORT":
            return (
                trend_htf == "DOWN"
                and trend_power_htf in ["STRONG_BEAR", "MIXED"]
                and smc_htf != "LIQUIDITY_BREAK_UP"
            )

        return False
    except Exception as e:
        print(f"higher_timeframe_confirmation error for {symbol} {current_interval}: {e}")
        return False


# ================= VOLATILITY FILTER =================
def volatility_ok(df):
    try:
        atr_val = atr(df).iloc[-1]
        close_val = df["close"].iloc[-1]

        if pd.isna(atr_val) or close_val <= 0:
            return True

        ratio = atr_val / close_val
        return 0.0007 <= ratio <= 0.06
    except:
        return True



def cached_market_data(symbol, interval="5m", limit=250, ttl=MARKET_CONTEXT_TTL_SECONDS):
    try:
        key = (symbol, interval, int(limit))
        now = time.time()
        cached = MARKET_CONTEXT_CACHE.get(key)
        if cached and now - cached["time"] <= ttl:
            return cached["df"]
        df = get_market_data(symbol, interval, limit=limit)
        if df is not None and not df.empty:
            MARKET_CONTEXT_CACHE[key] = {"time": now, "df": df}
        return df
    except Exception as e:
        print(f"cached_market_data error {symbol} {interval}: {e}")
        return None


def _safe_ema_value(df, period):
    try:
        value = ema(df, period).iloc[-1]
        return None if pd.isna(value) else float(value)
    except Exception:
        return None


def _lower_highs_lows(df):
    try:
        if df is None or len(df) < 40:
            return False
        recent = df.tail(40)
        first = recent.head(20)
        last = recent.tail(20)
        return float(last["high"].max()) < float(first["high"].max()) and float(last["low"].min()) < float(first["low"].min())
    except Exception:
        return False


def detect_market_regime(btc_candles, eth_candles=None):
    try:
        df = btc_candles
        if df is None or len(df) < 80:
            return "SIDEWAYS"
        close = float(df["close"].iloc[-1])
        if close <= 0:
            return "SIDEWAYS"
        ema50 = _safe_ema_value(df, 50)
        ema200 = _safe_ema_value(df, 200) or _safe_ema_value(df, 100)
        atr_series = atr(df).dropna()
        atr_val = float(atr_series.iloc[-1]) if len(atr_series) else 0
        atr_avg = float(atr_series.tail(30).mean()) if len(atr_series) >= 30 else atr_val
        atr_expanding = bool(atr_avg and atr_val > atr_avg * 1.35)
        momentum_6 = (close - float(df["close"].iloc[-7])) / float(df["close"].iloc[-7]) if float(df["close"].iloc[-7]) else 0
        last = df.iloc[-1]
        last_body = (float(last["open"]) - float(last["close"])) / close if close else 0
        large_red = float(last["close"]) < float(last["open"]) and last_body > 0.018
        lower_structure = _lower_highs_lows(df)

        eth_bearish = False
        if eth_candles is not None and len(eth_candles) >= 80:
            eth50 = _safe_ema_value(eth_candles, 50)
            eth200 = _safe_ema_value(eth_candles, 200) or _safe_ema_value(eth_candles, 100)
            eth_bearish = bool(eth50 and eth200 and eth50 < eth200)

        if large_red or (momentum_6 <= -0.028 and atr_expanding) or (lower_structure and momentum_6 <= -0.018):
            return "DUMP_RISK"
        if ema50 and ema200 and ema50 < ema200 and (momentum_6 < -0.006 or lower_structure or eth_bearish):
            return "BEARISH"
        if atr_expanding and abs(momentum_6) > 0.02:
            return "HIGH_VOLATILITY"
        if ema50 and ema200 and ema50 > ema200 and momentum_6 >= -0.004:
            return "BULLISH"
        return "SIDEWAYS"
    except Exception as e:
        print(f"detect_market_regime error: {e}")
        return "SIDEWAYS"


def multi_timeframe_quality(symbol, direction, current_interval, current_df):
    result = {
        "state": "UNCONFIRMED",
        "score": 0,
        "strong_conflict": False,
        "reason": "insufficient higher timeframe data",
    }
    try:
        frames = {
            current_interval: current_df,
            "15m": cached_market_data(symbol, "15m", limit=220),
            "1h": cached_market_data(symbol, "1h", limit=220),
            "4h": cached_market_data(symbol, "4h", limit=220),
        }
        score = 0
        conflicts = 0
        confirmations = 0
        for tf, frame in frames.items():
            if frame is None or len(frame) < 60:
                continue
            trend = detect_trend(frame)
            power = trend_strength(frame)
            smc_state = detect_smc(frame)
            if direction == "LONG":
                if trend == "UP" and power != "STRONG_BEAR" and smc_state != "LIQUIDITY_BREAK_DOWN":
                    confirmations += 1
                    score += 5 if tf in ["1h", "4h"] else 3
                elif power == "STRONG_BEAR" or smc_state == "LIQUIDITY_BREAK_DOWN":
                    conflicts += 1
            else:
                if trend == "DOWN" and power != "STRONG_BULL" and smc_state != "LIQUIDITY_BREAK_UP":
                    confirmations += 1
                    score += 5 if tf in ["1h", "4h"] else 3
                elif power == "STRONG_BULL" or smc_state == "LIQUIDITY_BREAK_UP":
                    conflicts += 1

        result["score"] = min(score, 18)
        result["strong_conflict"] = conflicts >= 2
        if confirmations >= 3 and not result["strong_conflict"]:
            result["state"] = "CONFIRMED"
            result["reason"] = "5m/15m timing aligns with 1h/4h context"
        elif confirmations >= 2 and conflicts == 0:
            result["state"] = "PARTIAL"
            result["reason"] = "partial multi-timeframe alignment"
        else:
            result["reason"] = f"weak MTF alignment confirmations={confirmations} conflicts={conflicts}"
        return result
    except Exception as e:
        result["reason"] = f"multi-timeframe error: {e}"
        return result


def spot_long_confirmation(df, support):
    try:
        if df is None or len(df) < 25 or support is None:
            return False, "missing support confirmation"
        support = float(support)
        recent = df.tail(8)
        close = float(df["close"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])
        last_open = float(df["open"].iloc[-1])
        last_low = float(df["low"].iloc[-1])
        rsi_series = rsi(df).dropna()
        vol_ma = df["volume"].rolling(20).mean().iloc[-1]
        volume_reclaim = pd.notna(vol_ma) and float(df["volume"].iloc[-1]) > float(vol_ma) * 1.08 and close > support
        support_bounce = recent["low"].min() <= support * 1.004 and close > support * 1.006
        liquidity_sweep = last_low < support * 0.998 and close > support
        higher_low = float(df["low"].iloc[-1]) > float(df["low"].iloc[-3]) and close > prev_close
        bullish_engulfing = close > last_open and close > float(df["open"].iloc[-2]) and last_open <= prev_close
        rsi_recovery = len(rsi_series) >= 3 and float(rsi_series.iloc[-3]) < 38 and float(rsi_series.iloc[-1]) > float(rsi_series.iloc[-2])
        confirmations = []
        if support_bounce:
            confirmations.append("support bounce")
        if liquidity_sweep:
            confirmations.append("liquidity sweep reclaim")
        if volume_reclaim:
            confirmations.append("volume reclaim")
        if higher_low:
            confirmations.append("higher low")
        if bullish_engulfing:
            confirmations.append("bullish engulfing")
        if rsi_recovery:
            confirmations.append("RSI recovery")
        if confirmations:
            return True, ", ".join(confirmations[:3])
        return False, "no spot LONG reversal confirmation near support"
    except Exception as e:
        return False, f"reversal confirmation error: {e}"


def learning_penalty(symbol, direction, setup_type):
    try:
        path = os.path.join(os.path.dirname(__file__), "trades.json")
        if not os.path.exists(path):
            return 0
        with open(path, "r", encoding="utf-8") as f:
            trades = json.load(f)
        closed = [t for t in trades if str(t.get("status", "")).upper() in ["TP", "SL"]][-80:]
        if not closed:
            return 0
        symbol_losses = sum(1 for t in closed[-25:] if t.get("pair") == symbol and str(t.get("status", "")).upper() == "SL")
        direction_losses = sum(1 for t in closed[-25:] if t.get("direction") == direction and str(t.get("status", "")).upper() == "SL")
        setup_losses = sum(1 for t in closed[-40:] if t.get("setup_type") == setup_type and str(t.get("status", "")).upper() == "SL")
        penalty = min(symbol_losses * 4 + direction_losses * 2 + setup_losses * 3, 18)
        return int(penalty)
    except Exception:
        return 0


def current_market_regime():
    btc_1h = cached_market_data("BTCUSDT", "1h", limit=220)
    eth_1h = cached_market_data("ETHUSDT", "1h", limit=220)
    return detect_market_regime(btc_1h, eth_1h)


def choose_signal_direction(symbol, interval, df, score, trend, trend_power, threshold):
    regime = current_market_regime()
    short_mtf = multi_timeframe_quality(symbol, "SHORT", interval, df)
    long_mtf = multi_timeframe_quality(symbol, "LONG", interval, df)
    local_bearish = trend == "DOWN" or trend_power == "STRONG_BEAR"
    local_bullish = trend == "UP" or trend_power == "STRONG_BULL"

    if regime in ["BEARISH", "DUMP_RISK"] and short_mtf.get("state") == "CONFIRMED" and local_bearish:
        return "SHORT", regime, short_mtf, "bearish market and MTF confirmed"

    if regime == "BULLISH" and score >= threshold and long_mtf.get("state") == "CONFIRMED" and local_bullish:
        return "LONG", regime, long_mtf, "bullish market and MTF confirmed"

    if regime in ["SIDEWAYS", "HIGH_VOLATILITY"]:
        return None, regime, {"state": "UNCONFIRMED", "reason": "sideways or high volatility"}, "SIDEWAYS_OR_UNCONFIRMED"

    if long_mtf.get("state") != "CONFIRMED" and short_mtf.get("state") != "CONFIRMED":
        return None, regime, {"state": "UNCONFIRMED", "reason": "MTF not confirmed"}, "SIDEWAYS_OR_UNCONFIRMED"

    if score <= -threshold and short_mtf.get("state") == "CONFIRMED" and local_bearish:
        return "SHORT", regime, short_mtf, "bearish score and MTF confirmed"

    if score >= threshold and long_mtf.get("state") == "CONFIRMED" and local_bullish:
        return "LONG", regime, long_mtf, "bullish score and MTF confirmed"

    return None, regime, {"state": "UNCONFIRMED", "reason": "direction not aligned with market"}, "SIDEWAYS_OR_UNCONFIRMED"


def build_market_context(symbol, interval, df, direction):
    regime = current_market_regime()
    mtf = multi_timeframe_quality(symbol, direction, interval, df)
    allowed = True
    reason = "market context accepted"
    if direction == "LONG" and regime in ["DUMP_RISK", "BEARISH", "HIGH_VOLATILITY"]:
        allowed = False
        reason = f"{regime} blocks LONG entries"
    elif direction == "SHORT" and regime == "BULLISH":
        allowed = False
        reason = "BULLISH regime blocks SHORT entries"
    elif mtf.get("strong_conflict"):
        allowed = False
        reason = mtf.get("reason", "strong multi-timeframe conflict")
    return {
        "allowed": allowed,
        "skip_reason": reason,
        "market_regime": regime,
        "multi_timeframe_context": mtf,
    }


def final_signal_score(signal, market_context, sr_targets, mtf_context, reversal_reason):
    regime = market_context.get("market_regime", "SIDEWAYS")
    regime_score = {
        "BULLISH": 18,
        "SIDEWAYS": 13,
        "HIGH_VOLATILITY": 9,
        "BEARISH": 7,
        "DUMP_RISK": 0,
    }.get(regime, 10)
    if signal.get("direction") == "SHORT" and regime in ["BEARISH", "DUMP_RISK", "HIGH_VOLATILITY"]:
        regime_score = max(regime_score, 13)

    trend_power = signal.get("trend_power", "MIXED")
    trend_score = 15 if trend_power in ["STRONG_BULL", "STRONG_BEAR"] else 8 if trend_power == "MIXED" else 6
    sr_score = min(20, int(sr_targets.get("support_strength", 0)) + int(sr_targets.get("resistance_strength", 0)) + 8)
    rr = float(sr_targets.get("risk_reward", 0) or 0)
    rr_score = 15 if rr >= 2.0 else 12 if rr >= 1.8 else 8 if rr >= 1.5 else 0
    volume_score = 10 if signal.get("volume") == "STRONG" else 5
    volatility_state = signal.get("volatility_state", "NORMAL")
    volatility_score = 8 if volatility_state in ["NORMAL", "HEALTHY", "MODERATE", "N/A"] else 5
    mtf_score = int(mtf_context.get("score", 0) or 0)
    setup_type = sr_targets.get("setup_type", "S/R_CONTINUATION")
    penalty = learning_penalty(signal.get("pair"), signal.get("direction"), setup_type)
    final_score = max(0, min(100, regime_score + trend_score + sr_score + rr_score + volume_score + volatility_score + mtf_score - penalty))

    reason = (
        f"{regime} regime; {mtf_context.get('state', 'UNCONFIRMED')} MTF; "
        f"S/R strength {sr_targets.get('support_strength')}/{sr_targets.get('resistance_strength')}; "
        f"RR {rr}; {reversal_reason}; learning penalty {penalty}"
    )
    return {
        "final_score": int(final_score),
        "market_regime": regime,
        "multi_timeframe": mtf_context.get("state", signal.get("multi_timeframe", "N/A")),
        "setup_type": setup_type,
        "learning_penalty": penalty,
        "market_regime_score": regime_score,
        "support_resistance_score": sr_score,
        "risk_reward_score": rr_score,
        "final_score_reason": reason,
        "signal_quality_reason": f"{signal.get('signal_quality_reason', 'S/R validated')} | {reason}",
    }


def candidate_pipeline_log(event, symbol, interval, stage=None, reason=None, signal=None, tier=None):
    try:
        parts = [str(event), f"symbol={symbol}", f"timeframe={interval}"]
        if stage:
            parts.append(f"stage={stage}")
        if tier:
            parts.append(f"tier={tier}")
        if signal:
            parts.append(f"direction={signal.get('direction')}")
            parts.append(f"setup={signal.get('setup_type') or signal.get('strategy_name')}")
            parts.append(f"conf={signal.get('display_confidence', signal.get('confidence'))}")
            parts.append(f"rr={signal.get('risk_reward')}")
        if reason:
            parts.append(f"reason={str(reason)[:180]}")
        print(" ".join(parts))
    except Exception:
        pass


def skip_signal(symbol, interval, reason):
    try:
        _record_scan_rejection(reason)
        key = (symbol, interval, reason)
        now = time.time()
        if now - SIGNAL_SKIP_LOG_CACHE.get(key, 0) >= SIGNAL_SKIP_LOG_TTL_SECONDS:
            SIGNAL_SKIP_LOG_CACHE[key] = now
            print(f"SIGNAL_SKIPPED symbol={symbol} timeframe={interval} reason={reason}")
        LAST_DRY_RUN_SKIPS.append({"symbol": symbol, "timeframe": interval, "skip_reason": reason})
        if len(LAST_DRY_RUN_SKIPS) > 200:
            del LAST_DRY_RUN_SKIPS[:-200]
    except Exception:
        pass
    return None



def _signal_build_key(symbol, interval):
    return (str(symbol or "").upper(), str(interval or "").lower())


def _signal_in_build_cooldown(symbol, interval):
    try:
        key = _signal_build_key(symbol, interval)
        last_seen = SIGNAL_BUILD_COOLDOWN_CACHE.get(key, 0)
        return time.time() - last_seen < SIGNAL_BUILD_COOLDOWN_SECONDS
    except Exception:
        return False


def _mark_signal_built(signal):
    try:
        _scan_diag_inc("candidates_built")
        key = _signal_build_key(signal.get("pair"), signal.get("timeframe"))
        SIGNAL_BUILD_COOLDOWN_CACHE[key] = time.time()
        tier = mark_opportunity_tier(signal)
        print(
            f"SIGNAL_BUILT direction={signal.get('direction')} "
            f"symbol={signal.get('pair')} timeframe={signal.get('timeframe')} tier={tier}"
        )
    except Exception:
        pass


def _selected_signal_summary(signals):
    return [
        {
            "symbol": s.get("pair"),
            "timeframe": s.get("timeframe"),
            "direction": s.get("direction"),
            "display_confidence": s.get("display_confidence", s.get("confidence")),
            "rr": s.get("risk_reward"),
        }
        for s in (signals or [])
    ]


# ================= NEWS FILTER =================
def news_filter():
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()

        titles = [x["title"].lower() for x in data.get("Data", [])[:6]]
        danger = [
            "crash", "hack", "ban", "sec", "regulation",
            "lawsuit", "exploit", "liquidation", "collapse"
        ]

        hits = 0
        for t in titles:
            for k in danger:
                if k in t:
                    hits += 1

        return hits < 4
    except:
        return True


# ================= AI SCORE =================
def ai_score(rsi_val, macd_val, signal_val, trend, volume, smc, trend_power, structure):
    score = 0

    # RSI
    if rsi_val < 32:
        score += 2
    elif rsi_val > 68:
        score -= 2
    elif 45 <= rsi_val <= 58:
        score += 1

    # MACD
    if macd_val > signal_val:
        score += 2
    else:
        score -= 2

    # TREND
    if trend == "UP":
        score += 2
    elif trend == "DOWN":
        score -= 2

    # VOLUME
    if volume == "STRONG":
        score += 2

    # SMC
    if smc == "LIQUIDITY_BREAK_UP":
        score += 2
    elif smc == "LIQUIDITY_BREAK_DOWN":
        score -= 2

    # TREND POWER
    if trend_power == "STRONG_BULL":
        score += 2
    elif trend_power == "STRONG_BEAR":
        score -= 2

    # STRUCTURE
    if structure == "NEAR_BREAKOUT_HIGH":
        score += 1
    elif structure == "NEAR_BREAKOUT_LOW":
        score -= 1

    return score


# ================= SMART TARGET BOOST =================
def smart_target_multiplier(interval, trend_power, volume, structure, direction):
    tp_mult = 1.0
    sl_mult = 1.0

    # ===== Timeframe =====
    if interval == "15m":
        tp_mult += 0.30
        sl_mult += 0.10
    elif interval == "5m":
        tp_mult += 0.10

    # ===== Trend strength =====
    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        tp_mult += 0.35
        sl_mult += 0.10
    elif trend_power == "MIXED":
        tp_mult -= 0.10

    # ===== Volume =====
    if volume == "STRONG":
        tp_mult += 0.25

    # ===== Structure =====
    if direction == "LONG" and structure == "NEAR_BREAKOUT_HIGH":
        tp_mult += 0.20

    if direction == "SHORT" and structure == "NEAR_BREAKOUT_LOW":
        tp_mult += 0.20

    return max(tp_mult, 1.0), max(sl_mult, 0.9)


# ================= SUPPORT / RESISTANCE TARGETS =================
def _cluster_price_levels(raw_levels, tolerance_pct=0.0025, limit=8):
    if not raw_levels:
        return []

    raw_levels = sorted(raw_levels, key=lambda item: item[0])
    clusters = []
    for price, index in raw_levels:
        if price <= 0:
            continue
        if not clusters:
            clusters.append({"prices": [price], "strength": 1, "last_index": index})
            continue

        current = clusters[-1]
        avg_price = sum(current["prices"]) / len(current["prices"])
        tolerance = max(avg_price * tolerance_pct, 1e-12)
        if abs(price - avg_price) <= tolerance:
            current["prices"].append(price)
            current["strength"] += 1
            current["last_index"] = max(current["last_index"], index)
        else:
            clusters.append({"prices": [price], "strength": 1, "last_index": index})

    scored = []
    for cluster in clusters:
        avg_price = sum(cluster["prices"]) / len(cluster["prices"])
        scored.append({
            "price": avg_price,
            "strength": cluster["strength"],
            "last_index": cluster["last_index"],
        })

    scored.sort(key=lambda item: (item["strength"], item["last_index"]), reverse=True)
    return [item["price"] for item in scored[:limit]]


def _cluster_price_level_meta(levels, tolerance_pct=0.0025, limit=8):
    if not levels:
        return []

    sorted_levels = sorted(levels, key=lambda item: item[0])
    clusters = []

    for item in sorted_levels:
        if len(item) >= 4:
            price, index, reaction, volume_confirmation = item[:4]
        elif len(item) >= 3:
            price, index, reaction = item[:3]
            volume_confirmation = False
        else:
            price, index = item[:2]
            reaction = 0
            volume_confirmation = False

        if not clusters:
            clusters.append({
                "prices": [float(price)],
                "indices": [int(index)],
                "reactions": [float(reaction or 0)],
                "volume_hits": 1 if volume_confirmation else 0,
            })
            continue

        current = clusters[-1]
        avg_price = sum(current["prices"]) / len(current["prices"])
        tolerance = max(avg_price * tolerance_pct, 1e-12)
        if abs(float(price) - avg_price) <= tolerance:
            current["prices"].append(float(price))
            current["indices"].append(int(index))
            current["reactions"].append(float(reaction or 0))
            if volume_confirmation:
                current["volume_hits"] += 1
        else:
            clusters.append({
                "prices": [float(price)],
                "indices": [int(index)],
                "reactions": [float(reaction or 0)],
                "volume_hits": 1 if volume_confirmation else 0,
            })

    scored = []
    total_len = max(max((max(c["indices"]) for c in clusters), default=1), 1)
    for cluster in clusters:
        avg_price = sum(cluster["prices"]) / len(cluster["prices"])
        touches = len(cluster["prices"])
        last_seen_index = max(cluster["indices"])
        age = max(total_len - last_seen_index, 0)
        reaction_score = sum(1 for value in cluster["reactions"] if value >= 0.004)
        volume_confirmation = cluster["volume_hits"] > 0
        recency_score = 2 if age <= 35 else 1 if age <= 80 else 0
        strength = touches + reaction_score + recency_score + (1 if volume_confirmation else 0)
        scored.append({
            "price": avg_price,
            "touches": touches,
            "strength": int(strength),
            "last_seen_index": last_seen_index,
            "last_index": last_seen_index,
            "age": age,
            "volume_confirmation": volume_confirmation,
            "reaction_score": reaction_score,
        })

    scored.sort(key=lambda item: (item["strength"], item["touches"], item["last_seen_index"]), reverse=True)
    return scored[:limit]


def calculate_support_resistance(candles):
    try:
        df = candles.tail(220).reset_index(drop=True)
        if len(df) < 50:
            return {"support": [], "resistance": [], "support_meta": [], "resistance_meta": []}

        df = df.copy()
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=["high", "low", "close"], inplace=True)
        df.reset_index(drop=True, inplace=True)
        if len(df) < 50:
            return {"support": [], "resistance": [], "support_meta": [], "resistance_meta": []}

        supports = []
        resistances = []
        lows = df["low"].astype(float).tolist()
        highs = df["high"].astype(float).tolist()
        closes = df["close"].astype(float).tolist()
        volumes = df["volume"].astype(float).fillna(0).tolist()
        volume_ma = df["volume"].rolling(20).mean().fillna(0).tolist()
        atr_series = atr(df).fillna(0).tolist()

        for i in range(3, len(df) - 5):
            low_window = lows[i - 3:i + 4]
            high_window = highs[i - 3:i + 4]
            future_closes = closes[i + 1:i + 6]
            atr_here = float(atr_series[i] or 0)
            vol_ok = bool(volume_ma[i] and volumes[i] >= volume_ma[i] * 1.03)

            if lows[i] == min(low_window) and lows[i] < min(lows[i - 1], lows[i + 1]):
                reaction = 0
                if lows[i] > 0 and future_closes:
                    reaction = (max(future_closes) - lows[i]) / lows[i]
                if atr_here <= 0 or reaction >= max(0.0025, (atr_here / max(lows[i], 1e-12)) * 0.45):
                    supports.append((lows[i], i, reaction, vol_ok))

            if highs[i] == max(high_window) and highs[i] > max(highs[i - 1], highs[i + 1]):
                reaction = 0
                if highs[i] > 0 and future_closes:
                    reaction = (highs[i] - min(future_closes)) / highs[i]
                if atr_here <= 0 or reaction >= max(0.0025, (atr_here / max(highs[i], 1e-12)) * 0.45):
                    resistances.append((highs[i], i, reaction, vol_ok))

        support_meta = _cluster_price_level_meta(supports, tolerance_pct=0.003, limit=10)
        resistance_meta = _cluster_price_level_meta(resistances, tolerance_pct=0.003, limit=10)
        # Sale-ready filter: prefer levels that were touched more than once and reacted recently.
        strong_support = [
            item for item in support_meta
            if item["touches"] >= 2 and item["strength"] >= 4 and item.get("age", 999) <= 150
        ]
        strong_resistance = [
            item for item in resistance_meta
            if item["touches"] >= 2 and item["strength"] >= 4 and item.get("age", 999) <= 150
        ]

        return {
            "support": [item["price"] for item in strong_support],
            "resistance": [item["price"] for item in strong_resistance],
            "support_meta": strong_support,
            "resistance_meta": strong_resistance,
        }
    except Exception as e:
        print(f"calculate_support_resistance error: {e}")
        return {"support": [], "resistance": [], "support_meta": [], "resistance_meta": []}


def nearest_support(price, levels):
    try:
        price = float(price)
        below = [float(level) for level in levels if float(level) < price]
        return max(below) if below else None
    except Exception:
        return None


def nearest_resistance(price, levels):
    try:
        price = float(price)
        above = [float(level) for level in levels if float(level) > price]
        return min(above) if above else None
    except Exception:
        return None


def _level_meta_for_price(price, meta_levels):
    try:
        if price is None:
            return {}
        price = float(price)
        if not meta_levels:
            return {}
        return min(meta_levels, key=lambda item: abs(float(item.get("price", 0)) - price))
    except Exception:
        return {}


def sr_based_targets(candles, entry, direction, atr_value=None, min_rr=2.0):
    try:
        entry = float(entry)
        atr_value = float(atr_value or 0)
    except Exception:
        return None

    levels = calculate_support_resistance(candles)
    supports = sorted([float(level) for level in levels.get("support", []) if float(level) > 0])
    resistances = sorted([float(level) for level in levels.get("resistance", []) if float(level) > 0])
    support = nearest_support(entry, supports)
    resistance = nearest_resistance(entry, resistances)

    if support is None or resistance is None:
        return None

    support_meta = _level_meta_for_price(support, levels.get("support_meta", []))
    resistance_meta = _level_meta_for_price(resistance, levels.get("resistance_meta", []))
    support_strength = int(support_meta.get("strength", 0) or 0)
    resistance_strength = int(resistance_meta.get("strength", 0) or 0)
    if (
        support_strength < 4
        or resistance_strength < 4
        or int(support_meta.get("touches", 0) or 0) < 2
        or int(resistance_meta.get("touches", 0) or 0) < 2
    ):
        return None

    min_target_distance = max(entry * 0.007, atr_value * 0.75 if atr_value > 0 else 0)
    buffer = max(entry * 0.002, atr_value * 0.35 if atr_value > 0 else 0)
    preferred_rr = max(float(min_rr or 2.0), 2.0)
    absolute_min_rr = 1.8

    if direction == "LONG":
        if not (support < entry):
            return None
        sl = support - buffer
        if sl <= 0 or sl >= entry:
            return None
        risk = entry - sl
        candidates = [level for level in resistances if level > entry + min_target_distance]
        tp = None
        rr = None
        preferred_found = False
        for level in candidates:
            reward = level - entry
            current_rr = reward / risk if risk > 0 else 0
            if current_rr >= preferred_rr:
                tp = level
                rr = current_rr
                preferred_found = True
                break
            if tp is None and current_rr >= absolute_min_rr:
                tp = level
                rr = current_rr
        if tp is None:
            return None
    elif direction == "SHORT":
        if not (resistance > entry):
            return None
        sl = resistance + buffer
        if sl <= entry:
            return None
        risk = sl - entry
        candidates = [level for level in reversed(supports) if level < entry - min_target_distance]
        tp = None
        rr = None
        preferred_found = False
        for level in candidates:
            reward = entry - level
            current_rr = reward / risk if risk > 0 else 0
            if current_rr >= preferred_rr:
                tp = level
                rr = current_rr
                preferred_found = True
                break
            if tp is None and current_rr >= absolute_min_rr:
                tp = level
                rr = current_rr
        if tp is None:
            return None
    else:
        return None

    setup_type = "S/R_CONTINUATION" if preferred_found else "S/R_MINIMUM_RR"
    quality = "preferred" if preferred_found else "minimum acceptable"
    return {
        "tp": tp,
        "sl": sl,
        "support": support,
        "resistance": resistance,
        "nearest_support": support,
        "nearest_resistance": resistance,
        "support_strength": support_strength,
        "resistance_strength": resistance_strength,
        "risk_reward": round(rr, 2),
        "target_basis": "Strong Support/Resistance",
        "setup_type": setup_type,
        "signal_quality_reason": (
            f"Strong real S/R validated; support strength {support_strength} "
            f"({int(support_meta.get('touches', 0) or 0)} touches), "
            f"resistance strength {resistance_strength} "
            f"({int(resistance_meta.get('touches', 0) or 0)} touches), "
            f"{quality} RR {round(rr, 2)}"
        ),
    }


def _recent_extension_pct(df, direction, lookback=5):
    try:
        if df is None or len(df) < lookback + 2:
            return 0.0
        entry = float(df["close"].iloc[-1])
        ref = float(df["close"].iloc[-lookback-1])
        if entry <= 0 or ref <= 0:
            return 0.0
        if direction == "LONG":
            return (entry - ref) / ref
        return (ref - entry) / ref
    except Exception:
        return 0.0


def _wick_reversal_warning(df, direction):
    try:
        if df is None or len(df) < 4:
            return False
        recent = df.tail(3)
        warnings = 0
        for _, candle in recent.iterrows():
            high = float(candle["high"])
            low = float(candle["low"])
            open_ = float(candle["open"])
            close = float(candle["close"])
            rng = max(high - low, 1e-12)
            upper = high - max(open_, close)
            lower = min(open_, close) - low
            body = abs(close - open_)
            if direction == "LONG" and upper / rng > 0.42 and body / rng < 0.48:
                warnings += 1
            if direction == "SHORT" and lower / rng > 0.42 and body / rng < 0.48:
                warnings += 1
        return warnings >= 2
    except Exception:
        return False


def _sr_reaction_confirmation(df, direction, support, resistance, atr_value, interval="5m"):
    """Confirm that price is reacting from S/R instead of chasing a finished move."""
    try:
        if df is None or len(df) < 35:
            return False, "not enough candles for S/R reaction confirmation"
        recent = df.tail(8)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = float(last["close"])
        open_ = float(last["open"])
        prev_close = float(prev["close"])
        support = float(support)
        resistance = float(resistance)
        atr_value = float(atr_value) if atr_value is not None and not pd.isna(atr_value) else 0.0
        if close <= 0 or support <= 0 or resistance <= 0 or atr_value <= 0:
            return False, "invalid S/R reaction inputs"

        ema20 = float(ema(df, 20).iloc[-1])
        ema50 = float(ema(df, 50).iloc[-1])
        rsi_series = rsi(df)
        rsi_now = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0

        touch_buffer = max(atr_value * 0.55, close * {"5m": 0.0035, "15m": 0.0055, "1h": 0.009}.get(interval, 0.005))
        reclaim_buffer = max(atr_value * 0.18, close * 0.0015)

        if direction == "LONG":
            touched_support = float(recent["low"].min()) <= support + touch_buffer
            reclaimed = close > support + reclaim_buffer and close >= prev_close
            candle_ok = close > open_ or close > ema20
            trend_ok = close >= ema20 * 0.996 and ema20 >= ema50 * 0.992
            rsi_ok = 42 <= rsi_now <= 68
            if not touched_support:
                return False, "LONG skipped: no fresh support touch/retest"
            if not reclaimed:
                return False, "LONG skipped: support not reclaimed yet"
            if not candle_ok:
                return False, "LONG skipped: weak reaction candle"
            if not trend_ok:
                return False, "LONG skipped: EMA structure not supportive"
            if not rsi_ok:
                return False, f"LONG skipped: RSI {round(rsi_now, 1)} not in safe rebound zone"
            return True, "LONG confirmed by support retest, reclaim, EMA and RSI"

        if direction == "SHORT":
            touched_resistance = float(recent["high"].max()) >= resistance - touch_buffer
            rejected = close < resistance - reclaim_buffer and close <= prev_close
            candle_ok = close < open_ or close < ema20
            trend_ok = close <= ema20 * 1.004 and ema20 <= ema50 * 1.008
            rsi_ok = 32 <= rsi_now <= 58
            if not touched_resistance:
                return False, "SHORT skipped: no fresh resistance touch/retest"
            if not rejected:
                return False, "SHORT skipped: resistance not rejected yet"
            if not candle_ok:
                return False, "SHORT skipped: weak rejection candle"
            if not trend_ok:
                return False, "SHORT skipped: EMA structure not supportive"
            if not rsi_ok:
                return False, f"SHORT skipped: RSI {round(rsi_now, 1)} not in safe rejection zone"
            return True, "SHORT confirmed by resistance retest, rejection, EMA and RSI"

        return False, "unknown direction"
    except Exception as e:
        return False, f"S/R reaction confirmation error: {e}"


def _entry_location_filter(df, direction, sr_targets, atr_value, interval="5m"):
    """Reject entries that are late in the move or too close to the next opposing level."""
    try:
        entry = float(df["close"].iloc[-1])
        support = float(sr_targets.get("support") or sr_targets.get("nearest_support"))
        resistance = float(sr_targets.get("resistance") or sr_targets.get("nearest_resistance"))
        if entry <= 0 or support <= 0 or resistance <= 0 or resistance <= support:
            return False, "invalid support/resistance range"
        rng = resistance - support
        pos = (entry - support) / rng
        atr_value = float(atr_value) if atr_value is not None and not pd.isna(atr_value) else 0.0
        atr_ratio = atr_value / entry if entry else 0.0
        extension_limit = {"5m": 0.0085, "15m": 0.014, "1h": 0.022}.get(interval, 0.012)
        extension = _recent_extension_pct(df, direction, lookback=5)

        if direction == "LONG":
            # The bot must buy near a confirmed support/reclaim, not after the move is almost finished.
            max_support_distance = max(0.006, atr_ratio * 1.15)
            if pos > 0.34:
                return False, f"late LONG entry: price already {round(pos*100, 1)}% through S/R range"
            if (entry - support) / entry > max_support_distance:
                return False, "LONG entry too far from confirmed support"
            if (resistance - entry) / entry < max(0.012, atr_ratio * 1.35):
                return False, "LONG entry too close to resistance"
            if extension > extension_limit * 0.75:
                return False, f"late LONG pump extension {round(extension*100, 2)}%"
            if _wick_reversal_warning(df, direction):
                return False, "LONG rejected by upper-wick exhaustion"
        else:
            # The bot must short near resistance, not after most of the dump has already happened.
            max_resistance_distance = max(0.006, atr_ratio * 1.15)
            if pos < 0.66:
                return False, f"late SHORT entry: price already near support ({round(pos*100, 1)}% range position)"
            if (resistance - entry) / entry > max_resistance_distance:
                return False, "SHORT entry too far from confirmed resistance"
            if (entry - support) / entry < max(0.012, atr_ratio * 1.35):
                return False, "SHORT entry too close to support"
            if extension > extension_limit * 0.75:
                return False, f"late SHORT dump extension {round(extension*100, 2)}%"
            if _wick_reversal_warning(df, direction):
                return False, "SHORT rejected by lower-wick exhaustion"

        reaction_ok, reaction_reason = _sr_reaction_confirmation(df, direction, support, resistance, atr_value, interval)
        if not reaction_ok:
            return False, reaction_reason

        return True, f"entry protected by S/R location and reaction: {reaction_reason}"
    except Exception as e:
        return False, f"entry location filter error: {e}"


def _market_direction_guard(direction, market_context, mtf_context):
    """Hard guard: only trade with a clear confirmed market regime."""
    regime = market_context.get("market_regime", "SIDEWAYS")
    mtf_state = mtf_context.get("state", "UNCONFIRMED")
    if mtf_state != "CONFIRMED":
        return False, "SIDEWAYS_OR_UNCONFIRMED"
    if regime in ["SIDEWAYS", "HIGH_VOLATILITY"]:
        return False, "SIDEWAYS_OR_UNCONFIRMED"
    if direction == "LONG" and regime != "BULLISH":
        return False, f"{regime} blocks LONG entries"
    if direction == "SHORT" and regime not in ["BEARISH", "DUMP_RISK"]:
        return False, f"{regime} blocks SHORT entries"
    return True, "market direction confirmed"


# ================= TP / SL =================
def dynamic_targets(entry, direction, atr_value, trend_power="MIXED", volume="WEAK", timeframe="5m", structure="MID_RANGE"):
    try:
        entry = float(entry)
        atr_value = float(atr_value) if atr_value is not None else 0
    except:
        atr_value = 0

    if entry <= 0:
        return None, None

    # ================= BASE MIN TARGETS =================
    if timeframe == "15m":
        min_tp_percent = 0.0115
        min_sl_percent = 0.0048
        atr_tp_multiplier = 2.9
        atr_sl_multiplier = 1.15
    elif timeframe == "1h":
        min_tp_percent = 0.016
        min_sl_percent = 0.0065
        atr_tp_multiplier = 3.4
        atr_sl_multiplier = 1.3
    else:  # 5m
        min_tp_percent = 0.0085
        min_sl_percent = 0.0038
        atr_tp_multiplier = 2.4
        atr_sl_multiplier = 0.95

    # ================= BOOSTS =================
    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        min_tp_percent += 0.0025
        atr_tp_multiplier += 0.5

    if volume == "STRONG":
        min_tp_percent += 0.002
        atr_tp_multiplier += 0.4

    # ================= LOW PRICE COIN PROTECTION =================
    if entry < 1:
        min_tp_percent += 0.004
        min_sl_percent += 0.0012

    if entry < 0.1:
        min_tp_percent += 0.004
        min_sl_percent += 0.0012

    # ================= SMART TARGET SYSTEM =================
    extra_tp_mult, extra_sl_mult = smart_target_multiplier(
        timeframe, trend_power, volume, structure, direction
    )

    atr_tp_multiplier *= extra_tp_mult
    atr_sl_multiplier *= extra_sl_mult

    # ================= ATR MOVE =================
    if pd.isna(atr_value) or atr_value <= 0:
        atr_based_tp = entry * min_tp_percent
        atr_based_sl = entry * min_sl_percent
    else:
        atr_based_tp = atr_value * atr_tp_multiplier
        atr_based_sl = atr_value * atr_sl_multiplier

    # ================= FINAL ENFORCED DISTANCE =================
    tp_move = max(atr_based_tp, entry * min_tp_percent)
    sl_move = max(atr_based_sl, entry * min_sl_percent)

    # ================= RR ENFORCEMENT =================
    min_rr_tp = sl_move * 2.0
    tp_move = max(tp_move, min_rr_tp)

    # ================= ANTI-TINY TARGETS =================
    if entry < 0.1:
        tp_move = max(tp_move, entry * 0.015)
        sl_move = max(sl_move, entry * 0.006)
    elif entry < 1:
        tp_move = max(tp_move, entry * 0.012)
        sl_move = max(sl_move, entry * 0.005)
    elif entry < 100:
        tp_move = max(tp_move, entry * 0.0085)
        sl_move = max(sl_move, entry * 0.0038)
    else:
        tp_move = max(tp_move, entry * 0.007)
        sl_move = max(sl_move, entry * 0.0033)

    # ================= FINAL LEVELS =================
    if direction == "LONG":
        tp = entry + tp_move
        sl = entry - sl_move
    else:
        tp = entry - tp_move
        sl = entry + sl_move

    return tp, sl


# ================= CONFIDENCE =================
def calculate_confidence(score, volume, smc, trend_power, structure, momentum_ok=False, htf_ok=False):
    """
    Confidence واقعي:
    - المتوسط يبقى 60~72
    - القوي 73~82
    - النادر جدًا 83~88
    - بدون أرقام مبالغ فيها
    """

    confidence = 52

    # ================= SCORE CORE =================
    confidence += abs(score) * 2.2

    # ================= VOLUME =================
    if volume == "STRONG":
        confidence += 5
    else:
        confidence -= 4

    # ================= SMART MONEY =================
    if smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
        confidence += 6
    elif smc == "RANGE":
        confidence -= 6
    else:
        confidence -= 2

    # ================= TREND POWER =================
    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        confidence += 6
    elif trend_power == "MIXED":
        confidence -= 7

    # ================= STRUCTURE =================
    if structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        confidence += 5
    elif structure == "MID_RANGE":
        confidence -= 5
    elif structure == "UNKNOWN":
        confidence -= 3

    # ================= MOMENTUM =================
    if momentum_ok:
        confidence += 5
    else:
        confidence -= 5

    # ================= HTF =================
    if htf_ok:
        confidence += 6
    else:
        confidence -= 6

    confidence = int(round(confidence))

    # ================= HARD REALISTIC CAP =================
    if confidence >= 89:
        confidence = 88

    if confidence < 48:
        confidence = 48

    return confidence


# ================= PRICE FORMAT =================
def format_price(price):
    try:
        price = float(price)

        if price >= 1000:
            return round(price, 2)
        elif price >= 100:
            return round(price, 3)
        elif price >= 1:
            return round(price, 4)
        elif price >= 0.1:
            return round(price, 5)
        elif price >= 0.01:
            return round(price, 6)
        elif price >= 0.001:
            return round(price, 7)
        else:
            return round(price, 8)
    except:
        return price


# ================= SIGNAL VALIDATION =================
def signal_levels_valid(entry, tp, sl, direction):
    try:
        entry = float(entry)
        tp = float(tp)
        sl = float(sl)

        if entry <= 0 or tp <= 0 or sl <= 0:
            return False

        if direction == "LONG":
            if not (tp > entry and sl < entry):
                return False

            reward = tp - entry
            risk = entry - sl

        elif direction == "SHORT":
            if not (tp < entry and sl > entry):
                return False

            reward = entry - tp
            risk = sl - entry
        else:
            return False

        if reward <= 0 or risk <= 0:
            return False

        # ===== Minimum distance حسب نوع العملة =====
        if entry < 0.1:
            min_reward = entry * 0.015
            min_risk = entry * 0.006
        elif entry < 1:
            min_reward = entry * 0.012
            min_risk = entry * 0.005
        elif entry < 10:
            min_reward = entry * 0.009
            min_risk = entry * 0.0042
        elif entry < 100:
            min_reward = entry * 0.008
            min_risk = entry * 0.0036
        else:
            min_reward = entry * 0.007
            min_risk = entry * 0.003

        if reward < min_reward or risk < min_risk:
            return False

        rr = reward / risk
        if rr < 1.8:
            return False

        return True
    except:
        return False


# ================= ADAPTIVE EXPERT SIGNAL ENGINE =================
def _safe_float(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _bounded(value, low=0, high=100):
    return max(low, min(high, value))


def closed_candle_frame(df):
    """Return only closed candles; when no explicit flag exists, skip the live tail."""
    try:
        if df is None or len(df) == 0:
            return df
        frame = df.copy()
        for col in ("complete", "closed", "is_closed"):
            if col in frame.columns:
                return frame[frame[col].astype(bool)].copy()
        if len(frame) > 8:
            return frame.iloc[:-1].copy()
        return frame.copy()
    except Exception:
        return df


def recent_closed_candles(df, count=3):
    try:
        frame = closed_candle_frame(df)
        if frame is None:
            return frame
        return frame.tail(count).copy()
    except Exception:
        return df.tail(count) if df is not None else df


def build_signal_quality_report(signal):
    try:
        confidence = _safe_float(signal.get("confidence"), 0)
        volume_score = _safe_float(signal.get("volume_score"), 50)
        risk_score = _safe_float(signal.get("risk_score"), 50)
        mtf_score = _safe_float(signal.get("multi_timeframe_score"), 50)
        rr = _safe_float(signal.get("risk_reward"), 0)
        volume_state = str(signal.get("volume_state") or "").upper()
        risk_level = str(signal.get("risk_level") or ("LOW" if risk_score <= 35 else "MEDIUM" if risk_score <= 60 else "HIGH")).upper()
        mtf_state = str(signal.get("multi_timeframe") or "").upper()
        volume_label = signal.get("volume_state") or signal.get("volume") or "UNKNOWN"

        if rr < 1.5:
            return None, f"RR {round(rr, 2)} below 1.5"

        rr_score = 95 if rr >= 2.4 else 88 if rr >= 2.0 else 80 if rr >= 1.8 else 72
        risk_component = max(0, 100 - risk_score)
        final_score = (
            confidence * 0.34
            + volume_score * 0.18
            + risk_component * 0.20
            + mtf_score * 0.16
            + rr_score * 0.12
        )
        final_score = int(round(_bounded(final_score, 0, 100)))

        display_confidence = int(round(confidence * 0.70 + final_score * 0.30))
        cap = 94
        cap_reason = "none"
        thin_volume = volume_state == "THIN" or volume_score < 45
        high_risk = risk_level == "HIGH"

        if thin_volume and high_risk:
            cap = 68
            cap_reason = "thin_volume_high_risk"
        elif high_risk:
            cap = 72
            cap_reason = "high_risk"
        elif thin_volume:
            cap = 78
            cap_reason = "thin_volume"

        strong_volume = volume_state in ["STRONG", "EXPANSION"] or volume_score >= 72
        confirmed_mtf = mtf_state in ["CONFIRMED", "STACKED_CONFIRMATION"] or mtf_score >= 68
        excellent_rr = rr >= 2.2
        low_or_medium_risk = risk_level in ["LOW", "MEDIUM"]
        if not (strong_volume and low_or_medium_risk and confirmed_mtf and excellent_rr):
            cap = min(cap, 94)
            if cap_reason == "none":
                cap_reason = "95_plus_requires_volume_risk_mtf_rr"

        display_confidence = int(_bounded(min(display_confidence, cap), 1, 99))
        report = {
            "display_confidence": display_confidence,
            "final_score": final_score,
            "risk_level": risk_level,
            "volume_gate": volume_label,
            "confidence_cap_reason": cap_reason,
        }
        return report, None
    except Exception as e:
        return None, f"quality report error: {e}"


def apply_signal_quality_report(signal):
    report, reason = build_signal_quality_report(signal)
    if not report:
        return False, reason
    signal["quality_report"] = report
    signal["display_confidence"] = report["display_confidence"]
    signal["final_score"] = report["final_score"]
    signal["risk_level"] = report["risk_level"]
    signal["volume_gate"] = report["volume_gate"]
    signal["confidence_cap_reason"] = report["confidence_cap_reason"]
    print(
        f"SIGNAL_QUALITY pair={signal.get('pair')} display_conf={report['display_confidence']} "
        f"final={report['final_score']} risk={report['risk_level']} "
        f"volume={report['volume_gate']} cap={report['confidence_cap_reason']}"
    )
    return True, None


def _recent_closed_trades(limit=120):
    try:
        path = os.path.join(os.path.dirname(__file__), "trades.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        return [t for t in rows if str(t.get("status", "")).upper() in ["TP", "SL"]][-limit:]
    except Exception:
        return []


def _performance_bucket(rows, key, value):
    sample = [t for t in rows if str(t.get(key) or "").upper() == str(value or "").upper()]
    if not sample:
        return 50.0, 0
    wins = sum(1 for t in sample if str(t.get("status", "")).upper() == "TP")
    return round((wins / len(sample)) * 100, 2), len(sample)


def statistical_learning_summary(rows):
    try:
        if len(rows) < 100:
            return {"ready": False, "trades": len(rows)}

        def bucket(key):
            groups = {}
            for row in rows:
                value = str(row.get(key) or "UNKNOWN").upper()
                groups.setdefault(value, {"trades": 0, "wins": 0})
                groups[value]["trades"] += 1
                if str(row.get("status", "")).upper() == "TP":
                    groups[value]["wins"] += 1
            scored = []
            for value, data in groups.items():
                if data["trades"] < 4:
                    continue
                win_rate = round((data["wins"] / data["trades"]) * 100, 2)
                scored.append((value, win_rate, data["trades"]))
            if not scored:
                return None, None
            scored.sort(key=lambda item: (item[1], item[2]))
            return scored[-1], scored[0]

        summary = {"ready": True, "trades": len(rows)}
        for label, key in [
            ("strategy", "strategy_name"),
            ("symbol", "pair"),
            ("timeframe", "timeframe"),
            ("session", "session"),
            ("regime", "market_regime"),
        ]:
            best, worst = bucket(key)
            summary[f"best_{label}"] = best
            summary[f"worst_{label}"] = worst
        return summary
    except Exception as e:
        return {"ready": False, "trades": len(rows), "error": str(e)}


def adaptive_learning_weight(strategy_name, symbol, timeframe, direction):
    try:
        rows = _recent_closed_trades()
        if not rows:
            return 0, "no recent closed trades"

        strategy_wr, strategy_trades = _performance_bucket(rows, "strategy_name", strategy_name)
        symbol_wr, symbol_trades = _performance_bucket(rows, "pair", symbol)
        timeframe_wr, timeframe_trades = _performance_bucket(rows, "timeframe", timeframe)
        direction_wr, direction_trades = _performance_bucket(rows, "direction", direction)

        adjustment = 0
        for wr, trades, weight in [
            (strategy_wr, strategy_trades, 5),
            (symbol_wr, symbol_trades, 4),
            (timeframe_wr, timeframe_trades, 3),
            (direction_wr, direction_trades, 3),
        ]:
            if trades < 4:
                continue
            if wr >= 62:
                adjustment += weight
            elif wr <= 42:
                adjustment -= weight

        adjustment = max(-15, min(15, adjustment))
        print(f"STRATEGY_PERFORMANCE strategy={strategy_name} win_rate={strategy_wr} trades={strategy_trades}")
        stats = statistical_learning_summary(rows)
        if stats.get("ready"):
            print(
                "STATISTICAL_LEARNING "
                f"trades={stats.get('trades')} "
                f"best_strategy={stats.get('best_strategy')} worst_strategy={stats.get('worst_strategy')} "
                f"best_symbol={stats.get('best_symbol')} worst_symbol={stats.get('worst_symbol')} "
                f"best_timeframe={stats.get('best_timeframe')} best_session={stats.get('best_session')} "
                f"best_regime={stats.get('best_regime')}"
            )
        print(f"LEARNING_WEIGHT strategy={strategy_name} symbol={symbol} timeframe={timeframe} adjustment={adjustment}")
        return adjustment, f"learning adjustment {adjustment}; strategy WR {strategy_wr}% over {strategy_trades}"
    except Exception as e:
        print(f"LEARNING_WEIGHT strategy={strategy_name} symbol={symbol} timeframe={timeframe} adjustment=0 error={e}")
        return 0, "learning unavailable"


def _expert_tf_direction(df):
    try:
        if df is None or len(df) < 80:
            return "UNKNOWN"
        close = _safe_float(df["close"].iloc[-1])
        ema20v = _safe_float(ema(df, 20).iloc[-1])
        ema50v = _safe_float(ema(df, 50).iloc[-1])
        ema200v = _safe_float(ema(df, 200).iloc[-1] if len(df) >= 200 else ema(df, 100).iloc[-1])
        rsi_now = _safe_float(rsi(df).iloc[-1], 50)
        if close <= 0 or min(ema20v, ema50v, ema200v) <= 0:
            return "UNKNOWN"
        if ema20v > ema50v > ema200v and close > ema50v and rsi_now >= 48:
            return "BULL"
        if ema20v < ema50v < ema200v and close < ema50v and rsi_now <= 52:
            return "BEAR"
        return "RANGE"
    except Exception:
        return "UNKNOWN"


def expert_multi_timeframe_context(symbol, direction, current_df=None):
    frames = {}
    try:
        for tf in ["4h", "1h", FUTURES_SETUP_TIMEFRAME, FUTURES_TRIGGER_TIMEFRAME]:
            df = current_df if tf == FUTURES_TRIGGER_TIMEFRAME and current_df is not None else cached_market_data(symbol, tf, 220)
            frames[tf] = {
                "direction": _expert_tf_direction(df),
                "available": df is not None and len(df) >= 80,
            }
        major = frames["4h"]["direction"]
        confirm = frames["1h"]["direction"]
        desired = "BULL" if direction == "LONG" else "BEAR"
        if major == "UNKNOWN" or confirm == "UNKNOWN":
            return {"state": "UNCONFIRMED", "score": 0, "reason": "4H/1H data unavailable", "frames": frames}
        if major != confirm:
            return {"state": "CONFLICT", "score": 0, "reason": f"4H {major} conflicts with 1H {confirm}", "frames": frames}
        if major != desired:
            return {"state": "CONFLICT", "score": 0, "reason": f"4H/1H {major} does not support {direction}", "frames": frames}

        score = 60
        if frames.get(FUTURES_TRIGGER_TIMEFRAME, {}).get("direction") in [desired, "RANGE"]:
            score += 20
        if frames.get(FUTURES_SETUP_TIMEFRAME, {}).get("direction") in [desired, "RANGE"]:
            score += 10
        state = "CONFIRMED" if score >= 80 else "PARTIAL"
        return {"state": state, "score": min(score, 100), "reason": f"4H main trend and 1H confirmation support {direction}", "frames": frames}
    except Exception as e:
        return {"state": "UNCONFIRMED", "score": 0, "reason": f"expert MTF error: {e}", "frames": frames}


def expert_session_state():
    try:
        now = datetime.utcnow()
        hour = now.hour + (now.minute / 60)
        if 13 <= hour < 16.5:
            return {"session": "LONDON_NEW_YORK_OVERLAP", "tradable": True, "quality_bonus": 8}
        if 7 <= hour < 16:
            return {"session": "LONDON", "tradable": True, "quality_bonus": 4}
        if 16.5 <= hour < 21:
            return {"session": "NEW_YORK_LATE", "tradable": False, "quality_bonus": -8}
        return {"session": "OFF_SESSION", "tradable": False, "quality_bonus": -12}
    except Exception:
        return {"session": "UNKNOWN", "tradable": False, "quality_bonus": -10}


def high_impact_news_guard():
    try:
        manual_flag = os.environ.get("HIGH_IMPACT_NEWS_ACTIVE", "").strip().lower() in {"1", "true", "yes", "on"}
        until = os.environ.get("HIGH_IMPACT_NEWS_UNTIL", "").strip()
        if manual_flag:
            return False, "HIGH_NEWS_RISK manual blackout active"
        if until:
            try:
                clean_until = until.replace("Z", "+00:00")
                until_dt = datetime.fromisoformat(clean_until)
                if until_dt.tzinfo is not None:
                    until_dt = until_dt.replace(tzinfo=None)
                if datetime.utcnow() <= until_dt:
                    return False, "HIGH_NEWS_RISK active until configured time"
            except Exception:
                return False, "HIGH_NEWS_RISK invalid HIGH_IMPACT_NEWS_UNTIL configuration"
        return True, "no high impact news blackout configured"
    except Exception as e:
        return False, f"HIGH_NEWS_RISK guard error: {e}"


def expert_volatility_state(df):
    try:
        if df is None or len(df) < 80:
            return {"state": "LOW_LIQUIDITY", "ok": False, "reason": "insufficient candles"}
        close = _safe_float(df["close"].iloc[-1])
        atr_series = atr(df).dropna()
        if close <= 0 or len(atr_series) < 30:
            return {"state": "LOW_VOLATILITY", "ok": False, "reason": "insufficient ATR history"}
        atr_val = _safe_float(atr_series.iloc[-1])
        atr_avg = _safe_float(atr_series.tail(60).mean(), atr_val)
        atr_ratio = atr_val / close if close > 0 else 0
        relative = atr_val / atr_avg if atr_avg > 0 else 0
        if atr_ratio < 0.0018 or relative < 0.55:
            return {"state": "LOW_VOLATILITY", "ok": False, "reason": f"ATR too low ratio={round(atr_ratio, 5)} relative={round(relative, 2)}"}
        if atr_ratio > 0.045 or relative > 2.25:
            return {"state": "HIGH_VOLATILITY", "ok": False, "reason": f"ATR too high ratio={round(atr_ratio, 5)} relative={round(relative, 2)}"}
        return {"state": "NORMAL_VOLATILITY", "ok": True, "reason": f"ATR tradable ratio={round(atr_ratio, 5)} relative={round(relative, 2)}"}
    except Exception as e:
        return {"state": "VOLATILITY_ERROR", "ok": False, "reason": str(e)}


def trend_exhaustion_filter(df, direction):
    try:
        if df is None or len(df) < 50:
            return False, "insufficient exhaustion history"
        close = _safe_float(df["close"].iloc[-1])
        avg_candle_move = float(df["close"].pct_change().abs().tail(40).mean() or 0)
        if close <= 0 or avg_candle_move <= 0:
            return False, "invalid exhaustion baseline"
        recent_move = abs(close - _safe_float(df["close"].iloc[-6])) / close
        expected_move = avg_candle_move * 6
        if expected_move > 0 and recent_move > expected_move * 0.80:
            return True, f"trend exhaustion: recent move used {round((recent_move / expected_move) * 100, 1)}% of average move"
        last = df.iloc[-1]
        candle_range = max(_safe_float(last["high"]) - _safe_float(last["low"]), close * 0.0001)
        upper_wick = _safe_float(last["high"]) - max(_safe_float(last["open"]), _safe_float(last["close"]))
        lower_wick = min(_safe_float(last["open"]), _safe_float(last["close"])) - _safe_float(last["low"])
        if direction == "LONG" and upper_wick / candle_range > 0.55:
            return True, "LONG exhaustion upper wick"
        if direction == "SHORT" and lower_wick / candle_range > 0.55:
            return True, "SHORT exhaustion lower wick"
        return False, "not exhausted"
    except Exception as e:
        return True, f"exhaustion filter error: {e}"


def smart_money_entry_zone(df, direction, regime_info):
    try:
        close = _safe_float(regime_info.get("close"))
        atr_val = max(_safe_float(regime_info.get("atr")), close * 0.003 if close else 0.0)
        support = regime_info.get("support")
        resistance = regime_info.get("resistance")
        recent_high = _safe_float(regime_info.get("recent_high"))
        recent_low = _safe_float(regime_info.get("recent_low"))
        if close <= 0 or atr_val <= 0:
            return {"ok": False, "setup": None, "reason": "invalid smart-money baseline"}

        closed_df = closed_candle_frame(df)
        if closed_df is None or len(closed_df) < 5:
            return {"ok": False, "setup": None, "reason": "insufficient closed candles for entry confirmation"}
        mid_range = recent_low + ((recent_high - recent_low) * 0.5) if recent_high > recent_low else close
        recent = list(reversed(range(max(1, len(closed_df) - 3), len(closed_df))))
        for idx in recent:
            age = (len(closed_df) - 1) - idx
            last = closed_df.iloc[idx]
            prev = closed_df.iloc[idx - 1]
            candle_close = _safe_float(last["close"])
            candle_range = max(_safe_float(last["high"]) - _safe_float(last["low"]), candle_close * 0.0001)
            upper_wick_ratio = (_safe_float(last["high"]) - max(_safe_float(last["open"]), _safe_float(last["close"]))) / candle_range
            lower_wick_ratio = (min(_safe_float(last["open"]), _safe_float(last["close"])) - _safe_float(last["low"])) / candle_range
            fvg_long = idx >= 2 and _safe_float(closed_df["low"].iloc[idx]) > _safe_float(closed_df["high"].iloc[idx - 2])
            fvg_short = idx >= 2 and _safe_float(closed_df["high"].iloc[idx]) < _safe_float(closed_df["low"].iloc[idx - 2])
            age_note = f"; entry_confirmation_age_candles={age}"

            if direction == "LONG":
                if support and abs(candle_close - support) <= max(atr_val * 0.85, candle_close * 0.007):
                    return {"ok": True, "setup": "Bounce from Support", "reason": "recent closed candle bounced from support with defined invalidation" + age_note, "entry_confirmation_age_candles": age}
                if lower_wick_ratio >= 0.45 and _safe_float(last["low"]) < recent_low and candle_close > recent_low:
                    return {"ok": True, "setup": "Liquidity Sweep", "reason": "recent sell-side liquidity swept and reclaimed" + age_note, "entry_confirmation_age_candles": age}
                if _safe_float(prev["high"]) < candle_close and _safe_float(last["low"]) <= _safe_float(prev["high"]) + atr_val * 0.25:
                    return {"ok": True, "setup": "Break + Retest", "reason": "recent breakout retested prior high" + age_note, "entry_confirmation_age_candles": age}
                if fvg_long and candle_close <= mid_range:
                    return {"ok": True, "setup": "Fair Value Gap", "reason": "recent bullish imbalance inside discount area" + age_note, "entry_confirmation_age_candles": age}
                if candle_close <= mid_range and regime_info.get("regime") in ["ACCUMULATION", "WEAK_BULL", "STRONG_BULL"]:
                    return {"ok": True, "setup": "Discount Pullback", "reason": "recent pullback in discount relative to range" + age_note, "entry_confirmation_age_candles": age}
            else:
                if resistance and abs(resistance - candle_close) <= max(atr_val * 0.85, candle_close * 0.007):
                    return {"ok": True, "setup": "Bounce from Resistance", "reason": "recent closed candle rejected resistance with defined invalidation" + age_note, "entry_confirmation_age_candles": age}
                if upper_wick_ratio >= 0.45 and _safe_float(last["high"]) > recent_high and candle_close < recent_high:
                    return {"ok": True, "setup": "Liquidity Sweep", "reason": "recent buy-side liquidity swept and rejected" + age_note, "entry_confirmation_age_candles": age}
                if _safe_float(prev["low"]) > candle_close and _safe_float(last["high"]) >= _safe_float(prev["low"]) - atr_val * 0.25:
                    return {"ok": True, "setup": "Break + Retest", "reason": "recent breakdown retested prior low" + age_note, "entry_confirmation_age_candles": age}
                if fvg_short and candle_close >= mid_range:
                    return {"ok": True, "setup": "Fair Value Gap", "reason": "recent bearish imbalance inside premium area" + age_note, "entry_confirmation_age_candles": age}
                if candle_close >= mid_range and regime_info.get("regime") in ["DISTRIBUTION", "WEAK_BEAR", "STRONG_BEAR"]:
                    return {"ok": True, "setup": "Premium Pullback", "reason": "recent pullback in premium relative to range" + age_note, "entry_confirmation_age_candles": age}
        return {"ok": False, "setup": None, "reason": "no retest, pullback, liquidity sweep, order block, FVG, or S/R bounce"}
    except Exception as e:
        return {"ok": False, "setup": None, "reason": f"smart money filter error: {e}"}


def late_entry_after_confirmation_guard(df, direction, regime_info, smart_entry):
    try:
        age = int(smart_entry.get("entry_confirmation_age_candles"))
        if age not in {0, 1, 2}:
            return False, "ENTRY_STALE: entry confirmation outside 0-2 closed candle window"
        closed_df = closed_candle_frame(df)
        if closed_df is None or len(closed_df) < age + 2:
            return False, "ENTRY_STALE: insufficient closed candles after confirmation"
        latest_close = _safe_float(closed_df["close"].iloc[-1])
        confirmation_close = _safe_float(closed_df["close"].iloc[-1 - age])
        atr_val = max(_safe_float(regime_info.get("atr")), latest_close * 0.003 if latest_close else 0.0)
        if latest_close <= 0 or confirmation_close <= 0 or atr_val <= 0:
            return False, "ENTRY_STALE: invalid late-entry baseline"
        max_chase = max(atr_val * 0.75, latest_close * 0.006)
        directional_move = latest_close - confirmation_close if direction == "LONG" else confirmation_close - latest_close
        if directional_move > max_chase:
            return False, (
                "LATE_ENTRY: price moved too far after confirmation "
                f"move={round(directional_move, 8)} max_allowed={round(max_chase, 8)} "
                f"age={age}"
            )
        return True, f"entry timing valid age={age} move={round(directional_move, 8)}"
    except Exception as e:
        return False, f"LATE_ENTRY guard error: {e}"


def expert_quality_checklist(signal, regime_info, expert_context):
    checks = []
    def add(name, passed, reason):
        checks.append({"name": name, "passed": bool(passed), "reason": reason})

    mtf = expert_context.get("mtf", {})
    volatility = expert_context.get("volatility", {})
    session = expert_context.get("session", {})
    smart = expert_context.get("smart_money", {})
    news_ok = expert_context.get("news_ok", False)
    rr = _safe_float(signal.get("risk_reward"))
    display_conf = _safe_float(signal.get("display_confidence", signal.get("confidence")))
    volume_score = _safe_float(signal.get("volume_score", regime_info.get("volume_score", 0)))
    risk_score = _safe_float(signal.get("risk_score", 100))
    regime = str(signal.get("market_regime") or regime_info.get("regime") or "")

    add("Trend", regime in ["STRONG_BULL", "WEAK_BULL", "STRONG_BEAR", "WEAK_BEAR", "EXPANSION", "ACCUMULATION", "DISTRIBUTION", "BREAKOUT", "REVERSAL", "RANGE"], regime)
    add("Momentum", display_conf >= 70 or signal.get("b_plus_calibrated") is True, f"display confidence {display_conf}")
    add("Volume", volume_score >= 50, f"volume score {volume_score}")
    add("Liquidity", regime not in ["LOW_LIQUIDITY", "LOW_VOLUME_CHOP"], regime)
    add("Volatility", volatility.get("ok") is True, volatility.get("reason"))
    add("MTF", mtf.get("state") == "CONFIRMED", mtf.get("reason"))
    add("Risk", risk_score < 78, f"risk score {risk_score}")
    add("RR", rr >= 1.5, f"RR {rr}")
    add("Entry", smart.get("ok") is True, smart.get("reason"))
    add("Structure", smart.get("ok") is True or (bool(signal.get("structure")) and str(signal.get("structure")) != "MID_RANGE"), signal.get("structure"))
    add("Session", session.get("tradable") is True or display_conf >= 94, session.get("session"))
    add("News", news_ok is True, expert_context.get("news_reason"))

    passed = sum(1 for item in checks if item["passed"])
    percent = round((passed / len(checks)) * 100, 2) if checks else 0
    failed = [item for item in checks if not item["passed"]]
    return {
        "passed": passed,
        "total": len(checks),
        "percent": percent,
        "failed": failed,
        "checks": checks,
    }


def expert_self_review(signal, checklist):
    try:
        if checklist.get("percent", 0) < EXPERT_QUALITY_MIN_PERCENT and signal.get("supply_calibrated") is not True:
            return False, "Would I risk my own money? No - checklist below fund-manager standard"
        if signal.get("supply_calibrated") is True and checklist.get("percent", 0) < 83:
            return False, "Would I risk my own money? No - calibrated checklist below B+ minimum"
        if _safe_float(signal.get("risk_score"), 100) >= 78:
            return False, "Would I risk my own money? No - risk score too high"
        if _safe_float(signal.get("risk_reward"), 0) < 1.5:
            return False, "Would I risk my own money? No - RR below minimum"
        if _safe_float(signal.get("display_confidence", signal.get("confidence")), 0) < 70 and signal.get("b_plus_calibrated") is not True:
            return False, "Would I risk my own money? No - confidence too low"
        return True, "Would I risk my own money? Yes - checklist passed"
    except Exception as e:
        return False, f"Would I risk my own money? No - self review error: {e}"


def _no_trade_reason(symbol, interval, reason):
    _record_scan_rejection(reason)
    print(f"NO_TRADE_REASON symbol={symbol} timeframe={interval} reason={reason}")
    print(f"NO_TRADE_BETTER_THAN_BAD_TRADE symbol={symbol} timeframe={interval}")


def _entry_manager_log(event, symbol, reason):
    try:
        reason_key = str(reason or "ok")[:90]
        key = (event, str(symbol or "").upper(), reason_key)
        now = time.time()
        if now - ENTRY_MANAGER_LOG_CACHE.get(key, 0) >= ENTRY_MANAGER_LOG_TTL_SECONDS:
            ENTRY_MANAGER_LOG_CACHE[key] = now
            print(f"{event} symbol={key[1]} reason={reason_key}")
    except Exception:
        pass


def get_live_price(symbol):
    symbol = str(symbol or "").upper().strip()
    if not symbol:
        return None, "missing symbol"
    sources = [
        ("BINANCE", f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"),
        ("BINANCE_US", f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}"),
    ]
    kucoin_symbol = symbol[:-4] + "-USDT" if symbol.endswith("USDT") else symbol
    sources.append(("KUCOIN", f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_symbol}"))
    failures = []
    for source, url in sources:
        data, status = _safe_market_json(url, timeout=6)
        try:
            if source == "KUCOIN":
                price = _safe_float((data or {}).get("data", {}).get("price"))
            else:
                price = _safe_float((data or {}).get("price"))
            if price > 0:
                return price, source
            failures.append(f"{source}:{status}")
        except Exception as e:
            failures.append(f"{source}:{e}")
    return None, ";".join(failures) or "no live price source"


def _entry_progress(direction, old_entry, current_price, tp1):
    try:
        if direction == "LONG":
            if current_price <= old_entry or tp1 <= old_entry:
                return 0.0
            return ((current_price - old_entry) / (tp1 - old_entry)) * 100
        if current_price >= old_entry or tp1 >= old_entry:
            return 0.0
        return ((old_entry - current_price) / (old_entry - tp1)) * 100
    except Exception:
        return 999.0


def _sl_room_percent(direction, current_price, sl):
    try:
        if current_price <= 0 or sl <= 0:
            return 0.0
        if direction == "LONG":
            return ((current_price - sl) / current_price) * 100
        return ((sl - current_price) / current_price) * 100
    except Exception:
        return 0.0


def _entry_manager_market_still_valid(symbol, direction, df, current_price):
    try:
        mtf = expert_multi_timeframe_context(symbol, direction, df)
        if mtf.get("state") != "CONFIRMED":
            return False, mtf.get("reason", "MTF no longer confirmed")
        ema20v = _safe_float(ema(df, 20).iloc[-1])
        ema50v = _safe_float(ema(df, 50).iloc[-1])
        if direction == "LONG" and current_price < ema50v and ema20v < ema50v:
            return False, "live price lost bullish EMA structure"
        if direction == "SHORT" and current_price > ema50v and ema20v > ema50v:
            return False, "live price lost bearish EMA structure"
        return True, "market direction still valid"
    except Exception as e:
        return False, f"market direction review error: {e}"


def _rebuild_entry_levels(signal, df, current_price):
    direction = signal.get("direction")
    support = _safe_float(signal.get("nearest_support") or signal.get("support"))
    resistance = _safe_float(signal.get("nearest_resistance") or signal.get("resistance"))
    atr_val = _safe_float(signal.get("atr"))
    if atr_val <= 0:
        atr_series = atr(df).dropna()
        atr_val = _safe_float(atr_series.iloc[-1] if len(atr_series) else 0)
    regime_info = {
        "support": support if support > 0 else None,
        "resistance": resistance if resistance > 0 else None,
    }
    return _candidate_levels(current_price, direction, regime_info, atr_val, rr_min=ENTRY_MANAGER_MIN_RR)


def professional_entry_manager(signal, df):
    try:
        symbol = signal.get("pair")
        direction = signal.get("direction")
        old_entry = _safe_float(signal.get("entry"))
        old_tp1 = _safe_float(signal.get("tp1") or signal.get("tp"))
        old_sl = _safe_float(signal.get("sl"))
        if not symbol or direction not in ["LONG", "SHORT"] or old_entry <= 0 or old_tp1 <= 0 or old_sl <= 0:
            _entry_manager_log("ENTRY_REJECTED", symbol, "invalid signal levels")
            return None, "invalid signal levels"

        current_price, source = get_live_price(symbol)
        if not current_price or current_price <= 0:
            _entry_manager_log("ENTRY_REJECTED", symbol, f"live price unavailable {source}")
            return None, f"live price unavailable: {source}"

        deviation = abs(current_price - old_entry) / old_entry * 100
        if deviation > ENTRY_MANAGER_MAX_UPDATE_PERCENT:
            _entry_manager_log("ENTRY_REJECTED", symbol, f"deviation {round(deviation, 4)}% above {ENTRY_MANAGER_MAX_UPDATE_PERCENT}%")
            return None, "live price moved too far from entry"

        progress = _entry_progress(direction, old_entry, current_price, old_tp1)
        if progress >= ENTRY_MANAGER_MAX_TP1_PROGRESS_PERCENT:
            _entry_manager_log("ENTRY_REJECTED", symbol, f"price progressed {round(progress, 2)}% toward TP1")
            return None, "price too close to TP1"

        sl_room = _sl_room_percent(direction, current_price, old_sl)
        if sl_room <= ENTRY_MANAGER_MIN_SL_ROOM_PERCENT:
            _entry_manager_log("ENTRY_REJECTED", symbol, f"SL room {round(sl_room, 4)}% too tight")
            return None, "price too close to SL"

        direction_ok, direction_reason = _entry_manager_market_still_valid(symbol, direction, df, current_price)
        if not direction_ok:
            _entry_manager_log("ENTRY_REJECTED", symbol, direction_reason)
            return None, direction_reason

        levels = _rebuild_entry_levels(signal, df, current_price)
        if not levels:
            _entry_manager_log("ENTRY_REJECTED", symbol, "updated S/R levels do not provide safe RR")
            return None, "updated S/R levels do not provide safe RR"
        if levels.get("risk_reward", 0) < ENTRY_MANAGER_MIN_RR:
            _entry_manager_log("ENTRY_REJECTED", symbol, f"updated RR {levels.get('risk_reward')} below {ENTRY_MANAGER_MIN_RR}")
            return None, "updated RR below minimum"
        if not signal_levels_valid(levels["entry"], levels["tp"], levels["sl"], direction):
            _entry_manager_log("ENTRY_REJECTED", symbol, "updated levels invalid")
            return None, "updated levels invalid"

        signal.update({
            "entry": format_price(levels["entry"]),
            "tp": format_price(levels["tp3"]),
            "tp1": format_price(levels["tp1"]),
            "tp2": format_price(levels["tp2"]),
            "tp3": format_price(levels["tp3"]),
            "sl": format_price(levels["sl"]),
            "risk_reward": levels["risk_reward"],
            "entry_manager": {
                "live_price": current_price,
                "source": source,
                "old_entry": old_entry,
                "deviation_percent": round(deviation, 5),
                "tp1_progress_percent": round(progress, 2),
                "updated": True,
            },
        })
        _entry_manager_log(
            "ENTRY_UPDATED",
            symbol,
            f"old={format_price(old_entry)} new={signal.get('entry')} rr={signal.get('risk_reward')} source={source}",
        )
        return signal, None
    except Exception as e:
        _entry_manager_log("ENTRY_REJECTED", signal.get("pair") if isinstance(signal, dict) else "", f"manager error {e}")
        return None, f"entry manager error: {e}"


def final_fund_manager_review(signal):
    try:
        direction = signal.get("direction")
        entry = _safe_float(signal.get("entry"))
        tp1 = _safe_float(signal.get("tp1") or signal.get("tp"))
        tp = _safe_float(signal.get("tp"))
        sl = _safe_float(signal.get("sl"))
        rr = _safe_float(signal.get("risk_reward"))
        if rr < ENTRY_MANAGER_MIN_RR:
            return False, f"RR {rr} below {ENTRY_MANAGER_MIN_RR}"
        if not signal_levels_valid(entry, tp, sl, direction):
            return False, "final levels invalid"
        if direction == "LONG" and not (tp1 > entry and tp > entry and sl < entry):
            return False, "LONG final geometry invalid"
        if direction == "SHORT" and not (tp1 < entry and tp < entry and sl > entry):
            return False, "SHORT final geometry invalid"
        if _safe_float(signal.get("display_confidence", signal.get("confidence")), 0) < 70:
            return False, "display confidence below minimum"
        return True, "fund manager review accepted live entry"
    except Exception as e:
        return False, f"final review error: {e}"


def detect_symbol_market_regime(symbol, interval, df):
    try:
        if df is None or len(df) < 80:
            return {"regime": "LOW_LIQUIDITY", "reason": "insufficient candles"}

        close = _safe_float(df["close"].iloc[-1])
        if close <= 0:
            return {"regime": "LOW_LIQUIDITY", "reason": "invalid close"}

        ema20v = _safe_float(ema(df, 20).iloc[-1])
        ema50v = _safe_float(ema(df, 50).iloc[-1])
        ema200v = _safe_float(ema(df, 200).iloc[-1] if len(df) >= 200 else ema(df, 100).iloc[-1])
        rsi_now = _safe_float(rsi(df).iloc[-1], 50)
        atr_series = atr(df).dropna()
        atr_val = _safe_float(atr_series.iloc[-1] if len(atr_series) else 0)
        atr_ratio = atr_val / close if close > 0 else 0
        volume_profile = robust_volume_profile(df)
        volume_ratio = _safe_float(volume_profile.get("volume_ratio"), 0)
        volume_state = volume_profile.get("volume_state", "UNKNOWN")
        volume_score = _safe_float(volume_profile.get("volume_score"), 45)
        atr_avg = _safe_float(atr_series.tail(60).mean() if len(atr_series) >= 60 else atr_val, atr_val)
        atr_relative = atr_val / atr_avg if atr_avg > 0 else 1
        levels = calculate_support_resistance(df)
        support = nearest_support(close, levels.get("support", []))
        resistance = nearest_resistance(close, levels.get("resistance", []))
        recent_high = _safe_float(df["high"].tail(25).max())
        recent_low = _safe_float(df["low"].tail(25).min())
        prev_high = _safe_float(df["high"].iloc[-26:-1].max())
        prev_low = _safe_float(df["low"].iloc[-26:-1].min())
        last = df.iloc[-1]
        candle_range = max(_safe_float(last["high"]) - _safe_float(last["low"]), close * 0.0001)
        body = abs(_safe_float(last["close"]) - _safe_float(last["open"]))
        upper_wick = _safe_float(last["high"]) - max(_safe_float(last["open"]), _safe_float(last["close"]))
        lower_wick = min(_safe_float(last["open"]), _safe_float(last["close"])) - _safe_float(last["low"])
        range_width = (recent_high - recent_low) / close if close > 0 and recent_high > recent_low else 0
        close_position = (close - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5
        ema_spread = (max(ema20v, ema50v, ema200v) - min(ema20v, ema50v, ema200v)) / close if close > 0 else 1
        long_mtf = multi_timeframe_quality(symbol, "LONG", interval, df)
        short_mtf = multi_timeframe_quality(symbol, "SHORT", interval, df)

        base = {
            "close": close,
            "ema20": ema20v,
            "ema50": ema50v,
            "ema200": ema200v,
            "rsi": rsi_now,
            "atr": atr_val,
            "atr_ratio": atr_ratio,
            "volume_ratio": volume_ratio,
            "volume_state": volume_state,
            "volume_score": volume_score,
            "support": support,
            "resistance": resistance,
            "recent_high": recent_high,
            "recent_low": recent_low,
            "range_width": range_width,
            "close_position": close_position,
            "ema_spread": ema_spread,
            "atr_relative": atr_relative,
            "body_ratio": body / candle_range,
            "upper_wick_ratio": upper_wick / candle_range,
            "lower_wick_ratio": lower_wick / candle_range,
            "long_mtf": long_mtf,
            "short_mtf": short_mtf,
        }

        volatility_state = expert_volatility_state(df)
        if volatility_state.get("state") == "LOW_VOLATILITY":
            if not STRICT_VOLATILITY_FILTER and _large_cap_symbol(symbol):
                base["volatility_filter_relaxed"] = True
                base["volatility_filter_reason"] = volatility_state.get("reason")
                return {**base, "regime": "CONSOLIDATION", "reason": f"LOW_VOLATILITY relaxed for large-cap: {volatility_state.get('reason')}"}
            return {**base, "regime": "LOW_VOLATILITY", "reason": volatility_state.get("reason")}

        fake_breakout_up = _safe_float(last["high"]) > prev_high and close < prev_high and upper_wick / candle_range >= 0.42
        fake_breakout_down = _safe_float(last["low"]) < prev_low and close > prev_low and lower_wick / candle_range >= 0.42
        if fake_breakout_up or fake_breakout_down:
            return {**base, "regime": "FAKE_BREAKOUT", "reason": "breakout failed and closed back inside range"}

        if volume_score < 45 and volume_ratio < 0.55 and range_width < 0.018 and ema_spread < 0.0065:
            return {**base, "regime": "LOW_VOLUME_CHOP", "reason": f"thin chop volume_score={round(volume_score, 1)} range={round(range_width, 4)}"}

        if range_width < 0.010 and atr_relative < 0.8 and ema_spread < 0.006:
            return {**base, "regime": "CONSOLIDATION", "reason": "tight range with compressed ATR"}

        if range_width >= 0.018 and atr_relative >= 1.25 and volume_ratio >= 1.0:
            expansion_direction = "LONG" if close_position >= 0.55 else "SHORT" if close_position <= 0.45 else None
            return {**base, "regime": "EXPANSION", "breakout_direction": expansion_direction, "reason": "ATR and volume expansion from range"}

        if range_width >= 0.014 and close_position <= 0.35 and volume_ratio >= 0.75 and 36 <= rsi_now <= 55:
            return {**base, "regime": "ACCUMULATION", "reversal_direction": "LONG", "reason": "discount range accumulation with acceptable volume"}

        if range_width >= 0.014 and close_position >= 0.65 and volume_ratio >= 0.75 and 45 <= rsi_now <= 66:
            return {**base, "regime": "DISTRIBUTION", "reversal_direction": "SHORT", "reason": "premium range distribution with acceptable volume"}

        # Treat very poor relative volume as a hard block, but do not reject
        # large-cap trend setups only because Binance.US/quote source reports a
        # temporarily thin candle. Thin-but-trending markets are handled later
        # by quality caps, not by inventing a trade.
        if volume_ratio and volume_ratio < 0.12:
            trend_stack = (ema20v > ema50v > ema200v) or (ema20v < ema50v < ema200v)
            mtf_confirmed = long_mtf.get("state") in ["CONFIRMED", "PARTIAL"] or short_mtf.get("state") in ["CONFIRMED", "PARTIAL"]
            if not (trend_stack and mtf_confirmed and volume_ratio >= 0.05):
                return {**base, "regime": "LOW_LIQUIDITY", "reason": f"volume ratio {round(volume_ratio, 2)} too low"}
        if atr_ratio > 0.06 or candle_range > max(atr_val * 3.0, close * 0.035):
            return {**base, "regime": "HIGH_VOLATILITY", "reason": f"ATR ratio {round(atr_ratio, 4)} too high"}
        if volume_ratio >= 1.25 and close > prev_high and rsi_now < 74:
            return {**base, "regime": "BREAKOUT", "breakout_direction": "LONG", "reason": "volume breakout above recent high"}
        if volume_ratio >= 1.25 and close < prev_low and rsi_now > 26:
            return {**base, "regime": "BREAKOUT", "breakout_direction": "SHORT", "reason": "volume breakdown below recent low"}
        if support and lower_wick / candle_range >= 0.45 and rsi_now <= 42 and abs(close - support) / close < 0.012:
            return {**base, "regime": "REVERSAL", "reversal_direction": "LONG", "reason": "support wick rejection with RSI recovery zone"}
        if resistance and upper_wick / candle_range >= 0.45 and rsi_now >= 58 and abs(resistance - close) / close < 0.012:
            return {**base, "regime": "REVERSAL", "reversal_direction": "SHORT", "reason": "resistance wick rejection with RSI rejection zone"}

        if range_width >= 0.012 and 38 <= rsi_now <= 62 and ema_spread < 0.0065:
            return {**base, "regime": "RANGE", "reason": "range-bound market with neutral RSI and tight EMAs"}

        if ema20v > ema50v > ema200v and long_mtf.get("state") in ["CONFIRMED", "PARTIAL"]:
            strength = "STRONG_BULL" if long_mtf.get("state") == "CONFIRMED" and volume_score >= 55 and rsi_now >= 52 and atr_relative >= 0.75 else "WEAK_BULL"
            return {**base, "regime": strength, "reason": f"{strength} EMA 20/50/200 bullish alignment"}
        if ema20v < ema50v < ema200v and short_mtf.get("state") in ["CONFIRMED", "PARTIAL"]:
            strength = "STRONG_BEAR" if short_mtf.get("state") == "CONFIRMED" and volume_score >= 55 and rsi_now <= 48 and atr_relative >= 0.75 else "WEAK_BEAR"
            return {**base, "regime": strength, "reason": f"{strength} EMA 20/50/200 bearish alignment"}
        if range_width >= 0.012 and 38 <= rsi_now <= 62:
            return {**base, "regime": "RANGE", "reason": "range-bound market with neutral RSI"}
        return {**base, "regime": "HIGH_VOLATILITY" if atr_ratio > 0.04 else "RANGE", "reason": "mixed structure without clean trend"}
    except Exception as e:
        return {"regime": "LOW_LIQUIDITY", "reason": f"regime detection error: {e}"}


def _candidate_levels(entry, direction, regime_info, atr_val, rr_min=1.5):
    """Build trade levels only when there is real room to the first obstacle.

    Previous adaptive levels could ignore a nearby support/resistance and place
    targets beyond it. That is exactly how a SHORT near support can bounce first,
    hit SL, then later continue down. This version treats the nearest
    support/resistance as an obstacle. If RR to the obstacle is not enough, the
    candidate is rejected instead of inventing a far target.
    """
    support = regime_info.get("support")
    resistance = regime_info.get("resistance")
    atr_val = max(_safe_float(atr_val), entry * 0.004)
    buffer = max(atr_val * 0.45, entry * 0.0025)

    if direction == "LONG":
        sl = (support - buffer) if support and support < entry else entry - max(atr_val * 1.25, entry * 0.006)
        risk = entry - sl
        if risk <= 0:
            return None

        if resistance and resistance > entry:
            obstacle_target = resistance - buffer * 0.25
            reward_to_obstacle = obstacle_target - entry
            if reward_to_obstacle <= 0 or (reward_to_obstacle / risk) < rr_min:
                return None
            tp3 = obstacle_target
        else:
            tp3 = entry + risk * max(1.8, rr_min)

        tp1 = entry + (tp3 - entry) * 0.45
        tp2 = entry + (tp3 - entry) * 0.72

    else:
        sl = (resistance + buffer) if resistance and resistance > entry else entry + max(atr_val * 1.25, entry * 0.006)
        risk = sl - entry
        if risk <= 0:
            return None

        if support and support < entry:
            obstacle_target = support + buffer * 0.25
            reward_to_obstacle = entry - obstacle_target
            if reward_to_obstacle <= 0 or (reward_to_obstacle / risk) < rr_min:
                return None
            tp3 = obstacle_target
        else:
            tp3 = entry - risk * max(1.8, rr_min)

        tp1 = entry - (entry - tp3) * 0.45
        tp2 = entry - (entry - tp3) * 0.72

    rr = abs(tp3 - entry) / max(abs(entry - sl), entry * 0.0001)
    return {
        "entry": entry,
        "sl": sl,
        "tp": tp3,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "risk_reward": round(rr, 2),
        "support": support,
        "resistance": resistance,
    }



ADAPTIVE_MARKET_MEMORY = {}
ADAPTIVE_WATCHLIST = []
ADAPTIVE_MEMORY_TTL_SECONDS = int(os.environ.get("ADAPTIVE_MEMORY_TTL_SECONDS", "7200"))
ADAPTIVE_OPPORTUNITY_MIN_SCORE = float(os.environ.get("ADAPTIVE_OPPORTUNITY_MIN_SCORE", "70"))


def _adaptive_log(event, **kwargs):
    try:
        parts = [event]
        for key, value in kwargs.items():
            safe = str(value).replace("\n", " ")[:140]
            parts.append(f"{key}={safe}")
        print(" ".join(parts))
    except Exception:
        pass


def adaptive_liquidity_map(df, regime_info=None):
    try:
        regime_info = regime_info or {}
        df = closed_candle_frame(df)
        if df is None or len(df) < 40:
            return {
                "liquidity_context": "INSUFFICIENT_DATA",
                "liquidity_score": 0,
                "liquidity_reason": "not enough candles for liquidity map",
            }
        recent = df.tail(36)
        close = _safe_float(df["close"].iloc[-1])
        last = df.iloc[-1]
        prev = df.iloc[-2]
        recent_high = _safe_float(recent["high"].max())
        recent_low = _safe_float(recent["low"].min())
        atr_val = max(_safe_float(regime_info.get("atr")), close * 0.003 if close else 0.0)
        tolerance = max(close * 0.0025, atr_val * 0.22)
        highs = [float(v) for v in recent["high"].tail(20).values]
        lows = [float(v) for v in recent["low"].tail(20).values]
        equal_highs = sum(1 for value in highs if abs(value - recent_high) <= tolerance) >= 2
        equal_lows = sum(1 for value in lows if abs(value - recent_low) <= tolerance) >= 2
        high_sweep = _safe_float(last["high"]) > recent_high and close < recent_high
        low_sweep = _safe_float(last["low"]) < recent_low and close > recent_low
        reclaim_after_low_sweep = low_sweep and close > _safe_float(prev["close"])
        rejection_after_high_sweep = high_sweep and close < _safe_float(prev["close"])
        candle_range = max(_safe_float(last["high"]) - _safe_float(last["low"]), close * 0.0001)
        upper_wick = _safe_float(last["high"]) - max(_safe_float(last["open"]), _safe_float(last["close"]))
        lower_wick = min(_safe_float(last["open"]), _safe_float(last["close"])) - _safe_float(last["low"])
        upper_rejection = upper_wick / candle_range >= 0.42
        lower_rejection = lower_wick / candle_range >= 0.42

        score = 35
        context = []
        if equal_highs:
            score += 8
            context.append("equal_highs")
        if equal_lows:
            score += 8
            context.append("equal_lows")
        if reclaim_after_low_sweep:
            score += 22
            context.append("sell_side_sweep_reclaim")
        elif low_sweep:
            score += 8
            context.append("sell_side_sweep_waiting_reclaim")
        if rejection_after_high_sweep:
            score += 22
            context.append("buy_side_sweep_rejection")
        elif high_sweep:
            score += 8
            context.append("buy_side_sweep_waiting_rejection")
        if upper_rejection or lower_rejection:
            score += 8
            context.append("rejection_wick")
        failed_sweep = (high_sweep and not rejection_after_high_sweep) or (low_sweep and not reclaim_after_low_sweep)
        if failed_sweep:
            score -= 18
            context.append("sweep_without_confirmation")
        score = int(_bounded(score, 0, 100))
        reason = ", ".join(context) if context else "no nearby liquidity event"
        return {
            "liquidity_context": "+".join(context) if context else "NEUTRAL",
            "liquidity_score": score,
            "liquidity_reason": reason,
            "equal_highs": equal_highs,
            "equal_lows": equal_lows,
            "liquidity_sweep": reclaim_after_low_sweep or rejection_after_high_sweep,
            "sweep_failed": failed_sweep,
            "stop_hunt_zone": bool(equal_highs or equal_lows or high_sweep or low_sweep),
            "reclaim_after_sweep": reclaim_after_low_sweep,
            "rejection_wick": bool(upper_rejection or lower_rejection),
        }
    except Exception as e:
        return {
            "liquidity_context": "ERROR",
            "liquidity_score": 0,
            "liquidity_reason": f"liquidity map error: {e}",
        }


def adaptive_market_memory_update(symbol, regime, setup_stage, rejection_reason=None):
    try:
        key = str(symbol or "").upper()
        now = time.time()
        old = ADAPTIVE_MARKET_MEMORY.get(key, {})
        old_regime = old.get("regime")
        stability = int(old.get("stability", 0) or 0)
        if old_regime == regime:
            stability = min(5, stability + 1)
        else:
            stability = 1 if stability <= 1 else stability - 1
        ADAPTIVE_MARKET_MEMORY[key] = {
            "time": now,
            "regime": regime,
            "setup_stage": setup_stage,
            "last_rejection_reason": rejection_reason,
            "stability": stability,
        }
        _adaptive_log("MARKET_MEMORY_UPDATED", symbol=key, regime=regime, stability=stability)
        return ADAPTIVE_MARKET_MEMORY[key]
    except Exception:
        return {}


def adaptive_mtf_playbook_context(symbol, interval, df):
    frames = {}
    try:
        for tf in ["4h", "1h", FUTURES_SETUP_TIMEFRAME, FUTURES_TRIGGER_TIMEFRAME]:
            frame = df if tf == interval else cached_market_data(symbol, tf, 220)
            frames[tf] = {
                "direction": _expert_tf_direction(frame),
                "available": frame is not None and len(frame) >= 80,
            }
        major = frames.get("4h", {}).get("direction", "UNKNOWN")
        confirm = frames.get("1h", {}).get("direction", "UNKNOWN")
        if major == "UNKNOWN" or confirm == "UNKNOWN":
            state = "UNCONFIRMED"
            reason = "4H/1H data unavailable"
        elif major == confirm == "BULL":
            state = "BULL_CONFIRMED"
            reason = "4H and 1H bullish"
        elif major == confirm == "BEAR":
            state = "BEAR_CONFIRMED"
            reason = "4H and 1H bearish"
        elif major == confirm == "RANGE":
            state = "RANGE_CONFIRMED"
            reason = "4H and 1H range"
        elif major in ["BULL", "BEAR"] and confirm == "RANGE":
            state = "SOFT_CONFLICT"
            reason = f"4H {major} with 1H RANGE"
        elif major == "RANGE" and confirm in ["BULL", "BEAR"]:
            state = "RANGE_WITH_LOWER_TF_TREND"
            reason = f"4H RANGE with 1H {confirm}"
        else:
            state = "HARD_CONFLICT"
            reason = f"4H {major} conflicts with 1H {confirm}"
        return {"state": state, "reason": reason, "frames": frames, "major": major, "confirm": confirm}
    except Exception as e:
        return {"state": "UNCONFIRMED", "reason": f"adaptive MTF error: {e}", "frames": frames}


def futures_bias_context(symbol):
    """Production futures bias: 4H macro, 1H directional bias."""
    try:
        df_4h = cached_market_data(symbol, "4h", 260)
        df_1h = cached_market_data(symbol, "1h", 260)
        if df_4h is None or len(df_4h) < 100 or df_1h is None or len(df_1h) < 100:
            return {"ok": False, "reason": "futures 4H/1H data unavailable", "macro": "UNKNOWN", "bias": "UNKNOWN"}
        macro = _expert_tf_direction(df_4h)
        bias = _expert_tf_direction(df_1h)
        if macro == "UNKNOWN" or bias == "UNKNOWN":
            return {"ok": False, "reason": f"unclear futures bias 4H={macro} 1H={bias}", "macro": macro, "bias": bias}
        if not FUTURES_ALLOW_COUNTER_TREND and ((macro == "BULL" and bias == "BEAR") or (macro == "BEAR" and bias == "BULL")):
            return {"ok": False, "reason": f"MTF conflict 4H={macro} 1H={bias}", "macro": macro, "bias": bias}
        if macro not in ["BULL", "BEAR"]:
            return {"ok": False, "reason": f"unclear 4H macro trend: {macro}", "macro": macro, "bias": bias}
        return {"ok": True, "reason": f"4H={macro} 1H={bias}", "macro": macro, "bias": bias, "df_4h": df_4h, "df_1h": df_1h}
    except Exception as e:
        return {"ok": False, "reason": f"futures bias error: {e}", "macro": "UNKNOWN", "bias": "UNKNOWN"}


def _futures_atr(df):
    try:
        series = atr(df).dropna()
        return _safe_float(series.iloc[-1], 0) if len(series) else 0.0
    except Exception:
        return 0.0


def _futures_level_context(df):
    try:
        close = _safe_float(df["close"].iloc[-1])
        levels = calculate_support_resistance(df)
        support = nearest_support(close, levels.get("support", []))
        resistance = nearest_resistance(close, levels.get("resistance", []))
        recent_high = _safe_float(df["high"].tail(36).max())
        recent_low = _safe_float(df["low"].tail(36).min())
        return {
            "close": close,
            "support": support,
            "resistance": resistance,
            "recent_high": recent_high,
            "recent_low": recent_low,
            "levels": levels,
        }
    except Exception:
        return {"close": 0, "support": None, "resistance": None, "recent_high": None, "recent_low": None, "levels": {}}


def futures_setup_context(symbol, direction, bias, setup_df):
    """30m setup validation. RSI/MACD alone never qualifies a setup."""
    try:
        if setup_df is None or len(setup_df) < 100:
            return {"ok": False, "stage": "WATCHING", "reason": "30m setup data unavailable"}
        close = _safe_float(setup_df["close"].iloc[-1])
        if close <= 0:
            return {"ok": False, "stage": "WATCHING", "reason": "invalid 30m close"}
        atr_val = _futures_atr(setup_df)
        if atr_val <= 0:
            return {"ok": False, "stage": "WATCHING", "reason": "30m ATR unavailable"}
        levels = _futures_level_context(setup_df)
        support = levels.get("support")
        resistance = levels.get("resistance")
        recent_high = levels.get("recent_high")
        recent_low = levels.get("recent_low")
        ema20v = _safe_float(ema(setup_df, 20).iloc[-1])
        ema50v = _safe_float(ema(setup_df, 50).iloc[-1])
        last = setup_df.iloc[-1]
        prev = setup_df.iloc[-2]
        candle_range = max(_safe_float(last["high"]) - _safe_float(last["low"]), close * 0.0001)
        upper_wick_ratio = (_safe_float(last["high"]) - max(_safe_float(last["open"]), _safe_float(last["close"]))) / candle_range
        lower_wick_ratio = (min(_safe_float(last["open"]), _safe_float(last["close"])) - _safe_float(last["low"])) / candle_range
        volume_profile = robust_volume_profile(setup_df)
        volume_score = _safe_float(volume_profile.get("volume_score"), 45)

        if recent_high and recent_low and recent_high > recent_low:
            range_pos = (close - recent_low) / (recent_high - recent_low)
            if 0.42 < range_pos < 0.58:
                return {"ok": False, "stage": "WATCHING", "reason": f"price in middle of 30m range position={round(range_pos, 2)}"}
        else:
            range_pos = 0.5

        setup = None
        reason = None
        if direction == "LONG":
            pullback = close >= min(ema20v, ema50v) * 0.995 and close <= max(ema20v, ema50v) * 1.015 and bias in ["BULL", "RANGE"]
            breakout_retest = recent_high and _safe_float(prev["close"]) > recent_high * 0.995 and _safe_float(last["low"]) <= recent_high + atr_val * 0.35 and close > recent_high
            sweep_reclaim = recent_low and _safe_float(last["low"]) < recent_low and close > recent_low and lower_wick_ratio >= 0.35
            sr_rejection = support and abs(close - support) <= max(atr_val * 0.9, close * 0.006) and lower_wick_ratio >= 0.28
            fvg_or_ob = len(setup_df) >= 4 and _safe_float(last["low"]) > _safe_float(setup_df["high"].iloc[-3]) and close <= (recent_low + (recent_high - recent_low) * 0.55 if recent_high and recent_low else close)
            if pullback:
                setup, reason = "Trend pullback to EMA20/EMA50 or structure", "30m pullback held dynamic support"
            if breakout_retest:
                setup, reason = "Breakout and retest", "30m breakout retested prior high"
            if sweep_reclaim:
                setup, reason = "Liquidity sweep and reclaim", "30m sell-side sweep reclaimed"
            if sr_rejection:
                setup, reason = "Support/Resistance rejection", "30m support rejection"
            if fvg_or_ob:
                setup, reason = "FVG / Order Block", "30m bullish imbalance confirmed by structure"
        else:
            pullback = close <= max(ema20v, ema50v) * 1.005 and close >= min(ema20v, ema50v) * 0.985 and bias in ["BEAR", "RANGE"]
            breakdown_retest = recent_low and _safe_float(prev["close"]) < recent_low * 1.005 and _safe_float(last["high"]) >= recent_low - atr_val * 0.35 and close < recent_low
            sweep_reject = recent_high and _safe_float(last["high"]) > recent_high and close < recent_high and upper_wick_ratio >= 0.35
            sr_rejection = resistance and abs(resistance - close) <= max(atr_val * 0.9, close * 0.006) and upper_wick_ratio >= 0.28
            fvg_or_ob = len(setup_df) >= 4 and _safe_float(last["high"]) < _safe_float(setup_df["low"].iloc[-3]) and close >= (recent_low + (recent_high - recent_low) * 0.45 if recent_high and recent_low else close)
            if pullback:
                setup, reason = "Trend pullback to EMA20/EMA50 or structure", "30m pullback held dynamic resistance"
            if breakdown_retest:
                setup, reason = "Breakdown and retest", "30m breakdown retested prior low"
            if sweep_reject:
                setup, reason = "Liquidity sweep and rejection", "30m buy-side sweep rejected"
            if sr_rejection:
                setup, reason = "Support/Resistance rejection", "30m resistance rejection"
            if fvg_or_ob:
                setup, reason = "FVG / Order Block", "30m bearish imbalance confirmed by structure"

        if not setup:
            adaptive_setup_lifecycle(symbol, "ARMED", "30m setup exists only as watchlist; no confirmed retest/pullback/rejection")
            return {"ok": False, "stage": "ARMED", "reason": "30m setup without confirmed retest/pullback/rejection"}
        if volume_score < 40:
            return {"ok": False, "stage": "WATCHING", "reason": f"30m volume/liquidity too weak score={round(volume_score, 1)}"}
        return {
            "ok": True,
            "setup": setup,
            "reason": reason,
            "stage": "CONFIRMED",
            "support": support,
            "resistance": resistance,
            "recent_high": recent_high,
            "recent_low": recent_low,
            "range_position": range_pos,
            "atr": atr_val,
            "volume_score": volume_score,
        }
    except Exception as e:
        return {"ok": False, "stage": "WATCHING", "reason": f"futures setup error: {e}"}


def futures_trigger_context(symbol, direction, trigger_df, setup_info):
    """15m final trigger. A setup without this returns SETUP_ARMED, not a signal."""
    try:
        if trigger_df is None or len(trigger_df) < 80:
            return {"ok": False, "stage": "ARMED", "reason": "15m trigger data unavailable"}
        close = _safe_float(trigger_df["close"].iloc[-1])
        if close <= 0:
            return {"ok": False, "stage": "ARMED", "reason": "invalid 15m close"}
        atr_val = _futures_atr(trigger_df)
        last = trigger_df.iloc[-1]
        prev = trigger_df.iloc[-2]
        candle_range = max(_safe_float(last["high"]) - _safe_float(last["low"]), close * 0.0001)
        body = abs(_safe_float(last["close"]) - _safe_float(last["open"]))
        if candle_range > max(atr_val * FUTURES_MAX_IMPULSE_ATR, close * 0.022):
            return {"ok": False, "stage": "INVALIDATED", "reason": "abnormal 15m candle expansion before entry"}
        if FUTURES_REQUIRE_TRIGGER_CLOSE and body / candle_range < 0.22:
            return {"ok": False, "stage": "ARMED", "reason": "15m candle close not decisive yet"}
        volume_profile = robust_volume_profile(trigger_df)
        volume_score = _safe_float(volume_profile.get("volume_score"), 45)
        rsi_now = _safe_float(rsi(trigger_df).iloc[-1], 50)
        ema20v = _safe_float(ema(trigger_df, 20).iloc[-1])
        ema50v = _safe_float(ema(trigger_df, 50).iloc[-1])
        levels = _futures_level_context(trigger_df)
        support = levels.get("support") or setup_info.get("support")
        resistance = levels.get("resistance") or setup_info.get("resistance")
        trigger = None
        reason = None
        if direction == "LONG":
            close_confirm = close > _safe_float(last["open"]) and close >= _safe_float(prev["close"]) and close >= ema20v * 0.998
            local_break_retest = _safe_float(last["low"]) <= _safe_float(prev["high"]) + atr_val * 0.35 and close > _safe_float(prev["high"])
            rejection = support and _safe_float(last["low"]) <= support + max(atr_val * 0.65, close * 0.004) and close > support
            momentum = ema20v >= ema50v * 0.995 and 44 <= rsi_now <= 70
            if close_confirm:
                trigger, reason = "15m confirmation candle", "15m closed in LONG direction"
            if local_break_retest:
                trigger, reason = "15m local break + retest", "local structure broke and retested"
            if rejection:
                trigger, reason = "15m rejection candle", "entry zone rejected support"
            if volume_score >= 55 and momentum:
                trigger = trigger or "15m volume/momentum confirmation"
                reason = reason or "volume and momentum confirm LONG"
            if resistance and (resistance - close) < max(atr_val * FUTURES_MIN_TP1_ATR_ROOM, close * 0.004):
                return {"ok": False, "stage": "INVALIDATED", "reason": "LONG too close to resistance"}
        else:
            close_confirm = close < _safe_float(last["open"]) and close <= _safe_float(prev["close"]) and close <= ema20v * 1.002
            local_break_retest = _safe_float(last["high"]) >= _safe_float(prev["low"]) - atr_val * 0.35 and close < _safe_float(prev["low"])
            rejection = resistance and _safe_float(last["high"]) >= resistance - max(atr_val * 0.65, close * 0.004) and close < resistance
            momentum = ema20v <= ema50v * 1.005 and 30 <= rsi_now <= 56
            if close_confirm:
                trigger, reason = "15m confirmation candle", "15m closed in SHORT direction"
            if local_break_retest:
                trigger, reason = "15m local break + retest", "local structure broke down and retested"
            if rejection:
                trigger, reason = "15m rejection candle", "entry zone rejected resistance"
            if volume_score >= 55 and momentum:
                trigger = trigger or "15m volume/momentum confirmation"
                reason = reason or "volume and momentum confirm SHORT"
            if support and (close - support) < max(atr_val * FUTURES_MIN_TP1_ATR_ROOM, close * 0.004):
                return {"ok": False, "stage": "INVALIDATED", "reason": "SHORT too close to support"}
        if not trigger:
            adaptive_setup_lifecycle(symbol, "ARMED", "30m setup ready; waiting for 15m trigger close")
            return {"ok": False, "stage": "ARMED", "reason": "15m trigger not confirmed yet"}
        return {
            "ok": True,
            "trigger": trigger,
            "reason": reason,
            "entry": close,
            "atr": atr_val,
            "support": support,
            "resistance": resistance,
            "volume_score": volume_score,
            "rsi": rsi_now,
        }
    except Exception as e:
        return {"ok": False, "stage": "ARMED", "reason": f"futures trigger error: {e}"}


def futures_apply_execution_frames(signal):
    """Validate and rebuild final Futures signal on 30m setup + 15m trigger only."""
    try:
        if str(signal.get("type") or "").upper() != "FUTURES":
            return signal, None
        symbol = signal.get("pair")
        direction = str(signal.get("direction") or "").upper()
        if direction not in ["LONG", "SHORT"]:
            return None, "invalid futures direction"
        bias = futures_bias_context(symbol)
        if not bias.get("ok"):
            return None, bias.get("reason")
        macro = bias.get("macro")
        one_h = bias.get("bias")
        if direction == "LONG" and macro != "BULL":
            return None, f"4H {macro} blocks LONG futures"
        if direction == "SHORT" and macro != "BEAR":
            return None, f"4H {macro} blocks SHORT futures"
        if one_h not in ([macro, "RANGE"]):
            return None, f"1H bias {one_h} conflicts with 4H {macro}"

        setup_df = cached_market_data(symbol, FUTURES_SETUP_TIMEFRAME, 240)
        trigger_df = cached_market_data(symbol, FUTURES_TRIGGER_TIMEFRAME, 240)
        setup = futures_setup_context(symbol, direction, one_h, setup_df)
        if not setup.get("ok"):
            if setup.get("stage") == "ARMED":
                adaptive_setup_lifecycle(symbol, "ARMED", setup.get("reason"))
                return None, f"SETUP_ARMED: {setup.get('reason')}"
            return None, setup.get("reason")
        trigger = futures_trigger_context(symbol, direction, trigger_df, setup)
        if not trigger.get("ok"):
            if trigger.get("stage") == "ARMED":
                adaptive_setup_lifecycle(symbol, "ARMED", trigger.get("reason"))
                return None, f"SETUP_ARMED: {trigger.get('reason')}"
            return None, trigger.get("reason")

        entry = _safe_float(trigger.get("entry"))
        atr_val = max(_safe_float(trigger.get("atr")), _safe_float(setup.get("atr")), entry * 0.004)
        regime_info = {
            "support": trigger.get("support") or setup.get("support"),
            "resistance": trigger.get("resistance") or setup.get("resistance"),
            "recent_low": setup.get("recent_low"),
            "recent_high": setup.get("recent_high"),
        }
        if FUTURES_REJECT_CHASE_ENTRY:
            planned_entry = _safe_float(signal.get("entry"), entry)
            if planned_entry > 0 and abs(entry - planned_entry) > atr_val * FUTURES_MAX_ENTRY_ATR_DISTANCE:
                return None, "ENTRY_MOVED"
        levels = _candidate_levels(entry, direction, regime_info, atr_val, rr_min=FUTURES_MIN_RR)
        if not levels:
            return None, "no safe 15m/30m RR room"
        if _safe_float(levels.get("risk_reward"), 0) < FUTURES_MIN_RR:
            return None, f"RR {levels.get('risk_reward')} below futures minimum {FUTURES_MIN_RR}"
        if direction == "LONG" and levels.get("resistance") and (levels["tp1"] >= levels["resistance"]):
            return None, "LONG TP1 too close to/through resistance"
        if direction == "SHORT" and levels.get("support") and (levels["tp1"] <= levels["support"]):
            return None, "SHORT TP1 too close to/through support"

        signal.update({
            "timeframe": FUTURES_TRIGGER_TIMEFRAME,
            "decision_timeframes": "4H/1H/30m/15m",
            "futures_macro_trend": macro,
            "futures_1h_bias": one_h,
            "futures_setup_timeframe": FUTURES_SETUP_TIMEFRAME,
            "futures_trigger_timeframe": FUTURES_TRIGGER_TIMEFRAME,
            "futures_30m_setup": setup.get("setup"),
            "futures_15m_trigger": trigger.get("trigger"),
            "entry": format_price(levels["entry"]),
            "entry_range": f"{format_price(levels['entry'] - atr_val * 0.18)} - {format_price(levels['entry'] + atr_val * 0.18)}",
            "tp": format_price(levels["tp3"]),
            "tp1": format_price(levels["tp1"]),
            "tp2": format_price(levels["tp2"]),
            "tp3": format_price(levels["tp3"]),
            "sl": format_price(levels["sl"]),
            "risk_reward": levels["risk_reward"],
            "support": format_price(levels.get("support") or regime_info.get("recent_low")),
            "resistance": format_price(levels.get("resistance") or regime_info.get("recent_high")),
            "nearest_support": format_price(levels.get("support") or regime_info.get("recent_low")),
            "nearest_resistance": format_price(levels.get("resistance") or regime_info.get("recent_high")),
            "stop_loss_reason": "SL placed behind 15m/30m structure with ATR buffer.",
            "cancel_condition": "Cancel if price leaves the entry range before fill, breaks the 15m structure, or the setup expires.",
            "signal_expiry_minutes": FUTURES_SIGNAL_EXPIRY_MINUTES,
            "recommended_leverage": f"Max {FUTURES_MAX_RECOMMENDED_LEVERAGE}x conservative",
            "signal_quality_reason": (
                f"4H trend {macro}; 1H bias {one_h}; 30m setup {setup.get('setup')}; "
                f"15m trigger {trigger.get('trigger')}; {trigger.get('reason')}"
            ),
        })
        return signal, None
    except Exception as e:
        return None, f"futures execution frame error: {e}"


def btc_market_context():
    try:
        btc_df = cached_market_data("BTCUSDT", "1h", 220)
        if btc_df is None or len(btc_df) < 80:
            return {"btc_context": "UNAVAILABLE", "btc_risk_mode": "CAUTION", "btc_alignment_score": 45}
        info = detect_symbol_market_regime("BTCUSDT", "1h", btc_df)
        regime = info.get("regime", "RANGE")
        vol = expert_volatility_state(btc_df)
        if regime in ["FAKE_BREAKOUT", "HIGH_VOLATILITY", "LOW_VOLUME_CHOP"] or not vol.get("ok", False):
            risk = "DEFENSIVE"
            score = 35
        elif regime in ["STRONG_BULL", "STRONG_BEAR", "WEAK_BULL", "WEAK_BEAR"]:
            risk = "NORMAL"
            score = 70
        else:
            risk = "CAUTION"
            score = 55
        return {
            "btc_context": regime,
            "btc_volatility_state": vol.get("state"),
            "btc_trend_direction": "BULL" if "BULL" in regime else "BEAR" if "BEAR" in regime else "RANGE",
            "btc_risk_mode": risk,
            "btc_alignment_score": score,
        }
    except Exception as e:
        return {"btc_context": "ERROR", "btc_risk_mode": "CAUTION", "btc_alignment_score": 45, "btc_reason": str(e)}


def adaptive_dynamic_risk_brain(regime_info, btc_context_info, liquidity_info, mtf_info):
    try:
        reasons = []
        regime = regime_info.get("regime", "RANGE")
        risk_mode = "NORMAL"
        if regime in ["LOW_VOLUME_CHOP", "FAKE_BREAKOUT", "HIGH_NEWS_RISK", "LOW_LIQUIDITY"]:
            risk_mode = "NO_TRADE"
            reasons.append(regime)
        if btc_context_info.get("btc_risk_mode") == "DEFENSIVE":
            risk_mode = "DEFENSIVE" if risk_mode != "NO_TRADE" else risk_mode
            reasons.append("BTC defensive")
        if mtf_info.get("state") == "HARD_CONFLICT":
            risk_mode = "NO_TRADE"
            reasons.append(mtf_info.get("reason"))
        if regime in ["HIGH_VOLATILITY", "LOW_VOLATILITY"] and risk_mode == "NORMAL":
            risk_mode = "CAUTION"
            reasons.append(regime)
        if liquidity_info.get("sweep_failed"):
            risk_mode = "NO_TRADE"
            reasons.append("failed liquidity sweep")
        if liquidity_info.get("liquidity_score", 0) < 35 and risk_mode == "NORMAL":
            risk_mode = "CAUTION"
            reasons.append("weak liquidity context")
        return {
            "risk_mode": risk_mode,
            "risk_mode_reason": "; ".join([str(r) for r in reasons if r]) or "normal adaptive risk",
        }
    except Exception as e:
        return {"risk_mode": "CAUTION", "risk_mode_reason": f"risk brain error: {e}"}


def adaptive_setup_lifecycle(symbol, stage, reason, setup=None):
    try:
        if stage == "WATCHING":
            _adaptive_log("SETUP_WATCHING", symbol=symbol, reason=reason)
        elif stage == "ARMED":
            _adaptive_log("SETUP_ARMED", symbol=symbol, reason=reason)
        elif stage == "CONFIRMED":
            _adaptive_log("SETUP_CONFIRMED", symbol=symbol, setup=setup or "adaptive")
        else:
            _adaptive_log("SETUP_INVALIDATED", symbol=symbol, reason=reason)
        if stage in {"WATCHING", "ARMED"}:
            ADAPTIVE_WATCHLIST.append({
                "time": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "stage": stage,
                "reason": reason,
            })
            del ADAPTIVE_WATCHLIST[:-100]
            _adaptive_log("WATCHLIST_SETUP", symbol=symbol, stage=stage, reason=reason)
    except Exception:
        pass


def adaptive_market_playbook(symbol, interval, df, regime_info, liquidity_info=None, btc_context_info=None):
    liquidity_info = liquidity_info or {}
    btc_context_info = btc_context_info or {}
    regime = regime_info.get("regime", "RANGE")
    close = _safe_float(regime_info.get("close"))
    support = regime_info.get("support")
    resistance = regime_info.get("resistance")
    range_pos = _safe_float(regime_info.get("close_position"), 0.5)
    rsi_now = _safe_float(regime_info.get("rsi"), 50)
    volume_score = _safe_float(regime_info.get("volume_score"), 0)
    rr_min = 1.5
    confidence_cap = None
    mtf = adaptive_mtf_playbook_context(symbol, interval, df)

    def rejected(reason, stage="INVALIDATED"):
        adaptive_setup_lifecycle(symbol, stage, reason)
        _adaptive_log("PLAYBOOK_REJECTED", symbol=symbol, reason=reason)
        return {"ok": False, "reason": reason, "stage": stage, "mtf": mtf}

    if regime in ["LOW_VOLUME_CHOP", "FAKE_BREAKOUT", "HIGH_NEWS_RISK", "LOW_LIQUIDITY"]:
        return rejected(f"{regime} no trade", "WATCHING" if regime == "LOW_VOLUME_CHOP" else "INVALIDATED")
    if mtf.get("state") == "HARD_CONFLICT":
        return rejected(f"hard MTF conflict: {mtf.get('reason')}")

    if regime in ["STRONG_BULL", "WEAK_BULL", "BULL_TREND"]:
        mtf_decision = evaluate_mtf_alignment(mtf, "LONG")
        if mtf_decision.get("classification") == "HARD_CONFLICT":
            return rejected(mtf_decision.get("reason"), "INVALIDATED")
        if not mtf_decision.get("ok"):
            return rejected(mtf_decision.get("reason"), "ARMED")
        setup = "trend_pullback_continuation"
        if mtf_decision.get("classification") == "STRICT_ALIGNMENT":
            reason = "4H and 1H bull trend continuation"
        else:
            reason = mtf_decision.get("reason")
            mtf["b_plus_mtf_path"] = True
            mtf["alignment_classification"] = mtf_decision.get("classification")
            _adaptive_log("MTF_SOFT_ALIGNMENT_ALLOWED", symbol=symbol, direction="LONG", major=mtf_decision.get("major"), confirm=mtf_decision.get("confirm"))
        return {
            "ok": True,
            "direction": "LONG",
            "strategy_name": setup,
            "reasons": [reason, regime_info.get("reason")],
            "rr_min": 1.5,
            "confidence_cap": confidence_cap,
            "mtf": mtf,
            "playbook": "STRONG_TREND",
        }

    if regime in ["STRONG_BEAR", "WEAK_BEAR", "BEAR_TREND"]:
        mtf_decision = evaluate_mtf_alignment(mtf, "SHORT")
        if mtf_decision.get("classification") == "HARD_CONFLICT":
            return rejected(mtf_decision.get("reason"), "INVALIDATED")
        if not mtf_decision.get("ok"):
            return rejected(mtf_decision.get("reason"), "ARMED")
        setup = "trend_following_confirmed"
        if mtf_decision.get("classification") == "STRICT_ALIGNMENT":
            reason = "4H and 1H bear trend continuation"
        else:
            reason = mtf_decision.get("reason")
            mtf["b_plus_mtf_path"] = True
            mtf["alignment_classification"] = mtf_decision.get("classification")
            _adaptive_log("MTF_SOFT_ALIGNMENT_ALLOWED", symbol=symbol, direction="SHORT", major=mtf_decision.get("major"), confirm=mtf_decision.get("confirm"))
        return {
            "ok": True,
            "direction": "SHORT",
            "strategy_name": setup,
            "reasons": [reason, regime_info.get("reason")],
            "rr_min": 1.5,
            "confidence_cap": confidence_cap,
            "mtf": mtf,
            "playbook": "STRONG_TREND",
        }

    if regime in ["RANGE", "CONSOLIDATION"]:
        if mtf.get("state") not in ["RANGE_CONFIRMED", "RANGE_WITH_LOWER_TF_TREND"]:
            return rejected(f"range setup requires 4H/1H range context: {mtf.get('reason')}", "WATCHING")
        if support and close and range_pos <= 0.18 and (rsi_now <= 48 or liquidity_info.get("rejection_wick")):
            return {
                "ok": True,
                "direction": "LONG",
                "strategy_name": "range_edge_bounce",
                "reasons": ["range support edge bounce", regime_info.get("reason")],
                "rr_min": 1.6,
                "confidence_cap": 78,
                "mtf": mtf,
                "playbook": "RANGE",
            }
        if resistance and close and range_pos >= 0.82 and (rsi_now >= 52 or liquidity_info.get("rejection_wick")):
            return {
                "ok": True,
                "direction": "SHORT",
                "strategy_name": "range_edge_bounce",
                "reasons": ["range resistance edge rejection", regime_info.get("reason")],
                "rr_min": 1.6,
                "confidence_cap": 78,
                "mtf": mtf,
                "playbook": "RANGE",
            }
        return rejected(f"mid-range no trade position={round(range_pos, 2)}", "WATCHING")

    if regime == "ACCUMULATION":
        if volume_score < 45:
            return rejected("ACCUMULATION needs volume_score >= 45", "ARMED")
        if liquidity_info.get("reclaim_after_sweep") or liquidity_info.get("liquidity_sweep"):
            return {
                "ok": True,
                "direction": "LONG",
                "strategy_name": "accumulation_reclaim",
                "reasons": ["accumulation reclaim after liquidity sweep", regime_info.get("reason")],
                "rr_min": 1.7,
                "confidence_cap": 82,
                "mtf": mtf,
                "playbook": "ACCUMULATION",
            }
        return rejected("ACCUMULATION waiting for sweep/reclaim confirmation", "ARMED")

    if regime == "DISTRIBUTION":
        if volume_score < 45:
            return rejected("DISTRIBUTION needs volume_score >= 45", "ARMED")
        if liquidity_info.get("rejection_wick") or liquidity_info.get("liquidity_sweep"):
            return {
                "ok": True,
                "direction": "SHORT",
                "strategy_name": "distribution_rejection",
                "reasons": ["distribution rejection at resistance", regime_info.get("reason")],
                "rr_min": 1.7,
                "confidence_cap": 82,
                "mtf": mtf,
                "playbook": "DISTRIBUTION",
            }
        return rejected("DISTRIBUTION waiting for resistance sweep/rejection", "ARMED")

    if regime in ["BREAKOUT", "EXPANSION"]:
        if liquidity_info.get("sweep_failed"):
            return rejected("FAKE_BREAKOUT no trade")
        direction = regime_info.get("breakout_direction") or ("LONG" if range_pos >= 0.55 else "SHORT")
        smart = smart_money_entry_zone(df, direction, regime_info)
        if not smart.get("ok") or "Retest" not in str(smart.get("setup", "")):
            return rejected("breakout chase blocked; waiting for break and retest", "ARMED")
        return {
            "ok": True,
            "direction": direction,
            "strategy_name": "break_and_retest",
            "reasons": ["breakout accepted only after retest", regime_info.get("reason")],
            "rr_min": 1.6,
            "confidence_cap": None,
            "mtf": mtf,
            "playbook": "BREAKOUT_EXPANSION",
        }

    return rejected(f"no adaptive playbook for {regime}", "WATCHING")


def apply_adaptive_confidence_cap(signal, cap, reason):
    try:
        if cap is None:
            return signal
        old_conf = _safe_float(signal.get("confidence"), 0)
        old_display = _safe_float(signal.get("display_confidence", old_conf), old_conf)
        if old_conf > cap:
            signal["confidence"] = int(cap)
        if old_display > cap:
            signal["display_confidence"] = int(cap)
        if signal.get("quality_report"):
            signal["quality_report"]["display_confidence"] = signal.get("display_confidence")
            signal["quality_report"]["confidence_cap_reason"] = reason
        signal["confidence_cap_reason"] = reason
    except Exception:
        pass
    return signal


def adaptive_opportunity_score(signal):
    try:
        display_conf = _safe_float(signal.get("display_confidence", signal.get("confidence")), 0)
        rr = _safe_float(signal.get("risk_reward"), 0)
        risk_score = _safe_float(signal.get("risk_score"), 50)
        liquidity_score = _safe_float(signal.get("liquidity_score"), 45)
        rs_score = _safe_float(signal.get("relative_strength_score"), 50)
        btc_score = _safe_float(signal.get("btc_alignment_score"), 50)
        freshness = 100 if signal.get("entry_manager", {}).get("updated") or signal.get("entry") else 80
        setup_validity = _safe_float(signal.get("setup_validity_score"), display_conf)
        entry_grade = _safe_float(signal.get("entry_location_grade"), 70)
        performance = _safe_float(signal.get("learning_adjustment"), 0)
        score = (
            setup_validity * 0.18
            + entry_grade * 0.14
            + liquidity_score * 0.12
            + rs_score * 0.10
            + min(rr * 22, 100) * 0.12
            + display_conf * 0.16
            + max(0, 100 - risk_score) * 0.08
            + freshness * 0.05
            + btc_score * 0.04
            + (50 + performance) * 0.01
        )
        if signal.get("mtf_path") == "soft_alignment" or signal.get("mtf_soft_conflict") is True:
            score -= 6
            signal["scoring_penalty_reason"] = "SOFT_MTF_ALIGNMENT_PENALTY"
        score = int(_bounded(round(score), 0, 100))
        signal["opportunity_score"] = score
        signal["ranking_reason"] = (
            f"setup={round(setup_validity, 1)} entry={round(entry_grade, 1)} "
            f"liq={round(liquidity_score, 1)} rs={round(rs_score, 1)} rr={rr} btc={round(btc_score, 1)}"
        )
        _adaptive_log("OPPORTUNITY_RANKED", symbol=signal.get("pair"), score=score, reason=signal.get("ranking_reason"))
        return score
    except Exception as e:
        signal["opportunity_score"] = 0
        signal["ranking_reason"] = f"opportunity score error: {e}"
        return 0


def relative_strength_context(symbol, signal, market_candidates=None):
    try:
        direction = signal.get("direction")
        score = 50
        if signal.get("pair") == "BTCUSDT":
            score = 55
        else:
            btc_align = _safe_float(signal.get("btc_alignment_score"), 50)
            momentum = _safe_float(signal.get("display_confidence", signal.get("confidence")), 50)
            volume = _safe_float(signal.get("volume_score"), 50)
            score = (momentum * 0.45) + (volume * 0.25) + (btc_align * 0.30)
            if direction == "SHORT":
                score = 100 - min(score, 100) if score > 60 else score
        score = int(_bounded(score, 0, 100))
        signal["relative_strength_score"] = score
        signal["btc_relative_score"] = score
        signal["momentum_rank"] = score
        signal["volume_rank"] = int(_bounded(_safe_float(signal.get("volume_score"), 50), 0, 100))
        _adaptive_log("RELATIVE_STRENGTH_RANK", symbol=symbol, rank=signal.get("momentum_rank"), score=score)
        return signal
    except Exception:
        signal["relative_strength_score"] = 50
        return signal


def _strategy_for_regime(regime_info):
    playbook = regime_info.get("adaptive_playbook")
    if isinstance(playbook, dict) and playbook.get("ok"):
        return playbook.get("direction"), playbook.get("strategy_name"), list(playbook.get("reasons") or [])

    regime = regime_info.get("regime")
    close = _safe_float(regime_info.get("close"))
    support = regime_info.get("support")
    resistance = regime_info.get("resistance")
    rsi_now = _safe_float(regime_info.get("rsi"), 50)

    if regime in ["STRONG_BULL", "WEAK_BULL", "BULL_TREND"]:
        return "LONG", "trend_following_long", ["Bull trend EMA alignment", regime_info.get("reason")]
    if regime in ["STRONG_BEAR", "WEAK_BEAR", "BEAR_TREND"]:
        return "SHORT", "trend_following_short", ["Bear trend EMA alignment", regime_info.get("reason")]
    if regime in ["BREAKOUT", "EXPANSION"]:
        direction = regime_info.get("breakout_direction")
        if not direction:
            direction = "LONG" if regime_info.get("close_position", 0.5) >= 0.55 else "SHORT"
        return direction, "confirmed_breakout", ["Breakout confirmed by volume", regime_info.get("reason")]
    if regime in ["REVERSAL", "ACCUMULATION", "DISTRIBUTION"]:
        direction = regime_info.get("reversal_direction")
        if not direction:
            direction = "LONG" if regime == "ACCUMULATION" else "SHORT"
        return direction, "wick_rejection_reversal", ["Reversal only after wick rejection", regime_info.get("reason")]
    if regime in ["RANGE", "CONSOLIDATION"]:
        if support and close and abs(close - support) / close < 0.012 and rsi_now <= 48:
            return "LONG", "range_support_bounce", ["Range support bounce", regime_info.get("reason")]
        if resistance and close and abs(resistance - close) / close < 0.012 and rsi_now >= 52:
            return "SHORT", "range_resistance_rejection", ["Range resistance rejection", regime_info.get("reason")]
    return None, None, [regime_info.get("reason", "no strategy matched")]


def _adaptive_score(regime_info, direction, strategy_name, levels, symbol, timeframe, reasons):
    score = 45
    long_mtf = regime_info.get("long_mtf", {})
    short_mtf = regime_info.get("short_mtf", {})
    mtf = long_mtf if direction == "LONG" else short_mtf
    volume_ratio = _safe_float(regime_info.get("volume_ratio"))
    rsi_now = _safe_float(regime_info.get("rsi"), 50)
    ema20v = _safe_float(regime_info.get("ema20"))
    ema50v = _safe_float(regime_info.get("ema50"))
    ema200v = _safe_float(regime_info.get("ema200"))
    rr = _safe_float(levels.get("risk_reward"))

    if mtf.get("state") == "CONFIRMED":
        score += 14
        reasons.append("MTF confirmed")
    elif mtf.get("state") == "PARTIAL":
        score += 7
        reasons.append("MTF partial")

    if direction == "LONG" and ema20v > ema50v > ema200v:
        score += 10
        reasons.append("EMA structure supports LONG")
    if direction == "SHORT" and ema20v < ema50v < ema200v:
        score += 10
        reasons.append("EMA structure supports SHORT")

    if volume_ratio >= 1.25:
        score += 8
        reasons.append(f"volume confirmation {round(volume_ratio, 2)}x")
    elif volume_ratio >= 0.8:
        score += 3

    if direction == "LONG" and 38 <= rsi_now <= 68:
        score += 6
        reasons.append("RSI quality for LONG")
    if direction == "SHORT" and 32 <= rsi_now <= 62:
        score += 6
        reasons.append("RSI quality for SHORT")

    if regime_info.get("support") and regime_info.get("resistance"):
        score += 8
        reasons.append("support/resistance mapped")

    if regime_info.get("upper_wick_ratio", 0) > 0.42 or regime_info.get("lower_wick_ratio", 0) > 0.42:
        score += 5
        reasons.append("candle wick confirmation")

    if rr >= 2.0:
        score += 10
    elif rr >= 1.5:
        score += 6

    learning_adjustment, learning_reason = adaptive_learning_weight(strategy_name, symbol, timeframe, direction)
    score += learning_adjustment
    reasons.append(learning_reason)
    return int(_bounded(score, 0, 100))


def build_adaptive_signal_candidate(symbol, interval, df, paid=True):
    try:
        regime_info = detect_symbol_market_regime(symbol, interval, df)
        regime = regime_info.get("regime", "LOW_LIQUIDITY")
        relaxed_low_volatility = (
            regime == "LOW_VOLATILITY"
            and not STRICT_VOLATILITY_FILTER
            and _large_cap_symbol(symbol)
        )
        if regime in ["LOW_LIQUIDITY", "HIGH_VOLATILITY", "LOW_VOLATILITY", "LOW_VOLUME_CHOP", "FAKE_BREAKOUT", "HIGH_NEWS_RISK"] and not relaxed_low_volatility:
            reason = f"{regime}: {regime_info.get('reason')}"
            _no_trade_reason(symbol, interval, reason)
            return None, reason, regime_info
        if relaxed_low_volatility:
            regime_info = {**regime_info, "regime": "CONSOLIDATION", "volatility_filter_relaxed": True}
            regime = "CONSOLIDATION"

        volatility_state = expert_volatility_state(df)
        relaxed_volatility_filter = (
            volatility_state.get("state") == "LOW_VOLATILITY"
            and not STRICT_VOLATILITY_FILTER
            and _large_cap_symbol(symbol)
        )
        if not volatility_state.get("ok") and not relaxed_volatility_filter:
            reason = f"{volatility_state.get('state')}: {volatility_state.get('reason')}"
            _no_trade_reason(symbol, interval, reason)
            return None, reason, {**regime_info, "volatility_filter": volatility_state}
        if relaxed_volatility_filter:
            regime_info = {**regime_info, "volatility_filter": volatility_state, "volatility_filter_relaxed": True}

        news_ok, news_reason = high_impact_news_guard()
        if not news_ok:
            _no_trade_reason(symbol, interval, news_reason)
            return None, news_reason, {**regime_info, "regime": "HIGH_NEWS_RISK", "reason": news_reason}

        liquidity_info = adaptive_liquidity_map(df, regime_info)
        btc_info = btc_market_context()
        playbook = adaptive_market_playbook(symbol, interval, df, regime_info, liquidity_info, btc_info)
        adaptive_market_memory_update(symbol, regime, playbook.get("stage", "EVALUATED"), playbook.get("reason"))
        if not playbook.get("ok"):
            reason = playbook.get("reason", "adaptive playbook rejected")
            _no_trade_reason(symbol, interval, reason)
            return None, reason, {**regime_info, **liquidity_info, **btc_info, "adaptive_playbook": playbook}
        _scan_diag_inc("playbooks_selected")
        _adaptive_log("PLAYBOOK_SELECTED", symbol=symbol, regime=regime, playbook=playbook.get("playbook"))
        adaptive_setup_lifecycle(symbol, "CONFIRMED", "playbook confirmed", playbook.get("strategy_name"))
        _scan_diag_inc("setups_confirmed")
        regime_info = {**regime_info, **liquidity_info, **btc_info, "adaptive_playbook": playbook, "adaptive_mtf_playbook": playbook.get("mtf")}

        risk_brain = adaptive_dynamic_risk_brain(regime_info, btc_info, liquidity_info, playbook.get("mtf", {}))
        regime_info.update(risk_brain)
        if risk_brain.get("risk_mode") == "NO_TRADE":
            reason = f"risk brain no trade: {risk_brain.get('risk_mode_reason')}"
            _no_trade_reason(symbol, interval, reason)
            return None, reason, regime_info

        direction, strategy_name, reasons = _strategy_for_regime(regime_info)
        if not direction or not strategy_name:
            return None, "no adaptive strategy matched", regime_info

        expert_mtf = expert_multi_timeframe_context(symbol, direction, df if interval == "5m" else None)
        mtf_override_ok = playbook.get("playbook") in {"RANGE", "ACCUMULATION", "DISTRIBUTION", "BREAKOUT_EXPANSION"} and playbook.get("mtf", {}).get("state") in {"RANGE_CONFIRMED", "RANGE_WITH_LOWER_TF_TREND", "SOFT_CONFLICT"}
        b_plus_mtf = b_plus_mtf_path_context(playbook.get("mtf"), direction)
        if expert_mtf.get("state") != "CONFIRMED" and not mtf_override_ok and not b_plus_mtf.get("ok"):
            reason = f"MTF rejected: {expert_mtf.get('reason')}"
            if b_plus_mtf.get("reason"):
                reason = f"{reason}; b_plus={b_plus_mtf.get('reason')}"
            _no_trade_reason(symbol, interval, reason)
            return None, reason, {**regime_info, "expert_mtf": expert_mtf}
        if mtf_override_ok:
            expert_mtf = {**expert_mtf, "state": "CONFIRMED", "score": max(_safe_float(expert_mtf.get("score"), 0), 80), "reason": f"playbook override: {playbook.get('mtf', {}).get('reason')}"}
        elif b_plus_mtf.get("ok") and expert_mtf.get("state") != "CONFIRMED":
            expert_mtf = {
                **expert_mtf,
                "state": "CONFIRMED",
                "score": max(_safe_float(expert_mtf.get("score"), 0), 78),
                "reason": b_plus_mtf.get("reason"),
                "b_plus_mtf_path": True,
                "b_plus_mtf_context": b_plus_mtf,
            }
            regime_info["b_plus_mtf_path"] = True
            regime_info["b_plus_mtf_reason"] = b_plus_mtf.get("reason")

        smart_entry = smart_money_entry_zone(df, direction, regime_info)
        if not smart_entry.get("ok"):
            reason = f"Entry rejected: {smart_entry.get('reason')}"
            _no_trade_reason(symbol, interval, reason)
            return None, reason, {**regime_info, "smart_money": smart_entry}
        entry_timing_ok, entry_timing_reason = late_entry_after_confirmation_guard(df, direction, regime_info, smart_entry)
        if not entry_timing_ok:
            _no_trade_reason(symbol, interval, entry_timing_reason)
            return None, entry_timing_reason, {**regime_info, "smart_money": smart_entry}
        _scan_diag_inc("entry_confirmations_passed")

        exhausted, exhaustion_reason = trend_exhaustion_filter(df, direction)
        if exhausted:
            _no_trade_reason(symbol, interval, exhaustion_reason)
            return None, exhaustion_reason, {**regime_info, "exhaustion": exhaustion_reason}

        entry = _safe_float(regime_info.get("close"))
        atr_val = _safe_float(regime_info.get("atr"))
        levels = _candidate_levels(entry, direction, regime_info, atr_val, rr_min=playbook.get("rr_min", 1.5))
        if not levels:
            return None, "not enough room to nearest support/resistance for safe RR", regime_info
        if levels["risk_reward"] < playbook.get("rr_min", 1.5):
            return None, f"RR {levels['risk_reward']} below {playbook.get('rr_min', 1.5)}", regime_info
        if not signal_levels_valid(levels["entry"], levels["tp"], levels["sl"], direction):
            return None, "invalid LONG/SHORT level geometry", regime_info

        confidence = _adaptive_score(regime_info, direction, strategy_name, levels, symbol, interval, reasons)
        min_conf = 75 if paid else 70
        b_plus_pending = False
        if confidence < min_conf:
            pre_signal_ok = (
                62 <= confidence <= 74
                and playbook.get("strategy_name") in B_PLUS_CONFIRMED_SETUPS
                and levels.get("risk_reward", 0) >= playbook.get("rr_min", 1.5)
                and smart_entry.get("ok") is True
                and expert_mtf.get("state") == "CONFIRMED"
            )
            if not pre_signal_ok:
                print(f"B_PLUS_CALIBRATION_REJECTED symbol={symbol} reason=confidence {confidence} below {min_conf}")
                return None, f"confidence {confidence} below {min_conf}", regime_info
            b_plus_pending = True

        target_basis = "Adaptive Support/Resistance"
        reason_text = "; ".join([str(r) for r in reasons if r])
        signal = {
            "pair": symbol,
            "timeframe": interval,
            "type": "FUTURES",
            "direction": direction,
            "entry": format_price(levels["entry"]),
            "tp": format_price(levels["tp3"]),
            "tp1": format_price(levels["tp1"]),
            "tp2": format_price(levels["tp2"]),
            "tp3": format_price(levels["tp3"]),
            "sl": format_price(levels["sl"]),
            "confidence": confidence,
            "trend": detect_trend(df),
            "volume": volume_strength(df),
            "smc": detect_smc(df),
            "trend_power": trend_strength(df),
            "structure": market_structure(df),
            "score": confidence - 50 if direction == "LONG" else 50 - confidence,
            "support": format_price(levels.get("support") or regime_info.get("recent_low")),
            "resistance": format_price(levels.get("resistance") or regime_info.get("recent_high")),
            "nearest_support": format_price(levels.get("support") or regime_info.get("recent_low")),
            "nearest_resistance": format_price(levels.get("resistance") or regime_info.get("recent_high")),
            "risk_reward": levels["risk_reward"],
            "support_strength": 4,
            "resistance_strength": 4,
            "target_basis": target_basis,
            "setup_type": strategy_name,
            "strategy_name": strategy_name,
            "market_regime": regime,
            "adaptive_regime": regime,
            "expert_mtf": expert_mtf,
            "expert_session": expert_session_state(),
            "expert_volatility": volatility_state,
            "smart_money_setup": smart_entry.get("setup"),
            "smart_money_reason": smart_entry.get("reason"),
            "entry_confirmation_age_candles": smart_entry.get("entry_confirmation_age_candles"),
            "entry_timing_reason": entry_timing_reason,
            "news_filter": news_reason,
            "atr": atr_val,
            "atr_ratio": regime_info.get("atr_ratio"),
            "volume_ratio": regime_info.get("volume_ratio"),
            "reasons": reasons,
            "signal_quality_reason": f"{reason_text}; {smart_entry.get('setup')}: {smart_entry.get('reason')}",
            "entry_location_reason": regime_info.get("reason", "adaptive setup"),
            "management_note": "Protect the trade after TP1 or +0.6R; reduce exposure in high volatility.",
            "breakeven_trigger_r": 0.6,
            "adaptive_playbook": playbook.get("playbook"),
            "setup_lifecycle": "CONFIRMED",
            "b_plus_calibration_pending": b_plus_pending,
            "b_plus_mtf_path": bool(expert_mtf.get("b_plus_mtf_path")),
            "b_plus_mtf_reason": expert_mtf.get("reason") if expert_mtf.get("b_plus_mtf_path") else None,
            "liquidity_context": liquidity_info.get("liquidity_context"),
            "liquidity_score": liquidity_info.get("liquidity_score"),
            "liquidity_reason": liquidity_info.get("liquidity_reason"),
            "btc_context": btc_info.get("btc_context"),
            "btc_risk_mode": btc_info.get("btc_risk_mode"),
            "btc_alignment_score": btc_info.get("btc_alignment_score"),
            "risk_mode": risk_brain.get("risk_mode"),
            "risk_mode_reason": risk_brain.get("risk_mode_reason"),
            "volatility_filter_relaxed": bool(regime_info.get("volatility_filter_relaxed")),
            "entry_location_grade": 86 if smart_entry.get("ok") else 45,
            "setup_validity_score": confidence,
        }
        if signal.get("b_plus_mtf_path"):
            signal["b_plus_calibration_pending"] = True
            signal["b_plus_calibrated"] = True
            signal["quality_tier"] = "B_PLUS"
            signal["opportunity_tier"] = "B_PLUS"
            signal["mtf_path"] = "soft_alignment"
            signal["mtf_soft_conflict"] = True
            signal["confidence_cap_reason"] = "b_plus_soft_mtf_path_cap"
            playbook["confidence_cap"] = min(_safe_float(playbook.get("confidence_cap"), 78) or 78, 78)
        apply_adaptive_confidence_cap(signal, playbook.get("confidence_cap"), f"{playbook.get('playbook')} confidence cap")
        relative_strength_context(symbol, signal)
        adaptive_opportunity_score(signal)
        _adaptive_log("PLAYBOOK_SIGNAL_BUILT", symbol=symbol, setup=strategy_name, conf=signal.get("display_confidence", signal.get("confidence")), rr=signal.get("risk_reward"))
        return signal, None, regime_info
    except Exception as e:
        return None, f"adaptive candidate error: {e}", {"regime": "ERROR"}


def finalize_adaptive_signal(signal, df, paid=True):
    try:
        direction = signal["direction"]
        interval = signal.get("timeframe", "5m")
        entry = _safe_float(signal["entry"])
        tp = _safe_float(signal["tp"])
        sl = _safe_float(signal["sl"])
        htf_ok = higher_timeframe_confirmation(signal["pair"], direction, interval)

        ai_engine_report = build_ai_engine_report(
            df,
            {
                "timeframe": interval,
                "direction": direction,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "confidence": signal.get("confidence"),
            },
            higher_tf_ok=htf_ok,
        )
        max_risk = 80 if paid else 84
        if ai_engine_report["risk_score"] >= max_risk:
            return None, f"risk score {ai_engine_report['risk_score']} too high"

        type_scores = evaluate_trade_types(
            direction=direction,
            trend=signal.get("trend"),
            trend_power=signal.get("trend_power"),
            confidence=signal.get("confidence"),
            htf_ok=htf_ok,
            structure=signal.get("structure"),
            volume=signal.get("volume"),
            volatility_state=ai_engine_report["volatility_state"],
            risk_score=ai_engine_report["risk_score"],
            timeframe=interval,
        )
        trade_type, adjusted_type_scores = choose_trade_type(type_scores)
        signal["type"] = trade_type
        if trade_type == "FUTURES":
            signal, futures_reason = futures_apply_execution_frames(signal)
            if not signal:
                return None, futures_reason or "futures 15m/30m validation rejected"
        signal.update({
            "type_scores": adjusted_type_scores,
            "spot_score": adjusted_type_scores.get("SPOT", 0),
            "futures_score": adjusted_type_scores.get("FUTURES", 0),
            "risk_score": ai_engine_report["risk_score"],
            "risk_level": ai_engine_report["risk_level"],
            "engine_confidence": ai_engine_report["engine_confidence"],
            "multi_timeframe": ai_engine_report["multi_timeframe"],
            "multi_timeframe_score": ai_engine_report["multi_timeframe_score"],
            "market_structure": ai_engine_report["market_structure"],
            "structure_score": ai_engine_report["structure_score"],
            "volume_state": ai_engine_report["volume_state"],
            "volume_score": ai_engine_report["volume_score"],
            "volume_ratio": ai_engine_report["volume_ratio"],
            "volatility_state": ai_engine_report["volatility_state"],
            "volatility_score": ai_engine_report["volatility_score"],
            "atr_ratio": ai_engine_report["atr_ratio"],
            "trend_score": ai_engine_report["trend_score"],
            "ema_alignment": ai_engine_report["ema_alignment"],
            "ai_engine": ai_engine_report,
            "final_score_reason": signal.get("signal_quality_reason"),
        })
        quality_ok, quality_reason = apply_signal_quality_report(signal)
        if not quality_ok:
            return None, quality_reason
        if _safe_float(signal.get("display_confidence"), 0) < 70:
            calibrated, calibration_reason = apply_b_plus_calibration(signal)
            if not calibrated:
                return None, f"display confidence {signal.get('display_confidence')} below 70"
        expert_context = {
            "mtf": signal.get("expert_mtf") or {},
            "volatility": signal.get("expert_volatility") or {},
            "session": signal.get("expert_session") or expert_session_state(),
            "smart_money": {
                "ok": bool(signal.get("smart_money_setup")),
                "setup": signal.get("smart_money_setup"),
                "reason": signal.get("smart_money_reason"),
            },
            "news_ok": str(signal.get("news_filter") or "").lower().startswith("no high impact"),
            "news_reason": signal.get("news_filter"),
        }
        checklist = expert_quality_checklist(signal, {
            "regime": signal.get("market_regime"),
            "volume_score": signal.get("volume_score"),
        }, expert_context)
        signal["quality_checklist"] = checklist
        signal["quality_checklist_score"] = checklist["percent"]
        if checklist["percent"] < EXPERT_QUALITY_MIN_PERCENT:
            supply_ok, supply_reason = adaptive_supply_calibration(signal, checklist)
            if supply_ok:
                signal["quality_gate_override_reason"] = supply_reason
            else:
                failed_names = ",".join([item["name"] for item in checklist.get("failed", [])])
                _no_trade_reason(signal.get("pair"), interval, f"quality checklist {checklist['percent']}% failed={failed_names}")
                return None, f"quality checklist {checklist['percent']}% below {EXPERT_QUALITY_MIN_PERCENT}% failed={failed_names}; supply={supply_reason}"
        self_ok, self_reason = expert_self_review(signal, checklist)
        signal["self_review"] = self_reason
        if not self_ok:
            _no_trade_reason(signal.get("pair"), interval, self_reason)
            return None, self_reason
        try:
            from ai_model import explain_predict_trade
            ai_ok, ai_reason = explain_predict_trade(signal)
        except Exception:
            ai_ok, ai_reason = predict_trade(signal), "legacy AI decision"
        if not ai_ok:
            return None, f"AI model rejected adaptive signal: {ai_reason}"
        managed_signal, entry_reason = professional_entry_manager(signal, df)
        if not managed_signal:
            return None, entry_reason
        final_ok, final_reason = final_fund_manager_review(managed_signal)
        if not final_ok:
            _entry_manager_log("FINAL_REVIEW_FAILED", managed_signal.get("pair"), final_reason)
            return None, final_reason
        _entry_manager_log("FINAL_REVIEW_PASSED", managed_signal.get("pair"), final_reason)
        _scan_diag_inc("finalized_candidates")
        return managed_signal, None
    except Exception as e:
        return None, f"adaptive finalize error: {e}"


def no_trade_summary(symbol, interval, market_summary, best_candidate, rejection_reason):
    try:
        compact_market = {
            "symbol": symbol,
            "timeframe": interval,
            "regime": market_summary.get("regime") if isinstance(market_summary, dict) else market_summary,
            "reason": market_summary.get("reason") if isinstance(market_summary, dict) else "",
        }
        print(f"NO_TRADE market_summary={compact_market} best_candidate={best_candidate} rejection_reason={rejection_reason}")
    except Exception:
        pass


# ================= STRONG SIGNAL FILTER =================
def strong_signal_filter(df, trend, trend_power, direction):
    try:
        if df is None or len(df) < 60:
            return False

        if is_choppy(df):
            return False

        # منع السوق المكسّر
        if trend_power == "MIXED":
            return False

        # منع عكس الترند القوي
        if trend_power == "STRONG_BULL" and direction == "SHORT":
            return False

        if trend_power == "STRONG_BEAR" and direction == "LONG":
            return False

        last = df["close"].iloc[-1]
        prev = df["close"].iloc[-4]

        if prev <= 0:
            return False

        move = abs(last - prev) / prev

        # لازم حركة محترمة
        if move < 0.003:
            return False

        # لازم آخر 3 شموع مايبقوش ضعاف
        recent_range = (df["high"].tail(3) - df["low"].tail(3)).mean()
        if recent_range <= 0:
            return False

        # ATR لازم يبقى محترم
        atr_val = atr(df).iloc[-1]
        if pd.isna(atr_val) or atr_val <= 0:
            return False

        if (atr_val / last) < 0.001:
            return False

        return True

    except:
        return False


# ================= GENERATE PAID SIGNAL =================
def generate_signal(symbol, interval="5m"):
    _scan_diag_attempt(symbol)
    df = get_market_data(symbol, interval)
    if df is None or len(df) < 100:
        return None

    if is_choppy(df):
        return None

    if not strong_momentum(df):
        return None

    if not volatility_ok(df):
        return None

    df["rsi"] = rsi(df)
    macd_line, signal_line = macd(df)
    df["atr"] = atr(df)

    trend = detect_trend(df)
    trend_power = trend_strength(df)
    volume = volume_strength(df)
    smc = detect_smc(df)
    structure = market_structure(df)

    news_ok = news_filter()

    rsi_val = df["rsi"].iloc[-1]
    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    atr_val = df["atr"].iloc[-1]

    if pd.isna(rsi_val) or pd.isna(macd_val) or pd.isna(signal_val):
        return None

    score = ai_score(
        rsi_val,
        macd_val,
        signal_val,
        trend,
        volume,
        smc,
        trend_power,
        structure
    )

    if not news_ok:
        return None

    candidate_pipeline_log("CANDIDATE_PIPELINE_ENTER", symbol, interval, stage="adaptive_build_paid")
    adaptive_signal, adaptive_reason, adaptive_regime = build_adaptive_signal_candidate(symbol, interval, df, paid=True)
    if adaptive_signal:
        candidate_pipeline_log("CANDIDATE_PIPELINE_ACCEPT", symbol, interval, stage="playbook_signal_built", signal=adaptive_signal)
        finalized_signal, finalize_reason = finalize_adaptive_signal(adaptive_signal, df, paid=True)
        if finalized_signal:
            tier = mark_opportunity_tier(finalized_signal)
            candidate_pipeline_log("CANDIDATE_PIPELINE_ACCEPT", symbol, interval, stage="finalized", signal=finalized_signal, tier=tier)
            _mark_signal_built(finalized_signal)
            return finalized_signal
        candidate_pipeline_log("CANDIDATE_PIPELINE_REJECT", symbol, interval, stage="finalize", reason=finalize_reason, signal=adaptive_signal)
        no_trade_summary(symbol, interval, adaptive_regime, {
            "direction": adaptive_signal.get("direction"),
            "strategy": adaptive_signal.get("strategy_name"),
            "confidence": adaptive_signal.get("confidence"),
            "rr": adaptive_signal.get("risk_reward"),
        }, finalize_reason)
        return skip_signal(symbol, interval, finalize_reason or "adaptive signal rejected")

    candidate_pipeline_log("CANDIDATE_PIPELINE_REJECT", symbol, interval, stage="adaptive_build", reason=adaptive_reason)
    no_trade_summary(symbol, interval, adaptive_regime, None, adaptive_reason)
    return skip_signal(symbol, interval, adaptive_reason or "adaptive strategy rejected")

    # Legacy strict path retained as unreachable fallback documentation.
    direction, regime, selected_mtf, direction_reason = choose_signal_direction(
        symbol, interval, df, score, trend, trend_power, MIN_SCORE_TO_TRADE
    )
    if not direction:
        return skip_signal(symbol, interval, direction_reason)

    if _signal_in_build_cooldown(symbol, interval):
        return skip_signal(symbol, interval, "duplicate symbol/timeframe cooldown")

    market_context = build_market_context(symbol, interval, df, direction)
    if not market_context.get("allowed", True):
        return skip_signal(symbol, interval, market_context.get("skip_reason", "market context rejected"))
    mtf_context = market_context.get("multi_timeframe_context", {})
    market_ok, market_reason = _market_direction_guard(direction, market_context, mtf_context)
    if not market_ok:
        return skip_signal(symbol, interval, market_reason)

    if not strong_signal_filter(df, trend, trend_power, direction):
        return skip_signal(symbol, interval, "local trend/momentum filter rejected setup")

    htf_ok = higher_timeframe_confirmation(symbol, direction, interval)

    # منع العكس القوي جدًا فقط
    if direction == "LONG" and trend_power == "STRONG_BEAR" and abs(score) < (MIN_SCORE_TO_TRADE + 2):
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL" and abs(score) < (MIN_SCORE_TO_TRADE + 2):
        return None

    # ================= NEW FILTERS =================
    if late_entry_filter(df, direction):
        return None

    if not support_resistance_filter(df, direction):
        return None

    if not pullback_entry_quality(df, direction):
        return None

    if not rejection_wick_filter(df, direction):
        return None

    entry = df["close"].iloc[-1]
    sr_targets = sr_based_targets(df, entry, direction, atr_val)
    if not sr_targets:
        return None
    tp = sr_targets["tp"]
    sl = sr_targets["sl"]
    location_ok, location_reason = _entry_location_filter(df, direction, sr_targets, atr_val, interval)
    if not location_ok:
        return skip_signal(symbol, interval, location_reason)
    if direction == "LONG":
        reversal_ok, reversal_reason = spot_long_confirmation(df, sr_targets.get("support"))
        if not reversal_ok:
            return skip_signal(symbol, interval, reversal_reason)
    else:
        reversal_reason = "short protected by strong resistance"

    # ===== Reject dead / tiny targets =====
    tp_distance = abs(tp - entry) / entry
    sl_distance = abs(sl - entry) / entry

    if tp_distance < 0.0085:
        return None

    if sl_distance < 0.0035:
        return None

    momentum_ok = strong_momentum(df)
    confidence = calculate_confidence(
        score, volume, smc, trend_power, structure, momentum_ok, htf_ok
    )

    if not signal_levels_valid(entry, tp, sl, direction):
        return None

    # مدفوع = لازم يكون نضيف
    min_paid_conf = 74 + (5 if not htf_ok else 0)

    if confidence < min_paid_conf:
        return None

    signal = {
        "pair": symbol,
        "timeframe": interval,
        "type": "FUTURES",
        "direction": direction,
        "entry": format_price(entry),
        "tp": format_price(tp),
        "sl": format_price(sl),
        "confidence": confidence,
        "trend": trend,
        "volume": volume,
        "smc": smc,
        "trend_power": trend_power,
        "structure": structure,
        "score": score,
        "support": format_price(sr_targets["support"]),
        "resistance": format_price(sr_targets["resistance"]),
        "nearest_support": format_price(sr_targets["nearest_support"]),
        "nearest_resistance": format_price(sr_targets["nearest_resistance"]),
        "risk_reward": sr_targets["risk_reward"],
        "support_strength": sr_targets.get("support_strength"),
        "resistance_strength": sr_targets.get("resistance_strength"),
        "target_basis": sr_targets["target_basis"],
        "setup_type": sr_targets.get("setup_type", "S/R_CONTINUATION"),
        "market_regime": market_context.get("market_regime", "SIDEWAYS"),
        "signal_quality_reason": sr_targets.get("signal_quality_reason", "Strong support/resistance validation passed") + f" | Direction: {direction_reason}",
        "entry_location_reason": location_reason,
        "management_note": "If price reaches +0.6R then protect the trade: move SL to breakeven or take partial profit.",
        "breakeven_trigger_r": 0.6
    }

    ai_engine_report = build_ai_engine_report(
        df,
        {
            "timeframe": interval,
            "direction": direction,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "confidence": confidence,
        },
        higher_tf_ok=htf_ok,
    )

    if ai_engine_report["risk_score"] >= 78:
        return None

    type_scores = evaluate_trade_types(
        direction=direction,
        trend=trend,
        trend_power=trend_power,
        confidence=confidence,
        htf_ok=htf_ok,
        structure=structure,
        volume=volume,
        volatility_state=ai_engine_report["volatility_state"],
        risk_score=ai_engine_report["risk_score"],
        timeframe=interval,
    )
    trade_type, adjusted_type_scores = choose_trade_type(type_scores)
    signal["type"] = trade_type
    if trade_type == "FUTURES":
        signal, futures_reason = futures_apply_execution_frames(signal)
        if not signal:
            _no_trade_reason(symbol, interval, futures_reason or "futures 15m/30m validation rejected")
            return None, futures_reason or "futures 15m/30m validation rejected"

    signal.update({
        "type_scores": adjusted_type_scores,
        "spot_score": adjusted_type_scores.get("SPOT", 0),
        "futures_score": adjusted_type_scores.get("FUTURES", 0),
        "risk_score": ai_engine_report["risk_score"],
        "risk_level": ai_engine_report["risk_level"],
        "engine_confidence": ai_engine_report["engine_confidence"],
        "multi_timeframe": ai_engine_report["multi_timeframe"],
        "multi_timeframe_score": ai_engine_report["multi_timeframe_score"],
        "market_structure": ai_engine_report["market_structure"],
        "structure_score": ai_engine_report["structure_score"],
        "volume_state": ai_engine_report["volume_state"],
        "volume_score": ai_engine_report["volume_score"],
        "volume_ratio": ai_engine_report["volume_ratio"],
        "volatility_state": ai_engine_report["volatility_state"],
        "volatility_score": ai_engine_report["volatility_score"],
        "atr_ratio": ai_engine_report["atr_ratio"],
        "trend_score": ai_engine_report["trend_score"],
        "ema_alignment": ai_engine_report["ema_alignment"],
        "ai_engine": ai_engine_report,
    })

    score_report = final_signal_score(signal, market_context, sr_targets, mtf_context, reversal_reason)
    required_score = MIN_SPOT_FINAL_SCORE if signal.get("type") == "SPOT" else MIN_FUTURES_FINAL_SCORE
    if score_report["final_score"] < required_score:
        return skip_signal(symbol, interval, f"final score {score_report['final_score']} below {required_score}: {score_report['final_score_reason']}")
    signal.update(score_report)
    quality_ok, quality_reason = apply_signal_quality_report(signal)
    if not quality_ok:
        return skip_signal(symbol, interval, quality_reason)
    if _safe_float(signal.get("display_confidence"), 0) < 70:
        calibrated, calibration_reason = apply_b_plus_calibration(signal)
        if not calibrated:
            return skip_signal(symbol, interval, f"display confidence {signal.get('display_confidence')} below 70")
    if signal["final_score"] < required_score:
        return skip_signal(symbol, interval, f"composite final score {signal['final_score']} below {required_score}: {signal.get('confidence_cap_reason')}")

    try:
        if not predict_trade(signal):
            return None
    except Exception as e:
        print(f"AI model error in generate_signal {symbol} {interval}: {e}")
        return None

    _mark_signal_built(signal)
    return signal


# ================= GENERATE FREE SIGNAL =================
def generate_free_signal(symbol, interval="5m"):
    _scan_diag_attempt(symbol)
    df = get_market_data(symbol, interval)
    if df is None or len(df) < 60:
        return None

    if is_choppy(df):
        return None

    if not strong_momentum(df):
        return None

    if not volatility_ok(df):
        return None

    df["rsi"] = rsi(df)
    macd_line, signal_line = macd(df)
    df["atr"] = atr(df)

    trend = detect_trend(df)
    trend_power = trend_strength(df)
    volume = volume_strength(df)
    smc = detect_smc(df)
    structure = market_structure(df)

    rsi_val = df["rsi"].iloc[-1]
    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    atr_val = df["atr"].iloc[-1]

    if pd.isna(rsi_val) or pd.isna(macd_val) or pd.isna(signal_val):
        return None

    score = ai_score(
        rsi_val,
        macd_val,
        signal_val,
        trend,
        volume,
        smc,
        trend_power,
        structure
    )

    candidate_pipeline_log("CANDIDATE_PIPELINE_ENTER", symbol, interval, stage="adaptive_build_free")
    adaptive_signal, adaptive_reason, adaptive_regime = build_adaptive_signal_candidate(symbol, interval, df, paid=False)
    if adaptive_signal:
        candidate_pipeline_log("CANDIDATE_PIPELINE_ACCEPT", symbol, interval, stage="playbook_signal_built", signal=adaptive_signal)
        finalized_signal, finalize_reason = finalize_adaptive_signal(adaptive_signal, df, paid=False)
        if finalized_signal:
            tier = mark_opportunity_tier(finalized_signal)
            candidate_pipeline_log("CANDIDATE_PIPELINE_ACCEPT", symbol, interval, stage="finalized", signal=finalized_signal, tier=tier)
            _mark_signal_built(finalized_signal)
            return finalized_signal
        candidate_pipeline_log("CANDIDATE_PIPELINE_REJECT", symbol, interval, stage="finalize", reason=finalize_reason, signal=adaptive_signal)
        no_trade_summary(symbol, interval, adaptive_regime, {
            "direction": adaptive_signal.get("direction"),
            "strategy": adaptive_signal.get("strategy_name"),
            "confidence": adaptive_signal.get("confidence"),
            "rr": adaptive_signal.get("risk_reward"),
        }, finalize_reason)
        return skip_signal(symbol, interval, finalize_reason or "adaptive signal rejected")

    candidate_pipeline_log("CANDIDATE_PIPELINE_REJECT", symbol, interval, stage="adaptive_build", reason=adaptive_reason)
    no_trade_summary(symbol, interval, adaptive_regime, None, adaptive_reason)
    return skip_signal(symbol, interval, adaptive_reason or "adaptive strategy rejected")

    direction, regime, selected_mtf, direction_reason = choose_signal_direction(
        symbol, interval, df, score, trend, trend_power, 5
    )
    if not direction:
        return skip_signal(symbol, interval, direction_reason)

    if _signal_in_build_cooldown(symbol, interval):
        return skip_signal(symbol, interval, "duplicate symbol/timeframe cooldown")

    market_context = build_market_context(symbol, interval, df, direction)
    if not market_context.get("allowed", True):
        return skip_signal(symbol, interval, market_context.get("skip_reason", "market context rejected"))
    mtf_context = market_context.get("multi_timeframe_context", {})
    market_ok, market_reason = _market_direction_guard(direction, market_context, mtf_context)
    if not market_ok:
        return skip_signal(symbol, interval, market_reason)

    if not strong_signal_filter(df, trend, trend_power, direction):
        return skip_signal(symbol, interval, "local trend/momentum filter rejected setup")

    htf_ok = higher_timeframe_confirmation(symbol, direction, interval)

    if not htf_ok and abs(score) < 6:
        return None

    if direction == "LONG" and trend_power == "STRONG_BEAR" and abs(score) < 6:
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL" and abs(score) < 6:
        return None

    # ================= NEW FILTERS =================
    if late_entry_filter(df, direction):
        return None

    if not support_resistance_filter(df, direction):
        return None

    if not pullback_entry_quality(df, direction):
        return None

    if not rejection_wick_filter(df, direction):
        return None

    entry = df["close"].iloc[-1]
    sr_targets = sr_based_targets(df, entry, direction, atr_val)
    if not sr_targets:
        return None
    tp = sr_targets["tp"]
    sl = sr_targets["sl"]
    location_ok, location_reason = _entry_location_filter(df, direction, sr_targets, atr_val, interval)
    if not location_ok:
        return skip_signal(symbol, interval, location_reason)
    if direction == "LONG":
        reversal_ok, reversal_reason = spot_long_confirmation(df, sr_targets.get("support"))
        if not reversal_ok:
            return skip_signal(symbol, interval, reversal_reason)
    else:
        reversal_reason = "short protected by strong resistance"

    tp_distance = abs(tp - entry) / entry
    sl_distance = abs(sl - entry) / entry

    if tp_distance < 0.0075:
        return None

    if sl_distance < 0.003:
        return None

    momentum_ok = strong_momentum(df)
    confidence = calculate_confidence(
        score, volume, smc, trend_power, structure, momentum_ok, htf_ok
    )

    if not signal_levels_valid(entry, tp, sl, direction):
        return None

    min_free_conf = 66 + (5 if not htf_ok else 0)

    if confidence < min_free_conf:
        return None

    signal = {
        "pair": symbol,
        "timeframe": interval,
        "type": "FUTURES",
        "direction": direction,
        "entry": format_price(entry),
        "tp": format_price(tp),
        "sl": format_price(sl),
        "confidence": confidence,
        "trend": trend,
        "volume": volume,
        "smc": smc,
        "trend_power": trend_power,
        "structure": structure,
        "score": score,
        "support": format_price(sr_targets["support"]),
        "resistance": format_price(sr_targets["resistance"]),
        "nearest_support": format_price(sr_targets["nearest_support"]),
        "nearest_resistance": format_price(sr_targets["nearest_resistance"]),
        "risk_reward": sr_targets["risk_reward"],
        "support_strength": sr_targets.get("support_strength"),
        "resistance_strength": sr_targets.get("resistance_strength"),
        "target_basis": sr_targets["target_basis"],
        "setup_type": sr_targets.get("setup_type", "S/R_CONTINUATION"),
        "market_regime": market_context.get("market_regime", "SIDEWAYS"),
        "signal_quality_reason": sr_targets.get("signal_quality_reason", "Strong support/resistance validation passed") + f" | Direction: {direction_reason}",
        "entry_location_reason": location_reason,
        "management_note": "If price reaches +0.6R then protect the trade: move SL to breakeven or take partial profit.",
        "breakeven_trigger_r": 0.6
    }

    ai_engine_report = build_ai_engine_report(
        df,
        {
            "timeframe": interval,
            "direction": direction,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "confidence": confidence,
        },
        higher_tf_ok=htf_ok,
    )

    if ai_engine_report["risk_score"] >= 82:
        return None

    type_scores = evaluate_trade_types(
        direction=direction,
        trend=trend,
        trend_power=trend_power,
        confidence=confidence,
        htf_ok=htf_ok,
        structure=structure,
        volume=volume,
        volatility_state=ai_engine_report["volatility_state"],
        risk_score=ai_engine_report["risk_score"],
        timeframe=interval,
    )
    trade_type, adjusted_type_scores = choose_trade_type(type_scores)
    signal["type"] = trade_type

    signal.update({
        "type_scores": adjusted_type_scores,
        "spot_score": adjusted_type_scores.get("SPOT", 0),
        "futures_score": adjusted_type_scores.get("FUTURES", 0),
        "risk_score": ai_engine_report["risk_score"],
        "risk_level": ai_engine_report["risk_level"],
        "engine_confidence": ai_engine_report["engine_confidence"],
        "multi_timeframe": ai_engine_report["multi_timeframe"],
        "multi_timeframe_score": ai_engine_report["multi_timeframe_score"],
        "market_structure": ai_engine_report["market_structure"],
        "structure_score": ai_engine_report["structure_score"],
        "volume_state": ai_engine_report["volume_state"],
        "volume_score": ai_engine_report["volume_score"],
        "volume_ratio": ai_engine_report["volume_ratio"],
        "volatility_state": ai_engine_report["volatility_state"],
        "volatility_score": ai_engine_report["volatility_score"],
        "atr_ratio": ai_engine_report["atr_ratio"],
        "trend_score": ai_engine_report["trend_score"],
        "ema_alignment": ai_engine_report["ema_alignment"],
        "ai_engine": ai_engine_report,
    })

    score_report = final_signal_score(signal, market_context, sr_targets, mtf_context, reversal_reason)
    required_score = MIN_SPOT_FINAL_SCORE if signal.get("type") == "SPOT" else MIN_FUTURES_FINAL_SCORE
    if score_report["final_score"] < required_score:
        return skip_signal(symbol, interval, f"final score {score_report['final_score']} below {required_score}: {score_report['final_score_reason']}")
    signal.update(score_report)
    quality_ok, quality_reason = apply_signal_quality_report(signal)
    if not quality_ok:
        return skip_signal(symbol, interval, quality_reason)
    if _safe_float(signal.get("display_confidence"), 0) < 70:
        calibrated, calibration_reason = apply_b_plus_calibration(signal)
        if not calibrated:
            return skip_signal(symbol, interval, f"display confidence {signal.get('display_confidence')} below 70")
    if signal["final_score"] < required_score:
        return skip_signal(symbol, interval, f"composite final score {signal['final_score']} below {required_score}: {signal.get('confidence_cap_reason')}")

    try:
        from ai_model import explain_predict_trade
        ai_ok, ai_reason = explain_predict_trade(signal)
        if not ai_ok:
            return skip_signal(symbol, interval, f"AI model rejected: {ai_reason}")
    except Exception as e:
        print(f"AI model error in generate_free_signal {symbol} {interval}: {e}")
        return None

    _mark_signal_built(signal)
    return signal


# ================= FREE SIGNALS ONLY =================
def get_top_free_signals(limit=2):
    global LAST_USED_PAIRS
    supply_cap = max(1, int(os.environ.get("MAX_CANDIDATES_PER_SCAN", "6") or 6))
    try:
        limit = max(1, min(int(limit), supply_cap, 10))
    except Exception:
        limit = min(2, supply_cap)

    candidates = []

    scan_symbols = get_scan_symbols()
    print(f"Dynamic symbols loaded: {len(scan_symbols)} symbols")

    for symbol in scan_symbols:
        for tf in TIMEFRAMES:
            try:
                signal = generate_free_signal(symbol, tf)
                if signal:
                    display_conf = _safe_float(signal.get("display_confidence", signal.get("confidence", 0)))
                    opportunity = adaptive_opportunity_score(signal)
                    signal["ranking_score"] = (
                        display_conf
                        + abs(signal["score"] * 2)
                        + max(0, 20 - int(signal.get("risk_score", 50) / 4))
                        + (_safe_float(signal.get("engine_confidence", display_conf)) * 0.18)
                        + (signal.get("multi_timeframe_score", 50) * 0.12)
                        + (signal.get("liquidity_score", 45) * 0.08)
                        + (signal.get("relative_strength_score", 50) * 0.08)
                        + (signal.get("btc_alignment_score", 50) * 0.05)
                        + (opportunity * 0.20)
                        + (6 if signal["volume"] == "STRONG" else 0)
                        + (6 if signal["trend_power"] in ["STRONG_BULL", "STRONG_BEAR"] else 0)
                        + (5 if signal["timeframe"] == "15m" else 0)
                        + (4 if signal["structure"] in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"] else 0)
                        + (3 if signal["smc"] in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"] else 0)
                    )

                    candidates.append(signal)
                    candidate_pipeline_log("CANDIDATE_APPENDED", signal.get("pair"), signal.get("timeframe"), stage="candidate_pool", signal=signal, tier=signal.get("quality_tier") or signal.get("opportunity_tier"))
                    if SIGNAL_DEBUG_LOGS:
                        print(
                            f"CANDIDATE_SIGNAL symbol={signal['pair']} tf={signal['timeframe']} "
                            f"direction={signal['direction']} display_conf={signal.get('display_confidence', signal.get('confidence'))} rr={signal.get('risk_reward')}"
                        )
            except Exception as e:
                print(f"Signal generation error for {symbol} {tf}: {e}")
                continue

    # ================= KEEP BEST SIGNAL ONLY PER PAIR =================
    best_per_pair = {}

    for s in candidates:
        pair = s["pair"]
        if pair not in best_per_pair or s["ranking_score"] > best_per_pair[pair]["ranking_score"]:
            best_per_pair[pair] = s

    candidates = list(best_per_pair.values())

    if not candidates:
        print("Top signals selected: []")
        return []

    candidates = sorted(candidates, key=lambda x: x["ranking_score"], reverse=True)

    top_pool = candidates[:6] if len(candidates) >= 6 else candidates[:]

    # تنويع بسيط بدون تدمير الجودة
    if len(top_pool) > 2:
        shuffled_tail = top_pool[1:]
        random.shuffle(shuffled_tail)
        top_pool = [top_pool[0]] + shuffled_tail

    remaining = [x for x in candidates if x not in top_pool]
    candidates = top_pool + remaining

    best = []
    used_pairs = set()

    # أول محاولة: استبعاد الأزواج المستخدمة مؤخرًا
    for s in candidates:
        if s["pair"] in LAST_USED_PAIRS:
            continue

        if s["pair"] not in used_pairs:
            best.append(s)
            used_pairs.add(s["pair"])
            record_trade_type(s.get("type"))

            LAST_USED_PAIRS.append(s["pair"])
            if len(LAST_USED_PAIRS) > 6:
                LAST_USED_PAIRS.pop(0)

        if len(best) >= limit:
            break

    # لو ماكفوش، رجّع من الباقي عادي
    if len(best) < limit:
        for s in candidates:
            if s["pair"] not in used_pairs:
                best.append(s)
                used_pairs.add(s["pair"])
                record_trade_type(s.get("type"))

            if len(best) >= limit:
                break

    print(f"Top signals selected: {_selected_signal_summary(best)}")
    try:
        _scan_diag_inc("final_signals", len(best))
        for selected in best:
            candidate_pipeline_log(
                "FINAL_SIGNAL_SELECTED",
                selected.get("pair"),
                selected.get("timeframe"),
                stage="selection",
                signal=selected,
                tier=selected.get("quality_tier") or selected.get("opportunity_tier"),
            )
    except Exception:
        pass
    return best

# ================= DRY RUN / SIGNAL HUNTER VERIFICATION =================
def _dry_signal_view(signal):
    """Return a compact, safe representation of a generated signal for dry-run output."""
    if not signal:
        return None
    return {
        "pair": signal.get("pair"),
        "timeframe": signal.get("timeframe"),
        "type": signal.get("type"),
        "direction": signal.get("direction"),
        "entry": signal.get("entry"),
        "tp": signal.get("tp"),
        "sl": signal.get("sl"),
        "support": signal.get("support"),
        "resistance": signal.get("resistance"),
        "risk_reward": signal.get("risk_reward"),
        "final_score": signal.get("final_score"),
        "market_regime": signal.get("market_regime"),
        "setup_type": signal.get("setup_type"),
        "quality_reason": signal.get("signal_quality_reason") or signal.get("final_score_reason"),
    }


def dry_run_signal_scan(symbols=None, timeframes=None, max_passed=10, verbose=True):
    """
    Dry-run the Signal Hunter without Telegram sends or database writes.

    It scans the conservative whitelist, prints PASSED/SKIPPED reasons, and returns
    a summary dict. This function is intentionally top-level so it can be imported:

        python -c "from market_analyzer import dry_run_signal_scan; print(dry_run_signal_scan())"
    """
    selected_symbols = list(symbols or get_scan_symbols())
    selected_timeframes = list(timeframes or TIMEFRAMES)
    summary = {
        "passed_count": 0,
        "skipped_count": 0,
        "errors_count": 0,
        "passed": [],
        "skipped": [],
        "errors": [],
    }

    for symbol in selected_symbols:
        for tf in selected_timeframes:
            before_skip_count = len(LAST_DRY_RUN_SKIPS)
            try:
                signal = generate_signal(symbol, tf)
                if signal:
                    row = _dry_signal_view(signal)
                    summary["passed_count"] += 1
                    summary["passed"].append(row)
                    if verbose:
                        print(
                            "PASSED "
                            f"symbol={row.get('pair')} tf={row.get('timeframe')} "
                            f"type={row.get('type')} dir={row.get('direction')} "
                            f"score={row.get('final_score')} rr={row.get('risk_reward')} "
                            f"regime={row.get('market_regime')} reason={row.get('quality_reason')}"
                        )
                    if len(summary["passed"]) >= max_passed:
                        continue
                else:
                    # Prefer the explicit skip reason captured by skip_signal(). If a
                    # filter returned None without logging, still report a clear generic reason.
                    reason = "filtered by hunter quality gates"
                    if len(LAST_DRY_RUN_SKIPS) > before_skip_count:
                        last = LAST_DRY_RUN_SKIPS[-1]
                        if last.get("symbol") == symbol and last.get("timeframe") == tf:
                            reason = last.get("skip_reason") or reason
                    row = {"symbol": symbol, "timeframe": tf, "reason": reason}
                    summary["skipped_count"] += 1
                    summary["skipped"].append(row)
                    if verbose:
                        print(f"SKIPPED symbol={symbol} tf={tf} reason={reason}")
            except Exception as exc:
                row = {"symbol": symbol, "timeframe": tf, "error": str(exc)}
                summary["errors_count"] += 1
                summary["errors"].append(row)
                if verbose:
                    print(f"ERROR symbol={symbol} tf={tf} error={exc}")

    if verbose:
        print(
            "DRY_RUN_SUMMARY "
            f"passed={summary['passed_count']} skipped={summary['skipped_count']} errors={summary['errors_count']}"
        )
    return summary
