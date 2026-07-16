from datetime import datetime

from .plan_catalog import (
    checkout_url,
    dashboard_url,
    format_money,
    login_link_url,
    public_plans_by_market,
)
from .runtime import PLAN_LABELS, send
from .subscriptions import (
    VIP_ALL_FOREX_CODE,
    get_user_market_capabilities,
    get_user_subscription_cards,
)


def command_menu(is_admin=False):
    lines = [
        "NEXORA COMMAND CENTER",
        "",
        "Account commands:",
        "/start - Connect your account and check access",
        "/subscription - View plan and access status",
        "/plans - Compare Crypto and Forex plans",
        "/subscribe - Open subscription options",
        "/stats - View account statistics",
        "/affiliate - View referrals and commission balance",
        "/help - Show this menu",
    ]
    if is_admin:
        lines.extend([
            "",
            "Admin commands:",
            "/admin - Open the admin command menu",
            "/admin_stats - View platform statistics",
            "/broadcast message - Send to linked users",
            "/broadcast_paid message - Send to paid users only",
        ])
    lines.extend([
        "",
        "Risk warning: Trading involves risk. Nexora signals support decision-making and do not guarantee profit.",
    ])
    return "\n".join(lines)


def admin_menu():
    return """NEXORA ADMIN CONSOLE

Commands:
/admin_stats
/broadcast message
/broadcast_paid message

Broadcast commands are protected and available only to an authorized admin Telegram account."""


def welcome_message(register_link):
    return f"""NEXORA AI TRADER

Welcome. Nexora filters the market and delivers qualified opportunities only when market conditions are suitable.

What Nexora reviews:
- Trend and market structure
- Volume and liquidity
- Multi-timeframe alignment
- Entry quality and risk
- Spot/Futures signal suitability

Your free plan includes the first eligible free signals after registration.

Create or connect your account:
{register_link}

After registration, send /start again to complete account linking."""


def linked_message(current_plan, expiry, is_admin=False):
    role = "Admin / Owner" if is_admin else "User"
    return f"""NEXORA AI TRADER

Account connected successfully.

Role: {role}
Plan: {PLAN_LABELS.get(current_plan, current_plan or 'Free Trial')}
Expiry: {expiry or 'not active'}

Use /subscription to review your active Crypto and Forex subscriptions.
Use /plans to compare available plans.

Risk warning: Trading involves risk. Nexora signals support decision-making and do not guarantee profit."""


def _telegram_lang(lang=None):
    value = str(lang or "").lower()
    return "ar" if value.startswith("ar") else "en"


def should_show_plans_for_text(text):
    value = str(text or "").strip().lower()
    if not value:
        return False
    keywords = [
        "/plans",
        "/pricing",
        "/subscribe",
        "plans",
        "pricing",
        "subscribe",
        "subscription",
        "crypto",
        "forex",
        "الخطط",
        "الاسعار",
        "الأسعار",
        "الاشتراك",
        "الاشتراكات",
        "فوركس",
        "كريبتو",
        "العملات الرقمية",
    ]
    return any(keyword in value for keyword in keywords)


def _cycle_label(cycle, lang):
    labels = {
        "monthly": ("Monthly", "شهري"),
        "yearly": ("Yearly", "سنوي"),
        "two_years": ("2 Years", "سنتين"),
        "lifetime_trial": ("Trial", "تجربة"),
    }
    en, ar = labels.get(cycle, (cycle.replace("_", " ").title(), cycle))
    return ar if lang == "ar" else en


def _billing_line(plan, lang):
    parts = []
    for cycle, data in (plan.get("billing_cycles") or {}).items():
        price = format_money(data.get("price"), data.get("currency", "USD"))
        original = data.get("original_price")
        if original:
            price = f"{price} (was {format_money(original, data.get('currency', 'USD'))})"
        parts.append(f"{_cycle_label(cycle, lang)}: {price}")
    return " | ".join(parts)


