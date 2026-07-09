from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


routes = read("trader_app/blueprints/routes.py")
dashboard = read("templates/dashboard.html")
auto_sender = read("auto_sender.py")
env_example = read(".env.example")

fake_metric_patterns = [
    "min(96, max(48",
    "58 + (trades * 3)",
    "62 + (trades * 4)",
    "Plan-adjusted signal quality estimate",
    "Trade capital + profit + affiliate balance",
]
for pattern in fake_metric_patterns:
    require(pattern not in routes + dashboard, f"fake/static dashboard metric remains: {pattern}")

require("signal_log" in routes, "dashboard metrics must read signal_log")
require("portfolio_display" in routes and '"N/A"' in routes, "portfolio must support honest N/A fallback")
require("roi_display" in routes and '"N/A"' in routes, "ROI must support honest N/A fallback")
require("record_sent_signal" in auto_sender, "signal tracking function missing")
require("display_confidence" in auto_sender, "tracked signal display confidence missing")
require("delivery_mode" in auto_sender, "delivery mode tracking missing")
require("take_profits" in auto_sender, "take-profit payload tracking missing")
require("TP1_HIT" in auto_sender and "SL_HIT" in auto_sender, "real outcome labels missing")
require("pnl_percent" in auto_sender and "get_live_price" in auto_sender, "outcome tracking must use live market data")

required_docs = [
    "SALE_ASSET_REGISTER.md",
    "BUYER_HANDOVER.md",
    "DEPLOYMENT_GUIDE.md",
    "ENVIRONMENT_VARIABLES.md",
    "BUYER_VERIFICATION_CHECKLIST.md",
    "SALE_README.md",
]
for doc in required_docs:
    require((ROOT / doc).exists(), f"missing sale document: {doc}")

require("Suggested selling price: 8000 USD" not in read("SALE_README.md"), "old hardcoded sale price remains")
require("put_your_bot_token_here" in env_example, ".env.example should contain placeholders, not production Telegram token")
secret_patterns = [
    r"\d{8,}:[A-Za-z0-9_-]{20,}",
    r"postgresql://[^\\s]*:[^\\s]*@",
]
for pattern in secret_patterns:
    require(not re.search(pattern, env_example), f"possible secret in .env.example pattern={pattern}")

print("ADMIN_REAL_METRICS_DOCS_OK")
print("REAL_METRICS_SALE_READINESS_OK")
