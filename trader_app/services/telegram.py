from datetime import datetime

from .runtime import send, format_signal, telegram_referral_link, ensure_user_has_referral_code, generate_referral_code


def command_menu(is_admin=False):
    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "🤖 NEXORA COMMAND CENTER",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "📌 Account Commands",
        "/start — Connect your account and check access",
        "/subscription — View plan and access status",
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
