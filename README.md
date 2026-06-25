# 🚀 Nexora AI Trader Bot + Website

A complete ready-to-deploy crypto trading bot business system.

---

## Brand Identity

Global product name: **Nexora AI Trader**

Brand assets:
- Full logo: `/static/brand/nexora-logo.svg`
- Favicon: `/static/brand/favicon.svg`
- Web manifest: `/static/site.webmanifest`
- Brand guide: `/BRAND_GUIDE.md`

Core positioning:
AI-powered crypto signals, Telegram delivery, premium account controls, affiliate growth, and optional Elite automation.

---

## 📌 Overview

This project is a full crypto trading bot system integrated with a website and Telegram bot.

It allows you to:

- Sell crypto trading signals
- Manage users
- Track referrals
- Deliver signals automatically
- Launch your own crypto bot business
- Offer free / paid / Elite plans

This system is suitable for anyone who wants to build a Telegram-based crypto signal service.

---

## ⚙️ Features

- 🤖 Telegram Trading Bot
- 🌐 Modern Landing Page
- 🔐 Register & Login System
- 📊 User Dashboard
- 💰 Affiliate / Referral System
- 📡 Auto Signal Sender
- 🧠 AI-Based Market Analysis
- 💳 Ready for Paid Plans
- 🔗 Telegram Account Linking
- 🛠️ Railway Deployment Ready

---

## AI Engine

The signal engine now attaches a structured AI report to every generated signal while keeping the legacy signal fields unchanged for backward compatibility.

Included analysis layers:
- Trend Detection
- Risk Score
- Confidence Score
- Multi-Timeframe Analysis
- Market Structure
- Volume Analysis
- Volatility Detection
- Performance Tracking
- Spot/Futures independent quality scoring
- Anti-monopoly trade type balancing

Core signal fields such as `pair`, `direction`, `entry`, `tp`, `sl`, `confidence`, and `score` are still preserved so existing Telegram sending, payment plans, and auto-trading flows continue to work.

---

## Telegram Commands

User commands:
- `/start` links Telegram and starts the onboarding flow
- `/help` shows the command menu
- `/subscription` shows plan, expiry, bot state, and Spot/Futures preferences
- `/stats` shows account statistics, Spot/Futures counts, and win rates
- `/affiliate` shows affiliate link and balance

Admin-only commands:
- `/admin` shows admin command menu
- `/admin_stats` shows platform statistics
- `/broadcast message` sends a broadcast to all linked Telegram users
- `/broadcast_paid message` sends a broadcast to paid, lifetime, and admin users only

Telegram broadcasts are restricted to an admin/lifetime Telegram account linked to the configured admin account.

---

# 🖥️ 1) Run Locally

## Step 1 — Install dependencies

Open terminal inside the project folder and run:

```bash
pip install -r requirements.txt

Step 2 — Create .env file

Copy .env.example and rename it to .env

On Window

copy .env.example .env
On Mac / Linux:
cp .env.example .env
Step 3 — Fill your environment variables

Open .env and put your real values inside:

SECRET_KEY=your_secret_key
TELEGRAM_TOKEN=your_bot_token
BOT_LINK=https://t.me/your_bot
BASE_URL=http://127.0.0.1:5000
ADMIN_EMAIL=your@email.com
FERNET_KEY=your_fernet_key
DATABASE_URL=sqlite:///database.db

Explanation:
	•	SECRET_KEY → Flask session security key
	•	TELEGRAM_TOKEN → Your Telegram bot token from BotFather
	•	BOT_LINK → Your bot link (example: https://t.me/your_bot)
	•	BASE_URL → Your local or deployed website URL
	•	ADMIN_EMAIL → Your admin account email
	•	FERNET_KEY → Used for encryption
	•	DATABASE_URL → Database connection string


Step 4 — Start the app

Run:
python app.py

Step 5 — Open in browser

Visit:
http://127.0.0.1:5000
Now your website should be running locally.


🤖 2) Telegram Bot Setup

Step 1 — Create your bot
	1.	Open Telegram
	2.	Search for BotFather
	3.	Start chat with BotFather
	4.	Type:
/newbot
5.	Choose:

	•	Bot name
	•	Bot username

BotFather will give you a token like this:
123456789:ABCDEFxxxxxxxxxxxxxxxx

Step 2 — Add token to .env

Put it here:

TELEGRAM_TOKEN=your_bot_token
BOT_LINK=https://t.me/your_bot

TELEGRAM_TOKEN=123456789:ABCDEFxxxxxxxxxxxxxxxx
BOT_LINK=https://t.me/my_awesome_bot

🌍 3) Deploy on Railway

Step 1 — Create Railway account

Go to
https://railway.app

Create account or login.

⸻

Step 2 — Create a new project
	1.	Click New Project
	2.	Choose one of these:
	•	Deploy from GitHub
	•	Or upload project manually

⸻

Step 3 — Add your files

Upload your project files or connect your GitHub repo.

Your project should include:

templates/
static/
app.py
auto_sender.py
market_analyzer.py
ai_model.py
requirements.txt
Procfile
.env.example
README.md
LICENSE.txt
Step 4 — Add Variables in Railway

Go to:
Project → Variables

SECRET_KEY=your_secret_key
TELEGRAM_TOKEN=your_bot_token
BOT_LINK=https://t.me/your_bot
BASE_URL=https://your-project.up.railway.app
ADMIN_EMAIL=your@email.com
FERNET_KEY=your_fernet_key
DATABASE_URL=your_database_url

Step 5 — Deploy

Railway will automatically build and deploy the project.

Once deployment is complete, Railway will give you a public URL مثل:

https://your-project.up.railway.app
Put this inside your Railway Variables a
BASE_URL=https://your-project.up.railway.app
🔗 4) Activate Telegram Webhook

Webhook is required so Telegram can send user messages to your bot.

⸻

Step 1 — Get your public deployed URL

Example:
https://your-project.up.railway.app

Step 2 — Use this command

Replace:
	•	YOUR_TOKEN
	•	your-project.up.railway.app

Then run:

curl https://api.telegram.org/botYOUR_TOKEN/setWebhook?url=https://your-project.up.railway.app/webhook


curl https://api.telegram.org/bot123456789:ABCDEFxxxxxxxxxxxxxxxx/setWebhook?url=https://your-project.up.railway.app/webhook


Step 3 — If successful, Telegram will return:
{"ok":true,"result":true,"description":"Webhook was set"}

That means your bot is now connected successfully.


👤 5) How Users Use the System

Website Flow
	1.	User opens the website
	2.	User creates account
	3.	User logs in
	4.	User sees dashboard
	5.	User can choose a plan
	6.	User can open Telegram bot

Telegram Flow
	1.	User clicks Open Bot
	2.	User starts the bot
	3.	User sends the same email used on the website
	4.	Bot links the account automatically
	5.	User starts receiving signals based on plan


💡 6) How It Works

This project works like this:
	•	Website handles users, login, plans, affiliate system
	•	Telegram bot handles communication and signal delivery
	•	Market logic handles signal generation
	•	Affiliate system tracks referrals
	•	Elite logic can support automation / advanced features


📁 7) Project Structure
templates/         # HTML pages
static/            # CSS, images, assets
app.py             # Main backend app
auto_sender.py     # Signal sending logic
market_analyzer.py # Market analysis logic
ai_model.py        # AI logic
.env.example       # Example environment variables
requirements.txt   # Python dependencies
Procfile           # Railway deployment config
README.md          # Setup guide
LICENSE.txt        # License file


⚠️ 8) Important Notes
	•	This is a source code product
	•	You must use your own:
	•	Telegram Bot Token
	•	Hosting
	•	Environment Variables
	•	Railway is recommended for deployment
	•	Basic Python / Flask knowledge is helpful
	•	Telegram webhook must be active for bot replies

🔒 9) Security Notes

Before using or reselling this system:
	•	Do NOT share your real .env
	•	Do NOT expose your Telegram token
	•	Do NOT upload your real database credentials publicly
	•	Keep your admin email private
	•	Use .env.example only for sharing / selling

⸻

💸 10) Business Use

You can use this project to:
	•	Launch your own crypto signals business
	•	Sell paid subscriptions
	•	Build a Telegram-based SaaS
	•	Grow using affiliate referrals
	•	Create a white-label crypto signal system

⸻

📦 11) Included in This Package

This package includes:
	•	Full website source code
	•	Telegram bot integration
	•	User authentication system
	•	Dashboard
	•	Affiliate system
	•	Signal delivery system
	•	Deployment-ready files
	•	Setup instructions

⸻

🛠️ 12) Recommended Customization Before Launch

Before launching your own version, it is recommended to change:
	•	Logo / brand name
	•	Telegram bot username
	•	Landing page text
	•	Pricing plans
	•	Admin email
	•	Payment methods
	•	Signal logic (if desired)

This makes the project fully yours.

⸻

❓ 13) Troubleshooting

Problem: Website not opening

Solution:

Make sure you ran:
python app.py
And open:
http://127.0.0.1:5000

Problem: Bot not replying

Solution:

Check:
	•	TELEGRAM_TOKEN is correct
	•	Webhook is active
	•	/webhook route is working
	•	Railway app is live

⸻

Problem: User registered but not receiving signals

Solution:

Make sure the user:
	1.	Opened the bot
	2.	Sent the same email used in registration
	3.	Account was linked successfully

⸻

Problem: Railway deployment failed

Solution:

Check:
	•	requirements.txt
	•	Procfile
	•	Environment Variables
	•	Python version compatibility

⸻

📄 14) License

This package is provided as a source code product.

You are allowed to:
	•	Use it for personal use
	•	Use it for commercial use
	•	Modify the code
	•	Launch your own brand with it

You are NOT allowed to:
	•	Resell the source code as your own product
	•	Redistribute the files publicly
	•	Share this package for free
	•	Re-upload the package as a competing source code product

⸻

🚀 15) Final Note

This project is built to help you launch quickly and start selling fast.

Set it up, deploy it, connect your bot, and you’re ready to run your own crypto signal business.

⸻

💳 16) Payments Layer

The payment system keeps the existing public routes stable:

	•	/create-payment?plan=basic|pro|vip creates a NOWPayments invoice
	•	/payment-webhook validates the NOWPayments IPN signature before activation
	•	/manual-payment/<plan> remains available for manual payments
	•	/invoice-history shows user invoice history

Tracked payment records:

	•	payment_invoices for invoices, coupon usage, links, and status
	•	processed_payments for webhook idempotency
	•	failed_payments for failed, expired, pending, or invalid payment events
	•	coupons for optional discounts
	•	subscription_renewals for new subscriptions and renewal extensions
	•	affiliate_commissions.payment_id to prevent duplicate commission payouts

Required Railway variables:

	•	NOWPAYMENTS_API_KEY
	•	NOWPAYMENTS_IPN_SECRET
	•	BASE_URL
	•	DATABASE_URL

⸻

🚢 17) Production Deployment

Production deployment files are included:

	•	Dockerfile
	•	docker-compose.yml
	•	gunicorn.conf.py
	•	deploy/nginx.conf
	•	DEPLOYMENT.md

Health check:

	•	/health

Railway still uses Procfile, now with the shared Gunicorn production config:

web: gunicorn -c gunicorn.conf.py app:app
worker: python auto_sender.py

For full deployment details, read DEPLOYMENT.md.

## Production Value Improvements

- Dashboard now shows subscription status and remaining paid days using the existing `plan`, `is_paid`, and `expiry` fields.
- Admin overview includes active, free, premium, expiring, and expired subscription counters without requiring schema changes.
- Admin system status now exposes bot, database, Telegram configuration, total signals, and last signal time using safe optional queries.
- Referral dashboard keeps the existing referral flow and adds clearer referral code and commission visibility.

No database schema, migrations, payment flow, Telegram token, route names, or authentication flow are changed by these improvements.

## Production Phase 2 Additions

- Subscription lifecycle helpers now expose `subscription_active`, `subscription_expired`, `remaining_days`, and `started_days_ago` using existing user fields only.
- Dashboard shows plan, start date, expiry, remaining days, status, premium state, and Telegram bot connection state.
- Referral dashboard shows link, code, QR code, total referrals, active referrals, paid referrals, commissions, balance, and withdrawals.
- Admin includes today registrations/payments, expired/expiring subscriptions, service status, worker status, and a read-only `/admin/system-health` page.
- Market source logs are throttled to reduce repeated Railway/Binance noise without changing signal calculations.
