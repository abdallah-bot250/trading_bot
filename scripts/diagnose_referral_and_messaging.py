import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def assert_contains(text, needle, label):
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def assert_not_contains(text, needle, label):
    if needle.lower() in text.lower():
        raise AssertionError(f"unsafe wording in {label}: {needle}")


routes = read("trader_app/blueprints/routes.py")
auto_sender = read("auto_sender.py")
runtime = read("trader_app/services/runtime.py")
telegram = read("trader_app/services/telegram.py")

assert_contains(routes, "registered_referrals_count", "registered referral metric")
assert_contains(routes, "FROM users\n                WHERE referred_by", "users.referred_by registered source")
assert_contains(routes, "affiliate_commissions", "paid referral source")
assert_contains(routes, "REFERRAL_SELF_REFERRAL_REJECTED", "self referral rejection log")
assert_contains(routes, "REFERRAL_DUPLICATE_SKIPPED", "duplicate referral log")
assert_contains(routes, "@admin_bp.route(\"/admin/referral-debug\")", "admin referral debug route")
assert_contains(routes, "https://www.instagram.com/nexoraaitrader/?hl=en", "official instagram fallback")
assert_contains(routes, "https://www.facebook.com/profile.php?id=61591117963149", "official facebook fallback")

assert_contains(auto_sender, "NEXORA TRADE OPPORTUNITY", "signal opportunity header")
assert_contains(runtime, "NEXORA TRADE OPPORTUNITY", "runtime signal opportunity header")
assert_contains(auto_sender, "not financial advice and does not guarantee profit", "risk disclaimer")
assert_contains(runtime, "not financial advice and does not guarantee profit", "runtime risk disclaimer")
assert_contains(auto_sender, "NEW NEXORA OPPORTUNITY", "locked signal header")
assert_contains(auto_sender, "Unlock the full setup", "locked signal protection")
assert_contains(auto_sender, "Watch Video & Unlock", "unlock button copy")
assert_contains(auto_sender, "\"web_app\"", "telegram web app unlock button")
assert_contains(auto_sender, "NEXORA TRADE RESULT", "trade result header")
assert_contains(telegram, "NEXORA COMMAND CENTER", "professional telegram command layer")

prompt_start = auto_sender.index("def send_unlock_prompt")
prompt_end = auto_sender.index("def free_earn_base_url", prompt_start)
prompt = auto_sender[prompt_start:prompt_end]
for forbidden in ("Entry:", "TP1:", "TP2:", "TP3:", "SL:"):
    assert_not_contains(prompt, forbidden, "locked signal prompt")

for text, label in ((auto_sender, "auto_sender"), (runtime, "runtime"), (telegram, "telegram")):
    assert_not_contains(text, "guaranteed profit", label)
    assert_not_contains(text, "100% accurate", label)
    assert_not_contains(text, "risk-free", label)

for rel in ("auto_sender.py", "trader_app/services/runtime.py", "trader_app/services/telegram.py", "trader_app/blueprints/routes.py"):
    ast.parse(read(rel), filename=rel)

print("REFERRAL_AND_MESSAGING_OK")
