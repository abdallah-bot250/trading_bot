from pathlib import Path
import re

PACKAGE_DIR = Path(r"C:\Users\pc\Documents\Codex\Nexora_Trader_SALE_PACKAGE_20260709")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


require(PACKAGE_DIR.exists(), f"sale package folder missing: {PACKAGE_DIR}")
require(not (PACKAGE_DIR / ".env").exists(), ".env must not be included")
require(not any("__pycache__" in p.parts for p in PACKAGE_DIR.rglob("*")), "__pycache__ found")
require(not any("review_diff" in p.name.lower() for p in PACKAGE_DIR.rglob("*")), "review_diff file found")

required_docs = [
    "README.md",
    "SALE_README.md",
    "SALE_ASSET_REGISTER.md",
    "BUYER_HANDOVER.md",
    "BUYER_VERIFICATION_CHECKLIST.md",
    "DEPLOYMENT_GUIDE.md",
    "ENVIRONMENT_VARIABLES.md",
    "INSTALLATION.md",
    "SECRET_AUDIT_REPORT.md",
    "SALE_LISTING_DRAFT.md",
    "BUYER_DUE_DILIGENCE_NOTES.md",
]
for doc in required_docs:
    require((PACKAGE_DIR / doc).exists(), f"missing sale doc: {doc}")

env_text = (PACKAGE_DIR / ".env.example").read_text(encoding="utf-8")
require("TELEGRAM_TOKEN=your_telegram_bot_token" in env_text, "Telegram token placeholder missing")
require("DATABASE_URL=your_database_url" in env_text, "Database URL placeholder missing")
require("ADSGRAM_BLOCK_ID=your_adsgram_block_id" in env_text, "AdsGram block placeholder missing")
require("BASE_URL=https://yourdomain.com" in env_text, "BASE_URL placeholder missing")
require(not re.search(r"\b\d{8,}:[A-Za-z0-9_-]{20,}\b", env_text), "real Telegram token pattern found")
require("abdallah" not in env_text.lower(), "personal email/name found in env example")
require("556644297" not in env_text and "0568869313" not in env_text, "personal phone found in env example")

listing = (PACKAGE_DIR / "SALE_LISTING_DRAFT.md").read_text(encoding="utf-8").lower()
for banned in ["guaranteed profit", "guaranteed signals", "guaranteed revenue", "fake mrr", "fake arr"]:
    require(banned not in listing, f"banned sale claim found: {banned}")

require((PACKAGE_DIR / "SALE_PROOF_PLACEHOLDERS").exists(), "proof placeholder folder missing")

print("SALE_PACKAGE_CLEAN_OK")
