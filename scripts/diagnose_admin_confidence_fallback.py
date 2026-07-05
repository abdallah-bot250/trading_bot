import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
routes = (ROOT / "trader_app" / "blueprints" / "routes.py").read_text(encoding="utf-8")

if "def admin_recent_signal_rows" not in routes:
    raise AssertionError("admin_recent_signal_rows helper missing")
if "ADMIN_CONFIDENCE_FALLBACK_USED source=" not in routes:
    raise AssertionError("fallback log missing")
if "display_confidence AS confidence" not in routes:
    raise AssertionError("display_confidence fallback missing")
if "final_score AS confidence" not in routes:
    raise AssertionError("final_score fallback missing")
if "NULL AS confidence" not in routes:
    raise AssertionError("NULL fallback missing")
if "SELECT chat_id, pair, direction, entry, tp, sl, confidence, status, created_at\n            FROM trades_log" in routes:
    raise AssertionError("unsafe direct confidence select still present")

for required in (
    "FREE_EARN_MODE",
    "REWARDED_AD_PROVIDER",
    "FREE_SIGNALS_LIFETIME",
    "LOCKED_SIGNAL_TTL_MINUTES",
    "/adsgram/reward?user_id=[userId]",
    "registered_referrals_count",
    "NEXORA TRADE OPPORTUNITY",
):
    if required not in (ROOT / ("auto_sender.py" if required in {"FREE_EARN_MODE", "REWARDED_AD_PROVIDER", "FREE_SIGNALS_LIFETIME", "LOCKED_SIGNAL_TTL_MINUTES", "NEXORA TRADE OPPORTUNITY"} else "trader_app/blueprints/routes.py")).read_text(encoding="utf-8"):
        raise AssertionError(f"launch safety marker missing: {required}")

ast.parse(routes, filename="trader_app/blueprints/routes.py")
print("ADMIN_CONFIDENCE_FALLBACK_OK")
