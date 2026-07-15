from pathlib import Path

from trader_app.services.payments import generate_nowpayments_signature, validate_nowpayments_signature

ROOT = Path(__file__).resolve().parents[1]


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8", errors="ignore")


def test_nowpayments_signature_is_hmac_sha512_sorted_json():
    secret = "test_ipn_secret"
    payload_a = {
        "payment_status": "finished",
        "invoice_id": "inv_123",
        "order_id": "chat_1",
        "nested": {"b": 2, "a": 1},
    }
    payload_b = {
        "nested": {"a": 1, "b": 2},
        "order_id": "chat_1",
        "invoice_id": "inv_123",
        "payment_status": "finished",
    }

    sig = generate_nowpayments_signature(payload_a, secret)
    assert len(sig) == 128
    assert sig == generate_nowpayments_signature(payload_b, secret)
    assert validate_nowpayments_signature(payload_b, sig, secret)[0] is True
    assert validate_nowpayments_signature(payload_b, sig, "wrong_secret")[0] is False
    assert validate_nowpayments_signature(payload_b, "bad_signature", secret)[0] is False


def test_create_payment_is_post_only_and_get_is_safe():
    routes = read("trader_app/blueprints/routes.py")
    start = routes.index('@payments_bp.route("/create-payment"')
    block = routes[start:routes.index('@payments_bp.route("/invoice-history")')]

    assert 'methods=["GET", "POST"]' in block
    assert 'if request.method != "POST"' in block
    assert 'CREATE_PAYMENT_GET_BLOCKED' in block
    assert 'return redirect("/payments")' in block
    assert 'NOWPAYMENTS_REUSE_PENDING_INVOICE' in block


def test_logout_no_longer_executes_on_get_and_templates_use_post():
    routes = read("trader_app/blueprints/routes.py")
    dashboard = read("templates/dashboard.html")

    assert '@auth_bp.route("/logout", methods=["GET", "POST"])' in routes
    assert 'if request.method != "POST":' in routes
    assert 'action="/logout" method="POST"' in dashboard
    assert 'href="/logout"' not in dashboard


def test_dynamic_symbols_not_forced_to_single_symbol_without_explicit_mode():
    market = read("market_analyzer.py")

    assert 'SINGLE_SYMBOL_MODE' in market
    assert 'MAX_DYNAMIC_SYMBOLS = _env_int("MAX_DYNAMIC_SYMBOLS", 120' in market
    assert 'fallback=all_sources_empty' in market
    assert market.count("USDT") > 20
