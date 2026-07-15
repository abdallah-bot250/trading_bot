import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def install_runtime_stubs():
    if "requests" not in sys.modules:
        requests_stub = types.ModuleType("requests")

        class RequestException(Exception):
            pass

        class Timeout(Exception):
            pass

        requests_stub.get = lambda *args, **kwargs: (_ for _ in ()).throw(RequestException("diagnostic network disabled"))
        requests_stub.post = lambda *args, **kwargs: (_ for _ in ()).throw(RequestException("diagnostic network disabled"))
        requests_stub.exceptions = types.SimpleNamespace(RequestException=RequestException, Timeout=Timeout)
        sys.modules["requests"] = requests_stub
    sys.modules.setdefault("ccxt", types.ModuleType("ccxt"))
    sys.modules.setdefault("psycopg2", types.ModuleType("psycopg2"))
    if "dotenv" not in sys.modules:
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *args, **kwargs: None
        sys.modules["dotenv"] = dotenv_stub
    if "pandas" not in sys.modules:
        sys.modules["pandas"] = types.ModuleType("pandas")
    if "numpy" not in sys.modules:
        sys.modules["numpy"] = types.ModuleType("numpy")


def test_no_signal_cooldown_memory_fallback():
    install_runtime_stubs()
    import auto_sender

    original_db = auto_sender.db
    original_cache = dict(auto_sender.LAST_NO_SIGNAL_NOTIFY)
    try:
        auto_sender.db = lambda: (_ for _ in ()).throw(Exception("diagnostic db unavailable"))
        auto_sender.LAST_NO_SIGNAL_NOTIFY.clear()
        assert_true(auto_sender.should_notify_no_signal("chat-a", "trial", "market_wait") is True, "First no-signal notice should send")
        assert_true(auto_sender.should_notify_no_signal("chat-a", "trial", "market_wait") is False, "Duplicate no-signal notice must be cooled down")
        assert_true(auto_sender.should_notify_no_signal("chat-a", "trial", "mtf_unconfirmed") is True, "Changed market state can send a fresh status")
        key = "chat-a:trial:market_wait"
        auto_sender.LAST_NO_SIGNAL_NOTIFY[key] = datetime.now() - timedelta(minutes=auto_sender.NO_SIGNAL_NOTIFY_COOLDOWN_MINUTES + 5)
        assert_true(auto_sender.should_notify_no_signal("chat-a", "trial", "market_wait") is True, "Expired cooldown should allow status")
    finally:
        auto_sender.db = original_db
        auto_sender.LAST_NO_SIGNAL_NOTIFY.clear()
        auto_sender.LAST_NO_SIGNAL_NOTIFY.update(original_cache)


def test_telegram_403_marks_connection_inactive_path_exists():
    text = (ROOT / "auto_sender.py").read_text(encoding="utf-8", errors="replace")
    assert_true("mark_telegram_connection_inactive" in text, "Telegram inactive marker missing")
    assert_true("UPDATE users" in text and "SET bot_active = 0" in text, "Telegram 403 must disable bot_active")
    assert_true("BOT_DISCONNECTED_OR_BLOCKED" in text, "Telegram blocked log missing")


def test_rejection_counter_single_primary_reason():
    install_runtime_stubs()
    import market_analyzer

    market_analyzer.reset_signal_scan_diagnostics()
    market_analyzer._scan_diag_attempt("BTCUSDT")
    code = market_analyzer._record_scan_rejection("INVALID_ENTRY no retest on 15m")
    summary = market_analyzer.get_signal_scan_diagnostics()
    rejection_total = sum(
        int(summary.get(key, 0) or 0)
        for key in [
            "rejected_low_volatility", "rejected_mtf", "rejected_liquidity",
            "rejected_fake_breakout", "rejected_quality", "rejected_entry",
        ]
    )
    assert_true(code == "INVALID_ENTRY", f"Expected INVALID_ENTRY, got {code}")
    assert_true(rejection_total == 1, f"Expected one primary rejection, got {rejection_total}")
    assert_true(rejection_total <= int(summary.get("scan_attempts", 0)), "Rejections must not exceed scan attempts")


def main():
    test_no_signal_cooldown_memory_fallback()
    test_telegram_403_marks_connection_inactive_path_exists()
    test_rejection_counter_single_primary_reason()
    print("POST_DEPLOY_SIGNAL_SUPPLY_FIX_DIAGNOSTICS_OK")


if __name__ == "__main__":
    main()