def _yes_no(value, lang):
    if lang == "ar":
        return "متاح" if value else "غير متاح"
    return "Enabled" if value else "Disabled"


def _available_text(value, lang):
    if lang == "ar":
        return "متاح" if value else "غير متاح"
    return "Available" if value else "Not available"


def _plan_block(plan, lang, detailed=False):
    name = plan.get("display_name")
    market = plan.get("market_type", "").upper()
    signal_types = ", ".join(plan.get("signal_types") or [])
    if lang == "ar":
        lines = [
            f"{name} ({market})",
            f"السعر: {_billing_line(plan, lang)}",
            f"الإشارات: {signal_types}",
            f"المستوى: {plan.get('signal_level')}",
            f"Auto Trade: {_available_text(bool(plan.get('auto_trade')), lang)}",
            f"Trial: {_available_text(bool(plan.get('trial')), lang)}",
            f"مناسبة لـ: {plan.get('recommended_for')}",
        ]
        if plan.get("plan_code") == VIP_ALL_FOREX_CODE:
            lines.extend([
                "الأصول المدعومة: " + ", ".join(plan.get("supported_assets") or []),
                "Forex Auto Trade: غير متاح حاليًا",
                "التحليل: اتجاه 4H/1H + دخول 15m/5m + دعم ومقاومة + ATR + RSI/MACD + سبريد حقيقي + فلتر أخبار.",
                "محتوى الإشارة: " + ", ".join(plan.get("signal_content") or []),
            ])
        if detailed:
            lines.append("المميزات: " + "; ".join(plan.get("features") or []))
        lines.append("تنبيه: " + str(plan.get("disclaimer") or "التداول فيه مخاطرة."))
        return "\n".join(lines)

    lines = [
        f"{name} ({market})",
        f"Price: {_billing_line(plan, lang)}",
        f"Signals: {signal_types}",
        f"Level: {plan.get('signal_level')}",
        f"Auto Trade: {_available_text(bool(plan.get('auto_trade')), lang)}",
        f"Trial: {_available_text(bool(plan.get('trial')), lang)}",
        f"Best for: {plan.get('recommended_for')}",
    ]
    if plan.get("plan_code") == VIP_ALL_FOREX_CODE:
        lines.extend([
            "Supported assets: " + ", ".join(plan.get("supported_assets") or []),
            "Forex Auto Trade: Not available",
            "Analysis: 4H/1H trend + 15m/5m entry + S/R + ATR + RSI/MACD + real spread + news filter.",
            "Signal includes: " + ", ".join(plan.get("signal_content") or []),
        ])
    if detailed:
        lines.append("Features: " + "; ".join(plan.get("features") or []))
    lines.append("Disclaimer: " + str(plan.get("disclaimer") or "Trading is risky."))
    return "\n".join(lines)


def _card_expiry(card):
    return card.get("expires_at") or card.get("expiry") or "Lifetime"


def _legacy_crypto_label(user):
    plan = str((user or {}).get("plan") or "trial").strip().lower()
    return PLAN_LABELS.get(plan, plan.title() if plan else "Free Trial")


def _legacy_crypto_expiry(user):
    return (user or {}).get("expiry") or "not active"


