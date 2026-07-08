from datetime import datetime

from .runtime import send, format_signal, telegram_referral_link, ensure_user_has_referral_code, generate_referral_code, PLAN_LABELS, PLAN_PRICES, PLAN_DURATIONS_DAYS


def command_menu(is_admin=False):
    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "🤖 NEXORA COMMAND CENTER",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "📌 Account Commands",
        "/start — Connect your account and check access",
        "/subscription — View plan and access status",
        "/plans - Compare Free Earn and paid plan access",
        "/stats — View account and signal statistics",
        "/affiliate — View referrals and commission balance",
        "/help — Show this menu",
    ]
    if is_admin:
        lines.extend([
            "",
            "🛡 Admin Commands",
            "/admin — Open the admin command menu",
            "/admin_stats — View platform statistics",
            "/broadcast message — Send to linked users",
            "/broadcast_paid message — Send to paid users only",
        ])
    lines.extend([
        "",
        "⚠️ Trading involves risk. Nexora signals support decision-making and do not guarantee profit.",
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

Welcome. Nexora filters the market and delivers only qualified opportunities when the current conditions are suitable.

What Nexora reviews:
- Trend and market structure
- Volume and liquidity
- Multi-timeframe alignment
- Entry quality and risk
- Spot/Futures signal suitability

Your free plan includes the first two eligible signals after registration.

Create or connect your account:
{register_link}

After registration, send /start again to complete account linking."""


def linked_message(current_plan, expiry, is_admin=False):
    role = "Admin / Owner" if is_admin else "User"
    return f"""━━━━━━━━━━━━━━━━━━
🤖 NEXORA AI TRADER
━━━━━━━━━━━━━━━━━━

✅ Account connected successfully

👤 Role: {role}
💎 Plan: {current_plan or 'trial'}
📅 Expiry: {expiry or 'not active'}

Use /subscription to review your plan.
Use /stats to review account statistics.
Use /affiliate to review referrals and commission balance.

⚠️ Trading involves risk. Nexora signals support decision-making and do not guarantee profit."""


def plan_explainer_message():
    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "NEXORA PLAN GUIDE",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "FREE EARN",
        "• Free registration.",
        "• Initial direct free-signal allowance if configured.",
        "• After that, qualified opportunities can be unlocked by watching a short rewarded video.",
        "• No paid subscription is required for the Free Earn lane.",
        "• Availability depends on real market conditions. No guaranteed daily signal count.",
        "",
        "PAID PLANS",
        "Direct ad-free access according to the selected plan.",
    ]
    for plan_id in ("basic", "pro", "vip", "pro_2y"):
        label = PLAN_LABELS.get(plan_id, plan_id.title())
        price = PLAN_PRICES.get(plan_id)
        days = PLAN_DURATIONS_DAYS.get(plan_id)
        duration = "2 years" if days and days >= 700 else "monthly"
        if plan_id == "basic":
            who = "For users who want direct Telegram delivery without ads."
            access = "Qualified opportunities with dashboard tracking."
        elif plan_id == "pro":
            who = "For active users who want stronger analysis access."
            access = "Advanced eligible opportunities and premium insights when available."
        elif plan_id == "vip":
            who = "For users who want Elite access and eligible automation controls."
            access = "Priority direct delivery plus Bybit-ready controls for eligible accounts."
        else:
            who = "For long-term users who want the highest available Nexora access."
            access = "Highest direct ad-free access according to the real product configuration."
        lines.extend([
            "",
            label.upper(),
            f"Price: ${price}" if price is not None else "Price: shown on website",
            f"Duration: {duration}",
            f"For: {who}",
            f"Access: {access}",
            "Ads: No rewarded ads.",
        ])
    lines.extend([
        "",
        "COMPARISON",
        "FREE EARN: watch rewarded videos to unlock eligible opportunities.",
        "PAID PLANS: direct ad-free access according to the selected plan.",
        "Highest plan: maximum available access according to the real product configuration.",
        "",
        "Trading involves risk. Signals support trading decisions and do not guarantee profits.",
    ])
    return "\n".join(lines)

def subscription_message(user):
    if not user:
        return "NEXORA ACCOUNT\n\nNo account is linked to this Telegram yet. Use /start and connect through the secure website link."

    plan = user.get("plan") or "trial"
    expiry = user.get("expiry") or "not active"
    is_paid = int(user.get("is_paid") or 0)
    trades = int(user.get("trades") or 0)
    bot_active = int(user.get("bot_active") or 0)
    spot_enabled = int(user.get("spot_enabled", 1) if user.get("spot_enabled") is not None else 1)
    futures_enabled = int(user.get("futures_enabled", 1) if user.get("futures_enabled") is not None else 1)

    status = "Active" if is_paid == 1 else "Free trial / inactive"
    bot_status = "Running" if bot_active == 1 else "Paused"

    return f"""NEXORA SUBSCRIPTION STATUS

Plan: {plan}
Status: {status}
Expiry: {expiry}
Free signals used: {trades}/2
Bot: {bot_status}
Spot signals: {'Enabled' if spot_enabled else 'Paused'}
Futures signals: {'Enabled' if futures_enabled else 'Paused'}

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
