from datetime import datetime

import psycopg2.extras

from .runtime import (
    AUTO_TRADE_PLANS,
    PLAN_DURATIONS_DAYS,
    PLAN_LABELS,
    db,
    log,
)


VIP_ALL_FOREX_CODE = "vip_all_forex"
VIP_ALL_FOREX_YEARLY_CODE = "vip_all_forex_yearly"
VIP_ALL_FOREX_DISPLAY_NAME = "VIP ALL FOREX"
VIP_ALL_FOREX_MARKET_TYPE = "forex"
CRYPTO_PRODUCT_CODES = {"basic", "pro", "vip", "pro_2y"}
VIP_ALL_FOREX_PAYMENT_CODES = {VIP_ALL_FOREX_CODE, VIP_ALL_FOREX_YEARLY_CODE}


def _as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _own_connection(conn):
    if conn is not None:
        return conn, False
    return db(), True


def ensure_user_subscriptions_table(conn=None):
    conn, should_close = _own_connection(conn)
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product_code TEXT NOT NULL,
                display_name TEXT,
                market_type TEXT,
                status TEXT DEFAULT 'active',
                is_paid INTEGER DEFAULT 0,
                starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NULL,
                payment_provider TEXT,
                payment_reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for column, definition in {
            "user_id": "INTEGER",
            "product_code": "TEXT",
            "display_name": "TEXT",
            "market_type": "TEXT",
            "status": "TEXT DEFAULT 'active'",
            "is_paid": "INTEGER DEFAULT 0",
            "starts_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "expires_at": "TIMESTAMP NULL",
            "payment_provider": "TEXT",
            "payment_reference": "TEXT",
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }.items():
            c.execute(f"ALTER TABLE user_subscriptions ADD COLUMN IF NOT EXISTS {column} {definition}")
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_product_status
            ON user_subscriptions(user_id, product_code, status)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_subscriptions_payment_reference
            ON user_subscriptions(payment_reference)
        """)
        if should_close:
            conn.commit()
    finally:
        if should_close:
            conn.close()


def _row_to_dict(row):
    if not row:
        return None
    if hasattr(row, "get"):
        return dict(row)
    return row


def upsert_user_subscription(
    user_id,
    product_code,
    display_name=None,
    market_type=None,
    status="active",
    is_paid=1,
    starts_at=None,
    expires_at=None,
    payment_provider=None,
    payment_reference=None,
    conn=None,
):
    if not user_id or not product_code:
        return None

    conn, should_close = _own_connection(conn)
    try:
        ensure_user_subscriptions_table(conn)
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        starts_at = starts_at or datetime.utcnow()
        display_name = display_name or PLAN_LABELS.get(product_code, product_code.replace("_", " ").title())
        market_type = market_type or ("forex" if product_code == VIP_ALL_FOREX_CODE else "crypto")
        row = None
        if payment_reference:
            c.execute("""
                SELECT *
                FROM user_subscriptions
                WHERE user_id = %s
                  AND product_code = %s
                  AND payment_reference = %s
                ORDER BY id DESC
                LIMIT 1
            """, (user_id, product_code, str(payment_reference)))
            row = c.fetchone()

        if not row:
            c.execute("""
                SELECT *
                FROM user_subscriptions
                WHERE user_id = %s
                  AND product_code = %s
                  AND status = 'active'
                ORDER BY expires_at DESC NULLS LAST, id DESC
                LIMIT 1
            """, (user_id, product_code))
            row = c.fetchone()

        if row:
            c.execute("""
                UPDATE user_subscriptions
                SET display_name = %s,
                    market_type = %s,
                    status = %s,
                    is_paid = %s,
                    starts_at = COALESCE(starts_at, %s),
                    expires_at = %s,
                    payment_provider = COALESCE(%s, payment_provider),
                    payment_reference = COALESCE(%s, payment_reference),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
            """, (
                display_name,
                market_type,
                status,
                1 if is_paid else 0,
                starts_at,
                expires_at,
                payment_provider,
                str(payment_reference) if payment_reference else None,
                row["id"],
            ))
        else:
            c.execute("""
                INSERT INTO user_subscriptions (
                    user_id, product_code, display_name, market_type, status, is_paid,
                    starts_at, expires_at, payment_provider, payment_reference
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                user_id,
                product_code,
                display_name,
                market_type,
                status,
                1 if is_paid else 0,
                starts_at,
                expires_at,
                payment_provider,
                str(payment_reference) if payment_reference else None,
            ))
        result = c.fetchone()
        if should_close:
            conn.commit()
        return _row_to_dict(result)
    finally:
        if should_close:
            conn.close()


def activate_vip_all_forex(user_id, expires_at, payment_provider="manual", payment_reference=None, conn=None):
    return upsert_user_subscription(
        user_id=user_id,
        product_code=VIP_ALL_FOREX_CODE,
        display_name=VIP_ALL_FOREX_DISPLAY_NAME,
        market_type=VIP_ALL_FOREX_MARKET_TYPE,
        status="active",
        is_paid=1,
        expires_at=expires_at,
        payment_provider=payment_provider,
        payment_reference=payment_reference,
        conn=conn,
    )