def _active_subscriptions_text(user, lang, chat_id=None):
    linked = bool(user and user.get("chat_id"))
    if not user:
        if lang == "ar":
            return (
                "Your active subscriptions\n"
                "Crypto plan: Not linked\n"
                "Crypto expiry: Not linked\n"
                "Forex plan: Not linked\n"
                "Forex expiry: Not linked\n"
                "Telegram linked: No\n"
                "Crypto signals: Disabled\n"
                "Forex signals: Disabled"
            )
        return (
            "Your active subscriptions\n"
            "Crypto plan: Not linked\n"
            "Crypto expiry: Not linked\n"
            "Forex plan: Not linked\n"
            "Forex expiry: Not linked\n"
            "Telegram linked: No\n"
            "Crypto signals: Disabled\n"
            "Forex signals: Disabled"
        )

    injected_cards = isinstance(user, dict) and user.get("subscription_cards") is not None
    cards = user.get("subscription_cards") if injected_cards else get_user_subscription_cards(user)
    crypto_cards = [card for card in cards if str(card.get("market_type") or "crypto").lower() == "crypto"]
    forex_cards = [card for card in cards if str(card.get("market_type") or "").lower() == "forex"]
    if injected_cards:
        capabilities = {
            "can_receive_crypto": bool(crypto_cards) or bool(_legacy_crypto_label(user) != "Free Trial"),
            "can_receive_forex": bool(forex_cards),
        }
    else:
        capabilities = get_user_market_capabilities(user.get("id"), user)

    crypto_plan = ", ".join(card.get("display_name") or card.get("product_code") for card in crypto_cards) or _legacy_crypto_label(user)
    crypto_expiry = ", ".join(str(_card_expiry(card)) for card in crypto_cards) or _legacy_crypto_expiry(user)
    forex_plan = ", ".join(card.get("display_name") or card.get("product_code") for card in forex_cards) or "Not active"
    forex_expiry = ", ".join(str(_card_expiry(card)) for card in forex_cards) or "not active"

    if lang == "ar":
        return "\n".join([
            "Your active subscriptions",
            f"Crypto plan: {crypto_plan}",
            f"Crypto expiry: {crypto_expiry}",
            f"Forex plan: {forex_plan}",
            f"Forex expiry: {forex_expiry}",
            f"Telegram linked: {_yes_no(linked, lang)}",
            f"Crypto signals: {_yes_no(capabilities.get('can_receive_crypto'), lang)}",
            f"Forex signals: {_yes_no(capabilities.get('can_receive_forex'), lang)}",
        ])

    return "\n".join([
        "Your active subscriptions",
        f"Crypto plan: {crypto_plan}",
        f"Crypto expiry: {crypto_expiry}",
        f"Forex plan: {forex_plan}",
        f"Forex expiry: {forex_expiry}",
        f"Telegram linked: {_yes_no(linked, lang)}",
        f"Crypto signals: {_yes_no(capabilities.get('can_receive_crypto'), lang)}",
        f"Forex signals: {_yes_no(capabilities.get('can_receive_forex'), lang)}",
    ])


