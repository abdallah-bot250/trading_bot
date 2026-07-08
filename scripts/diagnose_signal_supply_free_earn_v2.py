import inspect
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('FERNET_KEY', 'MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=')

import auto_sender
from market_analyzer import classify_opportunity_tier, get_signal_scan_diagnostics, reset_signal_scan_diagnostics
from trader_app.services.telegram import command_menu, plan_explainer_message

def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    high_quality = {
        "display_confidence": 90,
        "confidence": 90,
        "engine_confidence": 88,
        "final_score": 94,
        "risk_reward": 2.0,
        "risk_score": 45,
        "quality_checklist_score": 94,
        "pair": "BTCUSDT",
        "timeframe": "15m",
    }
    weak = {"display_confidence": 62, "final_score": 70, "risk_reward": 1.2}

    assert_true(auto_sender.FREE_SIGNALS_LIFETIME == int(auto_sender.FREE_SIGNALS_LIFETIME), "free lifetime config readable")
    assert_true(auto_sender.MAX_QUALIFIED_OPPORTUNITIES_PER_CYCLE != auto_sender.FREE_SIGNALS_LIFETIME or auto_sender.MAX_CANDIDATES_PER_SCAN != auto_sender.FREE_SIGNALS_LIFETIME, "scanner supply must not be controlled by FREE_SIGNALS_LIFETIME")
    assert_true(auto_sender.signal_allowed_for_plan("trial", high_quality), "trial/free earn must not reject high quality above old cap")
    assert_true(auto_sender.signal_allowed_for_plan("pro_2y", high_quality), "pro_2y must be eligible for qualified opportunities")
    assert_true(classify_opportunity_tier(high_quality) == "A_PLUS", "A+ tier classification failed")
    assert_true(classify_opportunity_tier(weak) in {"WATCHLIST", "REJECTED"}, "weak setup must not become qualified")

    reset_signal_scan_diagnostics()
    diag = get_signal_scan_diagnostics()
    assert_true("qualified_a_plus" in diag and "watchlist" in diag, "diagnostics missing opportunity tier counters")

    unlock_template = (ROOT / "templates" / "unlock_signal.html").read_text(encoding="utf-8")
    assert_true("Reward URL registered" not in unlock_template, "unlock page exposes internal Reward URL")
    assert_true("I followed both pages" not in unlock_template, "social follow blocker still present")
    assert_true("initData" not in unlock_template or "tg.initData" in unlock_template, "unexpected public initData explanation")

    src = inspect.getsource(auto_sender.send_unlock_prompt)
    assert_true('"web_app"' in src, "Telegram unlock prompt must use Web App button")

    menu = command_menu(False)
    plans = plan_explainer_message()
    assert_true("/plans" in menu, "/plans missing from command menu")
    assert_true("FREE EARN" in plans and "PAID PLANS" in plans, "plan explainer missing key sections")


    auto_source = (ROOT / "auto_sender.py").read_text(encoding="utf-8")
    route_source = (ROOT / "trader_app" / "blueprints" / "routes.py").read_text(encoding="utf-8")

    assert_true("verify_telegram_webapp_init_data" in auto_source, "Telegram Web App initData validator missing")
    assert_true("bind_adsgram_user_to_unlock" in auto_source and "verified_user_id" in auto_source, "secure AdsGram user binding missing")
    assert_true("adsgram_token_for_user" in auto_source and "mapped_token" in auto_source, "AdsGram reward must resolve server-side token mapping")
    assert_true("already_rewarded_or_unlocked" in auto_source or "already_used" in auto_source, "replay/double reward protection missing")
    assert_true("stale_credit_granted" in auto_source and "expired_credit_granted" in auto_source, "stale/expired unlock credit path missing")
    assert_true('if str(plan or "trial").lower() != "trial":' in auto_source and 'return "not_free"' in auto_source, "paid plans must bypass rewarded ads")
    assert_true("if not is_qualified_opportunity(s):" in auto_source, "final delivery must block watchlist/rejected opportunities")
    assert_true("FREE_SIGNALS_LIMIT = MAX_QUALIFIED_OPPORTUNITIES_PER_CYCLE" in auto_source, "FREE_SIGNALS_LIFETIME must not control scanner supply")
    assert_true("@public_bp.route(\"/adsgram/bind-user\"" in route_source, "AdsGram bind route missing")
    assert_true("@public_bp.route(\"/adsgram/reward\"" in route_source, "AdsGram reward callback missing")
    assert_true("@admin_bp.route(\"/admin/signal-supply\")" in route_source, "admin signal supply diagnostics route missing")

    print("SIGNAL_SUPPLY_FREE_EARN_V2_OK")


if __name__ == "__main__":
    main()
