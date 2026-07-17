from datetime import datetime

from .plan_catalog import (
    checkout_url,
    dashboard_url,
    format_money,
    login_link_url,
    public_plans_by_market,
)
from .runtime import PLAN_LABELS
from .subscriptions import VIP_ALL_FOREX_CODE
from .user_entitlements import get_user_entitlements


def _telegram_lang(lang=None):
    value = str(lang or "").lower()
    return "ar" if value.startswith("ar") else "en"


def _money_line(plan, cycle=None):
    cycles = plan.get("billing_cycles") or {}
    if cycle:
        data = cycles.get(cycle) or {}
        return format_money(data.get("price"), data.get("currency", "USD"))
    parts = []
    for name, data in cycles.items():
        parts.append(f"{name.replace('_', ' ').title()}: {format_money(data.get('price'), data.get('currency', 'USD'))}")
    return " | ".join(parts) or "N/A"


def _status(value, lang):
    value = str(value or "not active").lower()
    if lang == "ar":
        return {"active": "نشط", "expired": "منتهي", "not active": "غير نشط"}.get(value, value)
    return value.title()


def _yes(value, lang):
    if lang == "ar":
        return "مفعل" if value else "غير مفعل"
    return "Enabled" if value else "Disabled"


def _signal_types(plan):
    values = plan.get("signal_types") or []
    return ", ".join(values) if values else "N/A"


def should_show_plans_for_text(text):
    value = str(text or "").strip().lower()
    if not value:
        return False
    keywords = {
        "/plans", "/pricing", "/subscribe", "plans", "pricing", "subscribe",
        "subscription", "crypto", "forex", "vip all forex", "price", "prices",
        "الخطط", "الاسعار", "الأسعار", "الاشتراك", "الاشتراكات",
        "فوركس", "الفوركس", "كريبتو", "العملات الرقمية", "العملات",
    }
    return any(keyword in value for keyword in keywords)


def main_menu_payload(user=None, chat_id=None, lang="en"):
    lang = _telegram_lang(lang)
    if lang == "ar":
        text = "🚀 مرحبًا بك في Nexora Trader\n\nاختر ما تريد:"
        keyboard = [
            [{"text": "📈 خطط الكريبتو", "callback_data": "menu:crypto"}],
            [{"text": "💹 خطط الفوركس", "callback_data": "menu:forex"}],
            [{"text": "💎 خطط VIP", "callback_data": "menu:vip"}],
            [{"text": "🆓 التجربة المجانية", "callback_data": "menu:free"}],
            [{"text": "📊 Dashboard", "url": dashboard_url()}],
            [
                {"text": "❓ المساعدة", "callback_data": "menu:help"},
                {"text": "⚙ الحساب", "callback_data": "menu:account"},
            ],
        ]
    else:
        text = "🚀 Welcome to Nexora Trader\n\nChoose what you want:"
        keyboard = [
            [{"text": "📈 Crypto Plans", "callback_data": "menu:crypto"}],
            [{"text": "💹 Forex Plans", "callback_data": "menu:forex"}],
            [{"text": "💎 VIP Plans", "callback_data": "menu:vip"}],
            [{"text": "🆓 Free Trial", "callback_data": "menu:free"}],
            [{"text": "📊 Dashboard", "url": dashboard_url()}],
            [
                {"text": "❓ Help", "callback_data": "menu:help"},
                {"text": "⚙ Account", "callback_data": "menu:account"},
            ],
        ]
    if not user:
        keyboard.insert(0, [{"text": "🔗 Link account" if lang == "en" else "🔗 ربط الحساب", "url": login_link_url(chat_id)}])
    return text, {"inline_keyboard": keyboard}


def command_menu(is_admin=False):
    text = "Nexora command center\n\nUse the buttons below to manage plans, dashboard, help, and account status."
    keyboard = main_menu_payload(lang="en")[1]["inline_keyboard"]
    if is_admin:
        text += "\n\nAdmin: /admin, /admin_stats, /broadcast message"
    return text