def get_user_active_subscriptions(user_id, conn=None):
    if not user_id:
        return []
    conn, should_close = _own_connection(conn)
    try:
        ensure_user_subscriptions_table(conn)
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT *
            FROM user_subscriptions
            WHERE user_id = %s
              AND status = 'active'
              AND COALESCE(is_paid, 0) = 1
              AND (expires_at IS NULL OR expires_at >= NOW())
            ORDER BY created_at DESC, id DESC
        """, (user_id,))
        return [dict(row) for row in (c.fetchall() or [])]
    finally:
        if should_close:
            conn.close()


def get_user_latest_subscription(user_id, product_code=None, market_type=None, conn=None):
    """Return the latest subscription row for display, including expired rows.

    This is intentionally not used for delivery entitlement. Signal eligibility
    must continue to use get_user_active_subscriptions / has_active_subscription.
    """
    if not user_id:
        return None
    conn, should_close = _own_connection(conn)
    try:
        ensure_user_subscriptions_table(conn)
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        filters = ["user_id = %s"]
        params = [user_id]
        if product_code:
            filters.append("product_code = %s")
            params.append(str(product_code))
        if market_type:
            filters.append("market_type = %s")
            params.append(str(market_type))
        c.execute(f"""
            SELECT *,
                   CASE
                     WHEN status = 'active' AND (expires_at IS NULL OR expires_at >= NOW()) THEN 'active'
                     WHEN expires_at IS NOT NULL AND expires_at < NOW() THEN 'expired'
                     ELSE COALESCE(status, 'not active')
                   END AS display_status
            FROM user_subscriptions
            WHERE {' AND '.join(filters)}
            ORDER BY expires_at DESC NULLS LAST, updated_at DESC NULLS LAST, id DESC
            LIMIT 1
        """, tuple(params))
        return _row_to_dict(c.fetchone())
    finally:
        if should_close:
            conn.close()


def has_active_subscription(user_id, product_code, conn=None):
    return any(row.get("product_code") == product_code for row in get_user_active_subscriptions(user_id, conn))


def has_active_market_subscription(user_id, market_type, conn=None):
    market = str(market_type or "").strip().lower()
    return any(str(row.get("market_type") or "").strip().lower() == market for row in get_user_active_subscriptions(user_id, conn))


def legacy_crypto_subscription_from_user(user):
    if not user:
        return None
    plan = str(user.get("plan") or "trial").strip().lower()
    if plan not in CRYPTO_PRODUCT_CODES:
        return None
    expiry = user.get("expiry")
    is_paid = int(user.get("is_paid") or 0) == 1
    lifetime_owner = int(user.get("lifetime_owner") or 0) == 1
    if not is_paid and not lifetime_owner:
        return None
    return {
        "product_code": plan,
        "display_name": PLAN_LABELS.get(plan, plan.title()),
        "market_type": "crypto",
        "status": "active",
        "is_paid": 1,
        "starts_at": None,
        "expires_at": expiry,
        "payment_provider": "legacy_users_plan",
        "payment_reference": None,
    }


def get_user_subscription_cards(user, conn=None):
    cards = []
    legacy = legacy_crypto_subscription_from_user(user)
    if legacy:
        cards.append(legacy)
    user_id = user.get("id") if user else None
    cards.extend(get_user_active_subscriptions(user_id, conn) if user_id else [])
    latest_forex = get_user_latest_subscription(user_id, market_type=VIP_ALL_FOREX_MARKET_TYPE, conn=conn) if user_id else None
    if latest_forex and not any(card.get("product_code") in VIP_ALL_FOREX_PAYMENT_CODES for card in cards):
        latest_forex["status"] = latest_forex.get("display_status") or latest_forex.get("status") or "not active"
        latest_forex["display_only"] = True
        cards.append(latest_forex)
    seen = set()
    unique_cards = []
    for card in cards:
        code = card.get("product_code")
        if code in seen:
            continue
        seen.add(code)
        unique_cards.append(card)
    return unique_cards


def get_user_market_capabilities(user_id, user=None, conn=None):
    plan = str((user or {}).get("plan") or "trial").strip().lower()
    has_crypto = plan in {"trial", "basic", "pro", "vip", "pro_2y"}
    has_forex = has_active_market_subscription(user_id, VIP_ALL_FOREX_MARKET_TYPE, conn) if user_id else False
    return {
        "can_receive_crypto": has_crypto,
        "can_receive_forex": has_forex,
        "can_receive_metals": has_forex,
        "can_receive_indices": has_forex,
        "can_receive_oil": has_forex,
        "can_auto_trade_crypto": plan in AUTO_TRADE_PLANS,
        "can_auto_trade_forex": False,
        "forex_auto_trade_status": "Disabled until MT5/exchange execution is verified",
    }


def get_subscription_duration_days(product_code):
    return PLAN_DURATIONS_DAYS.get(product_code) or 365


def is_vip_all_forex_payment_code(product_code):
    return str(product_code or "").strip().lower() in VIP_ALL_FOREX_PAYMENT_CODES


def format_subscriptions_for_telegram(user, conn=None):
    cards = get_user_subscription_cards(user, conn)
    if not cards:
        plan = user.get("plan") if user else "trial"
        return [
            f"Crypto access: {PLAN_LABELS.get(plan, plan or 'Free Trial')}",
            "VIP ALL FOREX: Not active",
        ]
    lines = []
    for card in cards:
        expires = card.get("expires_at") or "No expiry"
        market = str(card.get("market_type") or "crypto").upper()
        status = card.get("display_status") or card.get("status") or "not active"
        lines.append(f"- {card.get('display_name') or card.get('product_code')} ({market}) status: {status}, expires: {expires}")
    if not any(card.get("product_code") in VIP_ALL_FOREX_PAYMENT_CODES for card in cards):
        lines.append("- VIP ALL FOREX: Not active")
    return lines
