"""Run once after deploy if Railway database has old plan constraints.
Usage on Railway shell: python scripts/railway_upgrade_plans.py
"""
import os
import psycopg2

url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PUBLIC_URL")
if not url:
    raise SystemExit("DATABASE_URL / DATABASE_PUBLIC_URL is missing")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

conn = psycopg2.connect(url, sslmode="require")
try:
    c = conn.cursor()
    c.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_plan")
    c.execute("""
        ALTER TABLE users
        ADD CONSTRAINT ck_users_plan
        CHECK (plan IN ('trial', 'basic', 'pro', 'vip', 'pro_2y'))
        NOT VALID
    """)
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS spot_auto_trade_enabled INTEGER DEFAULT 0")
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS futures_auto_trade_enabled INTEGER DEFAULT 0")
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS max_trade_size REAL DEFAULT 10")
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS stop_loss_required INTEGER DEFAULT 1")
    conn.commit()
    print("OK: plan constraint and auto-trading columns are ready")
finally:
    conn.close()
