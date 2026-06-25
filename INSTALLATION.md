# Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set real values in `.env`. Do not commit `.env`.

Required production variables:

```env
SECRET_KEY=
TELEGRAM_TOKEN=
BOT_LINK=https://t.me/your_bot_username
BASE_URL=https://nexoratrader.net
CANONICAL_DOMAIN=https://nexoratrader.net
ADMIN_EMAIL=
FERNET_KEY=
DATABASE_URL=
NOWPAYMENTS_API_KEY=
NOWPAYMENTS_IPN_SECRET=
```

Run web:

```bash
python app.py
```

Run worker:

```bash
python auto_sender.py
```

Telegram:

```bash
python scripts/telegram_webhook.py status
python scripts/telegram_webhook.py set
```

## Verification

After installation, verify:

1. `/dashboard` renders subscription status for free and paid users.
2. `/admin` renders even if optional reporting tables are missing.
3. Telegram linking and payment webhooks keep their existing route names and behavior.

## Phase 2 Verification

- Open `/dashboard` with a test user and confirm lifecycle/referral cards render.
- Open `/admin` and `/admin/system-health` with an admin account.
- Confirm no migration is required and no production data is modified by the new health page.