def admin_menu():
    return (
        "NEXORA ADMIN\n\n"
        "Available commands:\n"
        "/admin_stats\n"
        "/broadcast message\n"
        "/broadcast_paid message"
    )


def welcome_message(register_link):
    return (
        "🚀 Welcome to Nexora Trader\n\n"
        "Create or connect your account to receive eligible market alerts.\n\n"
        f"{register_link}\n\n"
        "Trading is risky. Signals are analysis, not profit guarantees."
    )


def linked_message(current_plan, expiry, is_admin=False):
    role = "Admin / Owner" if is_admin else "User"
    plan = PLAN_LABELS.get(current_plan, current_plan or "Free Trial")
    return f"✅ Account linked\n\nRole: {role}\nCrypto plan: {plan}\nCrypto expiry: {expiry or 'not active'}"


def active_subscriptions_text(user, lang="en", chat_id=None):
    lang = _telegram_lang(lang)
    ent = get_user_entitlements(user=user, chat_id=chat_id)
    crypto = ent["crypto"]
    forex = ent["forex"]
    if lang == "ar":
        return "\n".join([
            "Your active subscriptions",
            "",
            "Crypto",
            f"الخطة: {crypto['display_name']}",
            f"الحالة: {_status(crypto['status'], lang)}",
            f"الانتهاء: {crypto['expires_at']}",
            f"Spot: {_yes(crypto['can_receive_spot'], lang)}",
            f"Futures: {_yes(crypto['can_receive_futures'], lang)}",
            "",
            "VIP ALL FOREX",
            f"الخطة: {forex['display_name']}",
            f"الحالة: {_status(forex['status'], lang)}",
            f"الانتهاء: {forex['expires_at']}",
            f"Forex signals: {_yes(forex['can_receive_signals'], lang)}",
            f"Telegram linked: {_yes(ent['telegram_linked'], lang)}",
        ])
    return "\n".join([
        "Your active subscriptions",
        "",
        "Crypto",
        f"Plan: {crypto['display_name']}",
        f"Status: {_status(crypto['status'], lang)}",
        f"Expiry: {crypto['expires_at']}",
        f"Spot: {_yes(crypto['can_receive_spot'], lang)}",
        f"Futures: {_yes(crypto['can_receive_futures'], lang)}",
        "",
        "VIP ALL FOREX",
        f"Plan: {forex['display_name']}",
        f"Status: {_status(forex['status'], lang)}",
        f"Expiry: {forex['expires_at']}",
        f"Forex signals: {_yes(forex['can_receive_signals'], lang)}",
        f"Telegram linked: {_yes(ent['telegram_linked'], lang)}",
    ])


def _brief_plan(plan, lang):
    name = plan.get("display_name")
    market = str(plan.get("market_type") or "").upper()
    price = _money_line(plan)
    auto = plan.get("forex_auto_trade_status") if plan.get("plan_code") == VIP_ALL_FOREX_CODE else ("Available" if plan.get("auto_trade") else "Not available")
    if lang == "ar":
        return (
            f"✅ {name}\n"
            f"السوق: {market}\n"
            f"السعر: {price}\n"
            f"الإشارات: {_signal_types(plan)}\n"
            f"Auto Trade: {auto}\n"
            f"مناسب لـ: {plan.get('recommended_for')}"
        )
    return (
        f"✅ {name}\n"
        f"Market: {market}\n"
        f"Price: {price}\n"
        f"Signals: {_signal_types(plan)}\n"
        f"Auto Trade: {auto}\n"
        f"Best for: {plan.get('recommended_for')}"
    )


