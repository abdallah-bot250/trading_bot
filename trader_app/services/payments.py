import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta

from .runtime import PLAN_LABELS, PLAN_PRICES


SUCCESS_STATUSES = {"finished", "confirmed"}
FAILED_STATUSES = {"failed", "expired", "refunded", "partially_paid"}
PENDING_STATUSES = {"waiting", "confirming", "sending"}

COMMISSION_RATES = {
    "basic": 0.08,
    "pro": 0.12,
    "vip": 0.15,
    "ultimate": 0.20,
}


def normalize_plan(plan):
    plan = str(plan or "basic").strip().lower()
    return plan if plan in PLAN_PRICES else "basic"


def normalize_coupon_code(value):
    value = str(value or "").strip().upper()
    value = re.sub(r"[^A-Z0-9_-]", "", value)
    return value[:40]


def webhook_signature_payload(data):
    return json.dumps(data or {}, sort_keys=True, separators=(",", ":"))


def generate_nowpayments_signature(data, ipn_secret):
    return hmac.new(
        key=str(ipn_secret or "").encode("utf-8"),
        msg=webhook_signature_payload(data).encode("utf-8"),
        digestmod=hashlib.sha512,
    ).hexdigest()


def validate_nowpayments_signature(data, signature, ipn_secret):
    if not signature or not ipn_secret:
        return False, ""

    generated = generate_nowpayments_signature(data, ipn_secret)
    return hmac.compare_digest(str(signature).lower(), generated.lower()), generated


def coupon_is_active(row, now=None):
    if not row:
        return False, "not_found"

    now = now or datetime.now()
    active = int(row[2] or 0)
    expires_at = row[3]
    max_redemptions = row[4]
    redemption_count = int(row[5] or 0)

    if active != 1:
        return False, "inactive"

    if expires_at:
        try:
            expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00")).replace(tzinfo=None)
            if expiry < now:
                return False, "expired"
        except ValueError:
            return False, "bad_expiry"

    if max_redemptions is not None and redemption_count >= int(max_redemptions):
        return False, "limit_reached"

    return True, "ok"


def apply_coupon_amount(plan, coupon_row):
    original_amount = float(PLAN_PRICES[plan])
    if not coupon_row:
        return original_amount, 0.0, original_amount

    discount_percent = max(0.0, min(float(coupon_row[1] or 0), 95.0))
    discount_amount = round(original_amount * discount_percent / 100.0, 2)
    final_amount = round(max(original_amount - discount_amount, 1.0), 2)
    return original_amount, discount_amount, final_amount


def calculate_subscription_expiry(current_expiry, days=30, now=None):
    if str(current_expiry or "").strip().lower() == "lifetime":
        return "lifetime", False

    now = now or datetime.now()
    base_date = now
    if current_expiry:
        try:
            parsed = datetime.strptime(str(current_expiry)[:10], "%Y-%m-%d")
            if parsed > now:
                base_date = parsed
        except ValueError:
            base_date = now

    return (base_date + timedelta(days=days)).strftime("%Y-%m-%d"), base_date > now


def calculate_commission(plan, amount=None):
    plan = normalize_plan(plan)
    gross_amount = float(amount if amount is not None else PLAN_PRICES[plan])
    rate = float(COMMISSION_RATES.get(plan, COMMISSION_RATES["basic"]))
    return round(gross_amount * rate, 2), rate


def payment_status_bucket(status):
    status = str(status or "").strip().lower()
    if status in SUCCESS_STATUSES:
        return "success"
    if status in FAILED_STATUSES:
        return "failed"
    if status in PENDING_STATUSES:
        return "pending"
    return "unknown"
