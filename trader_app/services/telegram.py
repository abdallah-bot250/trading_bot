from datetime import datetime

from .runtime import send, format_signal, telegram_referral_link, ensure_user_has_referral_code, generate_referral_code


def command_menu(is_admin=False):
    lines = [
        "Nexora AI Trader",
        "",
        "الأوامر المتاحة:",
        "/start - ربط الحساب واستقبال أول الإشارات",
        "/subscription - حالة الاشتراك والخطة",
        "/stats - إحصائيات حسابك",
        "/affiliate - رابط الأفلييت والرصيد",
        "/help - عرض هذه القائمة",
    ]
    if is_admin:
        lines.extend([
            "",
            "Admin Commands:",
            "/admin - لوحة أوامر الأدمن",
            "/admin_stats - إحصائيات عامة",
            "/broadcast الرسالة - إرسال لكل الحسابات المرتبطة",
            "/broadcast_paid الرسالة - إرسال للمشتركين المدفوعين فقط",
        ])
    return "\n".join(lines)


def admin_menu():
    return """Nexora Admin Console

الأوامر:
/admin_stats
/broadcast الرسالة
/broadcast_paid الرسالة

تنبيه: أوامر البث لا تعمل إلا من حساب أدمن مربوط بنفس Telegram."""


def welcome_message(register_link):
    return f"""أهلاً بك في Nexora AI Trader

البوت يفلتر السوق ويرسل الفرص الأقوى فقط، بدل الدخول العشوائي.

يركز على:
- Trend
- Volume
- Multi-timeframe confirmation
- Risk score
- Spot/Futures quality scoring

عندك صفقتين مجانيتين بعد التسجيل.

اربط حسابك من هنا:
{register_link}

بعد التسجيل ابعت /start لاستقبال أول الإشارات."""


def linked_message(current_plan, expiry, is_admin=False):
    role = "Admin / Owner" if is_admin else "User"
    return f"""حسابك مربوط بنجاح

Role: {role}
Plan: {current_plan or 'trial'}
Expiry: {expiry or 'not active'}

استخدم /subscription لمعرفة حالة اشتراكك.
استخدم /stats لمتابعة إحصائياتك."""


def subscription_message(user):
    if not user:
        return "لا يوجد حساب مربوط بهذا Telegram. استخدم /start ثم سجل من الرابط الآمن."

    plan = user.get("plan") or "trial"
    expiry = user.get("expiry") or "not active"
    is_paid = int(user.get("is_paid") or 0)
    trades = int(user.get("trades") or 0)
    bot_active = int(user.get("bot_active") or 0)
    spot_enabled = int(user.get("spot_enabled", 1) if user.get("spot_enabled") is not None else 1)
    futures_enabled = int(user.get("futures_enabled", 1) if user.get("futures_enabled") is not None else 1)

    status = "Active" if is_paid == 1 or str(expiry).lower() == "lifetime" else "Trial / inactive"
    bot_status = "Running" if bot_active == 1 else "Stopped"

    return f"""Subscription Status

Plan: {plan}
Status: {status}
Expiry: {expiry}
Trial signals used: {trades}/2
Bot: {bot_status}
Spot Signals: {'Enabled' if spot_enabled else 'Paused'}
Futures Signals: {'Enabled' if futures_enabled else 'Paused'}

لو عايز تغير Spot/Futures افتح Dashboard ثم Settings."""


def user_statistics_message(stats):
    return f"""Account Statistics

Signals used: {stats.get('trades', 0)}
Profit: {stats.get('profit', 0)} USDT
Affiliate balance: ${stats.get('affiliate_balance', 0)}
Total referrals: {stats.get('total_referrals', 0)}
Spot signals today: {stats.get('spot_today', 0)}
Futures signals today: {stats.get('futures_today', 0)}
Spot win rate: {stats.get('spot_win_rate', 0)}%
Futures win rate: {stats.get('futures_win_rate', 0)}%

Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""


def admin_statistics_message(stats):
    return f"""Platform Statistics

Users: {stats.get('total_users', 0)}
Paid users: {stats.get('paid_users', 0)}
Linked Telegram users: {stats.get('linked_users', 0)}
Active bots: {stats.get('active_bots', 0)}
Starter: {stats.get('starter_users', 0)}
Pro: {stats.get('pro_users', 0)}
Elite: {stats.get('elite_users', 0)}
Pending withdrawals: {stats.get('pending_withdrawals', 0)}

Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""


def broadcast_result_message(sent_count, failed_count, target):
    return f"""Broadcast Complete

Target: {target}
Sent: {sent_count}
Failed: {failed_count}"""
