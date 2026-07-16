from datetime import date, datetime

import psycopg2.extras

from .runtime import AUTO_TRADE_PLANS, PLAN_LABELS, db, log
from .subscriptions import (
    VIP_ALL_FOREX_CODE,
    get_user_active_subscriptions,
)


CRYPTO_PLAN_CODES = {"trial", "basic", "pro", "vip", "pro_2y"}


def _as_dict(row):
    if not row:
        return {}
    if hasattr(row, "get"):
        return dict(row)
    return dict(row)


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt)
        except Exception:
            continue
    return None


def _is_lifetime(user):
    try:
        return int((user or {}).get("lifetime_owner") or 0) == 1
    except Exception:
        return False


def _expiry_status(expires_at, lifetime=False):
    if lifetime:
        return True, "Lifetime"
    parsed = _parse_datetime(expires_at)
    if not parsed:
        return False, "not active"
    if parsed >= datetime.utcnow():
        return True, parsed.strftime("%Y-%m-%d")
    return False, parsed.strftime("%Y-%m-%d")


def _safe_bool(value):
    try:
        return int(value or 0) == 1
    except Exception:
        return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_user(user_id=None, chat_id=None, email=None, conn=None):
    if user_id is None and not chat_id and not email:
        return {}
    should_close = False
    if conn is None:
        conn = db()
        should_close = True
    try:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_id is not None:
            c.execute("SELECT * FROM users WHERE id = %s LIMIT 1", (user_id,))
        elif chat_id:
            c.execute("SELECT * FROM users WHERE chat_id = %s ORDER BY id DESC LIMIT 1", (str(chat_id),))
        else:
            c.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(%s) ORDER BY id DESC LIMIT 1", (email,))
        return dict(c.fetchone() or {})
    except Exception as exc:
        log(f"USER_ENTITLEMENTS_USER_LOAD_FAILED reason={exc}")
        return {}
    finally:
        if should_close:
            conn.close()


def _crypto_entitlement(user):
    plan = str((user or {}).get("plan") or "trial").strip().lower()
    if plan not in CRYPTO_PLAN_CODES:
        plan = "trial"
    is_trial = plan == "trial"
    lifetime = _is_lifetime(user)
    paid = _safe_bool((user or {}).get("is_paid")) or lifetime
    active_by_expiry, expiry_label = _expiry_status((user or {}).get("expiry"), lifetime=lifetime)
    active = is_trial or (paid and active_by_expiry)
    expired = (not is_trial) and paid and not active_by_expiry
    spot_enabled = _safe_bool((user or {}).get("spot_enabled", 1))
    futures_enabled = _safe_bool((user or {}).get("futures_enabled", 1))
    return {
        "active": bool(active),
        "expired": bool(expired),
        "plan_code": plan,
        "display_name": PLAN_LABELS.get(plan, plan.replace("_", " ").title()),
        "starts_at": None,
        "expires_at": expiry_label,
        "lifetime": bool(lifetime),
        "can_receive_spot": bool(active and spot_enabled),
        "can_receive_futures": bool(active and futures_enabled),
        "can_use_auto_trade": bool(active and plan in AUTO_TRADE_PLANS),
        "status": "active" if active else "expired" if expired else "not active",
    }


def _forex_entitlement_from_rows(rows):
    forex_rows = [
        row for row in rows
        if str(row.get("product_code") or "").strip().lower() == VIP_ALL_FOREX_CODE
        or str(row.get("market_type") or "").strip().lower() == "forex"
    ]
    if not forex_rows:
        return {
            "active": False,
            "expired": False,
            "plan_code": None,
            "display_name": "VIP ALL FOREX",
            "starts_at": None,
            "expires_at": "not active",
            "lifetime": False,
            "can_receive_signals": False,
            "auto_trade_enabled": False,
            "status": "not active",
        }
    selected = forex_rows[0]
    lifetime = not selected.get("expires_at")
    active_by_expiry, expiry_label = _expiry_status(selected.get("expires_at"), lifetime=lifetime)
    active = str(selected.get("status") or "").lower() == "active" and _safe_bool(selected.get("is_paid")) and active_by_expiry
    return {
        "active": bool(active),
        "expired": bool(not active and bool(selected.get("expires_at"))),
        "plan_code": selected.get("product_code") or VIP_ALL_FOREX_CODE,
        "display_name": selected.get("display_name") or "VIP ALL FOREX",
        "starts_at": selected.get("starts_at"),
        "expires_at": expiry_label,
        "lifetime": bool(lifetime),
        "can_receive_signals": bool(active),
        "auto_trade_enabled": False,
        "status": "active" if active else "expired",
    }


def _forex_entitlement(user_id, conn=None, rows=None):
    if rows is None:
        try:
            rows = get_user_active_subscriptions(user_id, conn) if user_id else []
        except Exception as exc:
            log(f"USER_ENTITLEMENTS_FOREX_LOAD_FAILED user_id={user_id} reason={exc}")
            rows = []
    return _forex_entitlement_from_rows(rows)


def get_user_entitlements(user=None, user_id=None, chat_id=None, email=None, conn=None):
    loaded = _as_dict(user)
    if not loaded:
        loaded = _load_user(user_id=user_id, chat_id=chat_id, email=email, conn=conn)
    user_id = loaded.get("id") or loaded.get("user_id") or user_id
    chat_id = loaded.get("chat_id") or chat_id
    crypto = _crypto_entitlement(loaded)
    injected_rows = loaded.get("subscription_cards") if isinstance(loaded.get("subscription_cards"), list) else None
    forex = _forex_entitlement(user_id, conn, rows=injected_rows)
    return {
        "user_id": user_id,
        "email": loaded.get("email") or email,
        "role": "Admin" if _safe_bool(loaded.get("is_admin")) else "User",
        "telegram_linked": bool(chat_id),
        "telegram_active": _safe_bool(loaded.get("bot_active", 1)),
        "crypto": crypto,
        "forex": forex,
        "raw_user": loaded,
    }


def delivery_eligibility_for_signal(user=None, signal_market="crypto", user_id=None, chat_id=None, conn=None):
    ent = get_user_entitlements(user=user, user_id=user_id, chat_id=chat_id, conn=conn)
    market = str(signal_market or "crypto").lower()
    if not ent["telegram_linked"]:
        return ent, False, "missing_chat_id"
    if market == "forex":
        if ent["forex"]["can_receive_signals"]:
            return ent, True, "eligible"
        return ent, False, "vip_all_forex_required"
    crypto = ent["crypto"]
    if crypto["can_receive_spot"] or crypto["can_receive_futures"]:
        return ent, True, "eligible"
    return ent, False, crypto.get("status") or "crypto_inactive"


def log_delivery_eligibility(user, signal_market, eligible, reason, conn=None):
    try:
        ent = get_user_entitlements(user=user, conn=conn)
        log(
            "DELIVERY_ELIGIBILITY "
            f"user_id={ent.get('user_id') or ''} "
            f"market={signal_market} "
            f"telegram_linked={ent.get('telegram_linked')} "
            f"crypto_active={ent['crypto']['active']} "
            f"forex_active={ent['forex']['active']} "
            f"crypto_eligible={ent['crypto']['can_receive_spot'] or ent['crypto']['can_receive_futures']} "
            f"forex_eligible={ent['forex']['can_receive_signals']} "
            f"eligible={bool(eligible)} "
            f"reason={reason or ''}"
        )
    except Exception:
        pass
