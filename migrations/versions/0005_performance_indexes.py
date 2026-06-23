"""performance indexes

Revision ID: 0005_performance_indexes
Revises: 0004_payments_foundation
Create Date: 2026-06-23
"""

from alembic import op


revision = "0005_performance_indexes"
down_revision = "0004_payments_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE INDEX IF NOT EXISTS ix_payment_invoices_status_created ON payment_invoices (status, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_processed_payments_status_created ON processed_payments (payment_status, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_subscription_renewals_type_created ON subscription_renewals (renewal_type, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_paid_created ON users (is_paid, created_at)")
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('public.trades_log') IS NOT NULL THEN
                CREATE INDEX IF NOT EXISTS ix_trades_log_status_created ON trades_log (status, created_at);
                CREATE INDEX IF NOT EXISTS ix_trades_log_type_status ON trades_log (LOWER(COALESCE(trade_type, 'futures')), status);
                CREATE INDEX IF NOT EXISTS ix_trades_log_chat_created ON trades_log (chat_id, created_at);
                CREATE INDEX IF NOT EXISTS ix_trades_log_closed_pnl ON trades_log (status, pnl);
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_trades_log_closed_pnl")
    op.execute("DROP INDEX IF EXISTS ix_trades_log_chat_created")
    op.execute("DROP INDEX IF EXISTS ix_trades_log_type_status")
    op.execute("DROP INDEX IF EXISTS ix_trades_log_status_created")
    op.execute("DROP INDEX IF EXISTS ix_users_paid_created")
    op.execute("DROP INDEX IF EXISTS ix_users_created_at")
    op.execute("DROP INDEX IF EXISTS ix_subscription_renewals_type_created")
    op.execute("DROP INDEX IF EXISTS ix_processed_payments_status_created")
    op.execute("DROP INDEX IF EXISTS ix_payment_invoices_status_created")
