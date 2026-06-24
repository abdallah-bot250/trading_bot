"""database foundation

Revision ID: 0001_database_foundation
Revises:
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_database_foundation"
down_revision = None
branch_labels = None
depends_on = None


TABLES = [
    "users",
    "affiliate_referrals",
    "affiliate_commissions",
    "affiliate_withdrawals",
    "telegram_referrals",
    "processed_payments",
    "audit_logs",
]


def _add_column_if_missing(table, column):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns(table)}
    if column.name not in columns:
        op.add_column(table, column)


def _create_index_if_missing(name, table, columns, unique=False):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes(table)}
    if name not in indexes:
        op.create_index(name, table, columns, unique=unique)


def _create_check_constraint_if_missing(name, table, condition):
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = '{name}'
                ) THEN
                    ALTER TABLE {table}
                    ADD CONSTRAINT {name}
                    CHECK ({condition}) NOT VALID;
                END IF;
            END $$;
            """
        )
    )


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    for table in TABLES:
        _add_column_if_missing(table, sa.Column("uuid", sa.Text(), server_default=sa.text("gen_random_uuid()::text")))
        _add_column_if_missing(table, sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")))
        _add_column_if_missing(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))
        _create_index_if_missing(f"ix_{table}_uuid", table, ["uuid"], unique=True)
        _create_index_if_missing(f"ix_{table}_deleted_at", table, ["deleted_at"])

    _create_index_if_missing("ix_users_email", "users", ["email"])
    _create_index_if_missing("ix_users_plan_paid", "users", ["plan", "is_paid"])
    _create_index_if_missing("ix_users_referral_code", "users", ["referral_code"])
    _create_index_if_missing("ix_affiliate_referrals_referrer", "affiliate_referrals", ["referrer_chat_id"])
    _create_index_if_missing("ix_affiliate_referrals_referred", "affiliate_referrals", ["referred_chat_id"])
    _create_index_if_missing("ix_affiliate_commissions_referrer", "affiliate_commissions", ["referrer_chat_id"])
    _create_index_if_missing("ix_affiliate_commissions_status", "affiliate_commissions", ["status"])
    _create_index_if_missing("ix_affiliate_withdrawals_chat_status", "affiliate_withdrawals", ["chat_id", "status"])
    _create_index_if_missing("ix_processed_payments_order_id", "processed_payments", ["order_id"])
    _create_index_if_missing("ix_audit_logs_email_created", "audit_logs", ["email", "created_at"])
    _create_index_if_missing("ix_audit_logs_action_created", "audit_logs", ["action", "created_at"])

    _create_check_constraint_if_missing("ck_users_plan", "users", "plan IN ('trial', 'basic', 'pro', 'vip', 'pro_2y')")
    _create_check_constraint_if_missing("ck_users_trade_type", "users", "trade_type IN ('spot', 'futures')")
    _create_check_constraint_if_missing("ck_users_flags", "users", "is_paid IN (0, 1) AND bot_active IN (0, 1) AND is_admin IN (0, 1) AND lifetime_owner IN (0, 1)")
    _create_check_constraint_if_missing("ck_affiliate_commissions_amount_nonnegative", "affiliate_commissions", "amount >= 0")
    _create_check_constraint_if_missing("ck_affiliate_withdrawals_amount_positive", "affiliate_withdrawals", "amount > 0")
    _create_check_constraint_if_missing("ck_affiliate_withdrawals_status", "affiliate_withdrawals", "status IN ('pending', 'paid', 'rejected')")


def downgrade():
    pass