def telegram_plans_payload(user=None, chat_id=None, lang="en", view="all"):
    lang = _telegram_lang(lang)
    view = str(view or "all").lower()
    crypto = public_plans_by_market("crypto")
    forex = public_plans_by_market("forex")

    if view == "account":
        text = active_subscriptions_text(user, lang, chat_id)
        keyboard = [
            [{"text": "📊 Open dashboard" if lang == "en" else "📊 فتح Dashboard", "url": dashboard_url()}],
            [{"text": "⬅ Back" if lang == "en" else "⬅ رجوع", "callback_data": "menu:home"}],
        ]
        return text, {"inline_keyboard": keyboard}

    if view == "help":
        if lang == "ar":
            text = "❓ المساعدة\n\n• اربط حسابك من Dashboard.\n• اختر الخطة المناسبة.\n• الإشارات تحليل وليست ضمان ربح."
            keyboard = [
                [{"text": "Contact Support", "url": dashboard_url() + "#support"}],
                [{"text": "⬅ رجوع", "callback_data": "menu:home"}],
            ]
        else:
            text = "❓ Help\n\n• Link your account from Dashboard.\n• Choose a plan.\n• Signals are analysis, not profit guarantees."
            keyboard = [
                [{"text": "Contact Support", "url": dashboard_url() + "#support"}],
                [{"text": "⬅ Back", "callback_data": "menu:home"}],
            ]
        return text, {"inline_keyboard": keyboard}

    if view == "free":
        if lang == "ar":
            text = "🆓 التجربة المجانية\n\nأول إشارتين مؤهلتين مجانًا. بعد ذلك يمكن فتح الإشارات عبر Free Earn إذا كانت مفعلة، أو الترقية لخطة مدفوعة."
        else:
            text = "🆓 Free Trial\n\nFirst eligible crypto signals are free. After that, Free Earn unlocks may apply if enabled, or upgrade for direct delivery."
        return text, {"inline_keyboard": [
            [{"text": "📈 Crypto Plans" if lang == "en" else "📈 خطط الكريبتو", "callback_data": "menu:crypto"}],
            [{"text": "⬅ Back" if lang == "en" else "⬅ رجوع", "callback_data": "menu:home"}],
        ]}

    if view == "compare":
        if lang == "ar":
            text = (
                "📊 مقارنة مختصرة\n\n"
                "Crypto: إشارات Spot/Futures للعملات الرقمية.\n"
                "VIP ALL FOREX: فوركس وذهب يدويًا مع فلتر أخبار وسبريد حقيقي.\n"
                "Auto Trade: متاح فقط لبعض خطط الكريبتو. فوركس Auto Trade غير متاح حاليًا.\n\n"
                "اختر حسب السوق الذي تتداوله. هذا ليس نصيحة مالية."
            )
        else:
            text = (
                "📊 Quick comparison\n\n"
                "Crypto: Spot/Futures digital-asset signals.\n"
                "VIP ALL FOREX: manual Forex/Gold signals with news protection and real spread validation.\n"
                "Auto Trade: available only for eligible Crypto plans. Forex Auto Trade is not available.\n\n"
                "Choose by market. This is not financial advice."
            )
        return text, {"inline_keyboard": [
            [{"text": "📈 Crypto Plans" if lang == "en" else "📈 خطط الكريبتو", "callback_data": "menu:crypto"}],
            [{"text": "💹 Forex Plans" if lang == "en" else "💹 خطط الفوركس", "callback_data": "menu:forex"}],
            [{"text": "⬅ Back" if lang == "en" else "⬅ رجوع", "callback_data": "menu:home"}],
        ]}

    selected = crypto if view == "crypto" else forex if view == "forex" else [p for p in crypto + forex if view != "vip" or ("vip" in p.get("plan_code", ""))]
    if lang == "ar":
        title = "📦 الخطط المتاحة"
        intro = "الأسعار والأسماء من نفس كتالوج الموقع. الدفع يتم من صفحة آمنة فقط."
    else:
        title = "📦 Available plans"
        intro = "Names and prices come from the same website catalog. Checkout opens a secure page only."
    text = "\n\n".join([title, intro] + [_brief_plan(plan, lang) for plan in selected])

    keyboard = [
        [
            {"text": "Compare" if lang == "en" else "مقارنة", "callback_data": "menu:compare"},
            {"text": "Account" if lang == "en" else "الحساب", "callback_data": "menu:account"},
        ],
    ]
    if view in {"crypto", "all", "vip"}:
        keyboard.append([
            {"text": "Basic" if lang == "en" else "Basic", "url": checkout_url("basic")},
            {"text": "Pro" if lang == "en" else "Pro", "url": checkout_url("pro")},
        ])
        keyboard.append([
            {"text": "VIP" if lang == "en" else "VIP", "url": checkout_url("vip")},
            {"text": "Pro 2 Years" if lang == "en" else "Pro 2 Years", "url": checkout_url("pro_2y")},
        ])
    if view in {"forex", "all", "vip"}:
        keyboard.append([
            {"text": "Forex Monthly" if lang == "en" else "Forex شهري", "url": checkout_url("vip_all_forex", "monthly")},
            {"text": "Forex Yearly" if lang == "en" else "Forex سنوي", "url": checkout_url("vip_all_forex", "yearly")},
        ])
    if not user:
        keyboard.append([{"text": "🔗 Link account" if lang == "en" else "🔗 ربط الحساب", "url": login_link_url(chat_id)}])
    keyboard.append([{"text": "⬅ Back" if lang == "en" else "⬅ رجوع", "callback_data": "menu:home"}])
    return text, {"inline_keyboard": keyboard}


