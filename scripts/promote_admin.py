"""Promote the configured ADMIN_EMAIL account to admin.

Run from Railway shell after setting ADMIN_EMAIL.

Optional:
  ADMIN_TELEGRAM_ID=<your Telegram numeric chat id>

This script does not print secrets and does not create a password.
It only updates an existing account that already registered in the app.
"""

import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def normalize_database_url(value):
    value = str(value or "").strip()
    if value.startswith("postgres://"):
        value = value.replace("postgres://", "postgresql://", 1)
    return value


def main():
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    telegram_id = os.environ.get("ADMIN_TELEGRAM_ID", "").strip()
    database_url = normalize_database_url(os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PUBLIC_URL"))

    if not admin_email:
        raise SystemExit("ADMIN_EMAIL is missing")
    if not database_url:
        raise SystemExit("DATABASE_URL / DATABASE_PUBLIC_URL is missing")

    conn = psycopg2.connect(database_url, sslmode="require")
    try:
        c = conn.cursor()
        c.execute("SELECT id, email, chat_id, is_admin FROM users WHERE LOWER(email) = %s LIMIT 1", (admin_email,))
        row = c.fetchone()
        if not row:
            raise SystemExit(f"No registered user found for ADMIN_EMAIL={admin_email}. Register/login with this email first.")

        if telegram_id:
            c.execute("""
                UPDATE users
                SET is_admin = 1,
                    lifetime_owner = 0,
                    chat_id = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (telegram_id, row[0]))
        else:
            c.execute("""
                UPDATE users
                SET is_admin = 1,
                    lifetime_owner = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (row[0],))

        conn.commit()
        print(f"OK: admin enabled for {admin_email}")
        if telegram_id:
            print(f"OK: Telegram admin chat_id linked: {telegram_id}")
        else:
            print("NOTE: ADMIN_TELEGRAM_ID was not set, so Telegram admin commands require the account to already be linked.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
