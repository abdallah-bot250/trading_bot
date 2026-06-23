"""payments foundation

Revision ID: 0004_payments_foundation
Revises: 0002_spot_futures_preferences
Create Date: 2026-06-23
"""

from alembic import op


revision = "0004_payments_foundation"
down_revision = "0002_spot_futures_preferences"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS payment_invoices (
            id SERIAL PRIMARY KEY,
            invoice_id TEXT,
            payment_id TEXT,
            chat_id TEXT,
            email TEXT,
            plan TEXT,
            status TEXT DEFAULT 'created',
            amount REAL DEFAULT 0,
            original_amount REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'usd',
            coupon_code TEXT,
            invoice_url TEXT,
            raw_response TEXT,
            paid_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE,
            discount_percent REAL DEFAULT 0,
            active INTEGER DEFAULT 1,
            expires_at TEXT,
            max_redemptions INTEGER,
            redemption_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS failed_payments (
            id SERIAL PRIMARY KEY,
            payment_id TEXT,
            invoice_id TEXT,
            order_id TEXT,
            plan TEXT,
            payment_status TEXT,
            reason TEXT,
            raw_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscription_renewals (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            email TEXT,
            plan TEXT,
            payment_id TEXT,
            previous_expiry TEXT,
            new_expiry TEXT,
            amount REAL DEFAULT 0,
            renewal_type TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    op.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS plan TEXT")
    op.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS amount REAL DEFAULT 0")
    op.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'usd'")
    op.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS invoice_id TEXT")
    op.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS invoice_url TEXT")
    op.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS raw_payload TEXT")
    op.execute("ALTER TABLE affiliate_commissions ADD COLUMN IF NOT EXISTS payment_id TEXT")

    for table_name in ("payment_invoices", "coupons", "failed_payments", "subscription_renewals"):
        op.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS uuid TEXT")
        op.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        op.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL")
        op.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{table_name}_uuid ON {table_name} (uuid)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_deleted_at ON {table_name} (deleted_at)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_processed_payments_invoice_id ON processed_payments (invoice_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_affiliate_commissions_payment_id ON affiliate_commissions (payment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payment_invoices_chat_created ON payment_invoices (chat_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payment_invoices_status ON payment_invoices (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payment_invoices_invoice_id ON payment_invoices (invoice_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_coupons_code ON coupons (code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_failed_payments_created ON failed_payments (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_subscription_renewals_chat_created ON subscription_renewals (chat_id, created_at)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS subscription_renewals")
    op.execute("DROP TABLE IF EXISTS failed_payments")
    op.execute("DROP TABLE IF EXISTS coupons")
    op.execute("DROP TABLE IF EXISTS payment_invoices")