def plan_explainer_message(lang="en"):
    text, _ = telegram_plans_payload(lang=lang, view="compare")
    return text


def subscription_message(user, lang="en"):
    lang = _telegram_lang(lang)
    if not user:
        if lang == "ar":
            return "⚙ الحساب\n\nلا يوجد حساب مربوط بهذا Telegram. استخدم /start لربط الحساب."
        return "⚙ Account\n\nNo account is linked to this Telegram yet. Use /start to connect securely."
    ent = get_user_entitlements(user=user)
    raw = ent.get("raw_user") or {}
    trades = int(raw.get("trades") or 0)
    bot_active = int(raw.get("bot_active") or 0)
    bot_status = "يعمل" if lang == "ar" and bot_active == 1 else "متوقف" if lang == "ar" else "Running" if bot_active == 1 else "Paused"
    title = "⚙ حالة الحساب" if lang == "ar" else "⚙ Account status"
    free_line = "الإشارات المجانية المستخدمة" if lang == "ar" else "Free signals used"
    return f"{title}\n\n{active_subscriptions_text(user, lang)}\n\n{free_line}: {trades}/2\nBot: {bot_status}"


def user_statistics_message(stats):
    return (
        "NEXORA ACCOUNT STATISTICS\n\n"
        f"Signals used: {stats.get('trades', 0)}\n"
        f"Tracked outcome: {stats.get('profit', 0)} USDT\n"
        f"Affiliate balance: ${stats.get('affiliate_balance', 0)}\n"
        f"Registered referrals: {stats.get('registered_referrals', stats.get('total_referrals', 0))}\n"
        f"Active referrals: {stats.get('active_referrals', 0)}\n"
        f"Paid referrals: {stats.get('paid_referrals', 0)}\n"
        f"Spot signals today: {stats.get('spot_today', 0)}\n"
        f"Futures signals today: {stats.get('futures_today', 0)}\n\n"
        f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


def admin_statistics_message(stats):
    return (
        "NEXORA PLATFORM STATISTICS\n\n"
        f"Users: {stats.get('total_users', 0)}\n"
        f"Paid users: {stats.get('paid_users', 0)}\n"
        f"Linked Telegram users: {stats.get('linked_users', 0)}\n"
        f"Active bots: {stats.get('active_bots', 0)}\n"
        f"Pending withdrawals: {stats.get('pending_withdrawals', 0)}\n\n"
        f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


def broadcast_result_message(sent_count, failed_count, target):
    return f"NEXORA BROADCAST COMPLETE\n\nTarget: {target}\nSent: {sent_count}\nFailed: {failed_count}"
