import os
from copy import deepcopy

from .runtime import PLAN_DURATIONS_DAYS, PLAN_LABELS, PLAN_ORIGINAL_PRICES, PLAN_PRICES, current_base_url


SUPPORTED_FOREX_ASSETS = [
    "Major Forex pairs",
    "Gold/Silver when the active provider supports fresh real pricing",
]


def _price(plan_code):
    value = PLAN_PRICES.get(plan_code)
    return float(value) if value is not None else None


def _original_price(plan_code):
    value = PLAN_ORIGINAL_PRICES.get(plan_code)
    return float(value) if value is not None else None


def _duration(plan_code):
    return int(PLAN_DURATIONS_DAYS.get(plan_code) or 30)


PLAN_CATALOG = {
    "trial": {
        "plan_code": "trial",
        "display_name": PLAN_LABELS.get("trial", "Free Trial"),
        "market_type": "crypto",
        "billing_cycles": {"lifetime_trial": {"price": 0, "currency": "USD", "duration_days": 0}},
        "signal_types": ["Spot", "Futures"],
        "signal_level": "First eligible free signals, then Free Earn unlocks when configured.",
        "auto_trade": False,
        "trial": True,
        "features": [
            "First eligible crypto signals are free",
            "Rewarded unlock lane for eligible future signals",
            "Dashboard tracking",
        ],
        "active": True,
        "publicly_visible": True,
        "recommended_for": "New users testing Nexora before upgrading.",
        "disclaimer": "Signals depend on market quality and are not guaranteed.",
        "checkout_code": "trial",
    },
    "basic": {
        "plan_code": "basic",
        "display_name": PLAN_LABELS.get("basic", "Basic"),
        "market_type": "crypto",
        "billing_cycles": {"monthly": {"price": _price("basic"), "currency": "USD", "duration_days": _duration("basic")}},
        "signal_types": ["Spot", "Futures"],
        "signal_level": "Direct crypto signal access with standard filtering.",
        "auto_trade": False,
        "trial": False,
        "features": ["Ad-free Telegram delivery", "Spot/Futures signal eligibility", "Dashboard history"],
        "active": True,
        "publicly_visible": True,
        "recommended_for": "Users who want direct crypto alerts without ads.",
        "disclaimer": "No fixed daily signal count is promised.",
        "checkout_code": "basic",
    },
    "pro": {
        "plan_code": "pro",
        "display_name": PLAN_LABELS.get("pro", "Pro"),
        "market_type": "crypto",
        "billing_cycles": {"monthly": {"price": _price("pro"), "currency": "USD", "duration_days": _duration("pro")}},
        "signal_types": ["Spot", "Futures"],
        "signal_level": "Higher crypto access with stronger analysis context.",
        "auto_trade": False,
        "trial": False,
        "features": ["Advanced crypto signal access", "Confidence and risk context", "Priority direct delivery"],
        "active": True,
        "publicly_visible": True,
        "recommended_for": "Active crypto traders who want stronger filtered setups.",
        "disclaimer": "Trading is risky. Signals support decision-making only.",
        "checkout_code": "pro",
    },
    "vip": {
        "plan_code": "vip",
        "display_name": PLAN_LABELS.get("vip", "Elite"),
        "market_type": "crypto",
        "billing_cycles": {"monthly": {"price": _price("vip"), "currency": "USD", "duration_days": _duration("vip")}},
        "signal_types": ["Spot", "Futures"],
        "signal_level": "Elite crypto access with eligible automation controls.",
        "auto_trade": True,
        "trial": False,
        "features": ["Elite crypto delivery", "Bybit-ready auto-trade controls for eligible users", "Risk controls"],
        "active": True,
        "publicly_visible": True,
        "recommended_for": "Experienced crypto users who want premium access and automation controls.",
        "disclaimer": "Auto Trade requires user API setup and risk controls.",
        "checkout_code": "vip",
    },
    "pro_2y": {
        "plan_code": "pro_2y",
        "display_name": PLAN_LABELS.get("pro_2y", "Pro 2 Years"),
        "market_type": "crypto",
        "billing_cycles": {"two_years": {"price": _price("pro_2y"), "currency": "USD", "duration_days": _duration("pro_2y")}},
        "signal_types": ["Spot", "Futures"],
        "signal_level": "Highest long-term crypto access.",
        "auto_trade": True,
        "trial": False,
        "features": ["Highest crypto access", "Long-term ad-free delivery", "Auto-trade controls for eligible users"],
        "active": True,
        "publicly_visible": True,
        "recommended_for": "Long-term crypto users who want maximum crypto access.",
        "disclaimer": "Availability still depends on real market conditions.",
        "checkout_code": "pro_2y",
    },
    "vip_all_forex": {
        "plan_code": "vip_all_forex",
        "display_name": PLAN_LABELS.get("vip_all_forex", "VIP ALL FOREX"),
        "market_type": "forex",
        "billing_cycles": {
            "monthly": {"price": _price("vip_all_forex"), "original_price": _original_price("vip_all_forex"), "currency": "USD", "duration_days": _duration("vip_all_forex")},
            "yearly": {"price": _price("vip_all_forex_yearly"), "original_price": _original_price("vip_all_forex_yearly"), "currency": "USD", "duration_days": _duration("vip_all_forex_yearly"), "checkout_code": "vip_all_forex_yearly"},
        },
        "signal_types": ["Forex", "Gold/Silver"],
        "supported_assets": SUPPORTED_FOREX_ASSETS,
        "analysis": [
            "4H and 1H trend context",
            "15m/5m entry refinement",
            "Market structure",
            "Pullback/retest logic",
            "Support and resistance",
            "ATR volatility filter",
            "RSI/MACD confirmation",
            "Real Bid/Ask spread validation",
            "Economic-news filter",
        ],
        "signal_content": ["Entry", "Stop Loss", "TP1/TP2/TP3", "Risk/Reward", "Entry reason", "News status", "Data time/source"],
        "signal_level": "Forex-only signals with real spread and news protection.",
        "auto_trade": False,
        "forex_auto_trade_status": "Not available",
        "trial": False,
        "features": ["Major Forex pair analysis", "Gold/Silver when provider verified", "Economic-news protection", "Manual trading signals"],
        "active": True,
        "publicly_visible": True,
        "recommended_for": "Manual Forex and gold traders who want filtered entries with news protection.",
        "disclaimer": "Forex signals are analysis only and do not guarantee profit.",
        "checkout_code": "vip_all_forex",
    },
}