def telegram_plans_payload(user=None, chat_id=None, lang="en", view="all"):
    lang = _telegram_lang(lang)
    view = str(view or "all").lower()
    crypto = public_plans_by_market("crypto")
    forex = public_plans_by_market("forex")
    if view == "crypto":
        selected = crypto
    elif view == "forex":
        selected = forex
    else:
        selected = crypto + forex

    if lang == "ar":
        title = "خطط Nexora المتاحة"
        intro = "اختر خطة Crypto أو خطة VIP ALL FOREX. الأسعار من نفس كتالوج الموقع، ولا يتم تفعيل أي اشتراك إلا بعد تأكيد الدفع."
        compare = "المقارنة: Crypto للعملات الرقمية Spot/Futures. VIP ALL FOREX للفوركس والذهب يدويًا مع فلتر أخبار وسبريد حقيقي. Auto Trade للفوركس غير متاح حاليًا."
        not_sure = "لو لست متأكدًا: اختر Crypto لو تتداول العملات الرقمية، واختر Forex لو تتابع العملات والذهب. لا توجد نصيحة مالية شخصية."
    else:
        title = "Nexora plans"
        intro = "Choose Crypto plans or the independent VIP ALL FOREX plan. Telegram uses the same central catalog as the website, and subscriptions activate only after verified payment."
        compare = "Comparison: Crypto covers Spot/Futures digital-asset signals. VIP ALL FOREX covers manual Forex/Gold analysis with news protection and real spread validation. Forex Auto Trade is not available."
        not_sure = "Not sure? Choose Crypto for digital assets, Forex for currency/gold analysis. This is not personal financial advice."

    body = [title, "", intro, ""]
    if view == "compare":
        body.extend([compare, "", not_sure, "", _active_subscriptions_text(user, lang, chat_id)])
    else:
        for plan in selected:
            body.append(_plan_block(plan, lang, detailed=(view in {"forex", "details"})))
            body.append("")
        body.append(_active_subscriptions_text(user, lang, chat_id))

    keyboard = [
        [{"text": "Compare plans" if lang == "en" else "قارن الخطط", "callback_data": "plans:compare"}],
        [
            {"text": "Crypto plans" if lang == "en" else "خطط Crypto", "callback_data": "plans:crypto"},
            {"text": "VIP ALL FOREX", "callback_data": "plans:forex"},
        ],
    ]
    if user:
        keyboard.append([
            {"text": "Manage subscription" if lang == "en" else "إدارة الاشتراك", "url": dashboard_url()},
            {"text": "Open dashboard" if lang == "en" else "فتح Dashboard", "url": dashboard_url()},
        ])
    else:
        keyboard.append([
            {"text": "Link account first" if lang == "en" else "اربط حسابك أولًا", "url": login_link_url(chat_id)},
        ])
    if view in {"crypto", "all"}:
        keyboard.append([
            {"text": "Subscribe Basic" if lang == "en" else "اشترك Basic", "url": checkout_url("basic")},
            {"text": "Subscribe Pro" if lang == "en" else "اشترك Pro", "url": checkout_url("pro")},
        ])
    if view in {"forex", "all"}:
        keyboard.append([
            {"text": "Forex Monthly" if lang == "en" else "Forex شهري", "url": checkout_url("vip_all_forex", "monthly")},
            {"text": "Forex Yearly" if lang == "en" else "Forex سنوي", "url": checkout_url("vip_all_forex", "yearly")},
        ])
    keyboard.append([{"text": "Not sure" if lang == "en" else "مش متأكد", "callback_data": "plans:compare"}])
    return "\n".join(line for line in body if line is not None).strip(), {"inline_keyboard": keyboard}


def plan_explainer_message(lang="en"):
    text, _ = telegram_plans_payload(lang=lang)
    return text


def subscription_message(user):
    if not user:
        return (
            "NEXORA ACCOUNT\n\n"
            "No account is linked to this Telegram yet. Use /start and connect through the secure website link."
        )

    trades = int(user.get("trades") or 0)
    bot_active = int(user.get("bot_active") or 0)
    bot_status = "Running" if bot_active == 1 else "Paused"

    return f"""NEXORA SUBSCRIPTION STATUS

{_active_subscriptions_text(user, "en")}

Free signals used: {trades}/2
Bot: {bot_status}
Forex Auto Trade: Not available

Open your dashboard to manage plan, Telegram connection and signal preferences."""


def user_statistics_message(stats):
    return f"""NEXORA ACCOUNT STATISTICS

Signals used: {stats.get('trades', 0)}
Tracked outcome: {stats.get('profit', 0)} USDT
Affiliate balance: ${stats.get('affiliate_balance', 0)}
Registered referrals: {stats.get('registered_referrals', stats.get('total_referrals', 0))}
Active referrals: {stats.get('active_referrals', 0)}
Paid referrals: {stats.get('paid_referrals', 0)}
Spot signals today: {stats.get('spot_today', 0)}
Futures signals today: {stats.get('futures_today', 0)}
Spot win rate: {stats.get('spot_win_rate', 0)}%
Futures win rate: {stats.get('futures_win_rate', 0)}%

Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""


def admin_statistics_message(stats):
    return f"""NEXORA PLATFORM STATISTICS

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
    return f"""NEXORA BROADCAST COMPLETE

Target: {target}
Sent: {sent_count}
Failed: {failed_count}"""
