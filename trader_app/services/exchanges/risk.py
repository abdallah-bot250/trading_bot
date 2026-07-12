"""Server-side risk policy helpers for auto trade."""


DEFAULT_AUTO_TRADE_SETTINGS = {
    "mode": "balanced",
    "risk_per_trade": 1.0,
    "max_trade_size": 25.0,
    "max_daily_trades": 4,
    "max_daily_loss": 0.0,
    "max_daily_loss_percent": 4.0,
    "max_open_positions": 2,
    "max_leverage": 3,
    "pair_cooldown_minutes": 45,
    "consecutive_loss_limit": 2,
    "emergency_stop": 0,
    "stop_loss_required": 1,
    "take_profit_required": 1,
    "allowed_pairs": "",
    "blocked_pairs": "",
    "trading_session_hours": "",
}


def normalize_auto_trade_mode(value):
    mode = str(value or "balanced").strip().lower()
    if mode not in {"conservative", "balanced", "expert", "manual_confirm", "full_auto"}:
        return "balanced"
    return mode


def mode_risk_multiplier(mode):
    mode = normalize_auto_trade_mode(mode)
    return {
        "conservative": 0.5,
        "balanced": 1.0,
        "expert": 1.15,
        "manual_confirm": 0.75,
        "full_auto": 1.0,
    }.get(mode, 1.0)


def sanitize_float(value, default, min_value=0.0, max_value=None):
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    parsed = max(min_value, parsed)
    if max_value is not None:
        parsed = min(max_value, parsed)
    return parsed


def sanitize_int(value, default, min_value=0, max_value=None):
    try:
        parsed = int(float(value))
    except Exception:
        parsed = default
    parsed = max(min_value, parsed)
    if max_value is not None:
        parsed = min(max_value, parsed)
    return parsed