def all_plans(include_hidden=False):
    plans = [deepcopy(plan) for plan in PLAN_CATALOG.values()]
    if include_hidden:
        return plans
    return [plan for plan in plans if plan.get("active") and plan.get("publicly_visible")]


def public_plans_by_market(market_type=None):
    plans = all_plans(False)
    if market_type:
        market_type = str(market_type).lower()
        plans = [plan for plan in plans if plan.get("market_type") == market_type]
    return plans


def get_plan(plan_code):
    code = str(plan_code or "").strip().lower()
    if code == "vip_all_forex_yearly":
        plan = deepcopy(PLAN_CATALOG.get("vip_all_forex"))
        if plan:
            plan["plan_code"] = "vip_all_forex_yearly"
            plan["display_name"] = PLAN_LABELS.get("vip_all_forex_yearly", "VIP ALL FOREX Yearly")
            plan["checkout_code"] = "vip_all_forex_yearly"
            plan["billing_cycles"] = {"yearly": plan.get("billing_cycles", {}).get("yearly", {})}
        return plan
    return deepcopy(PLAN_CATALOG.get(code))


def get_checkout_code(plan_code, cycle=None):
    plan = get_plan(plan_code)
    if not plan:
        return None
    if cycle and cycle in plan.get("billing_cycles", {}):
        return plan["billing_cycles"][cycle].get("checkout_code") or plan.get("checkout_code")
    return plan.get("checkout_code")


def format_money(value, currency="USD"):
    if value is None:
        return "configured on website"
    amount = int(value) if float(value).is_integer() else round(float(value), 2)
    return f"${amount} {currency}"


def checkout_url(plan_code, cycle=None):
    checkout_code = get_checkout_code(plan_code, cycle) or plan_code
    return f"{current_base_url()}/manual-payment/{checkout_code}"


def dashboard_url():
    return f"{current_base_url()}/dashboard"


def login_link_url(chat_id=None):
    suffix = f"?chat_id={chat_id}" if chat_id else ""
    return f"{current_base_url()}/login{suffix}"


def plan_catalog_digest():
    return {
        plan["plan_code"]: {
            "name": plan["display_name"],
            "market_type": plan["market_type"],
            "billing_cycles": plan["billing_cycles"],
            "active": plan["active"],
            "publicly_visible": plan["publicly_visible"],
        }
        for plan in all_plans(True)
    }
