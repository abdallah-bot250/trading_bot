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
