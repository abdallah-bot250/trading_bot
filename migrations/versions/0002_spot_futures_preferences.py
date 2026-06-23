"""add spot and futures preferences

Revision ID: 0002_spot_futures_preferences
Revises: 0001_database_foundation
Create Date: 2026-06-23
"""

from alembic import op


revision = "0002_spot_futures_preferences"
down_revision = "0001_database_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS spot_enabled INTEGER NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS futures_enabled INTEGER NOT NULL DEFAULT 1")


def downgrade():
    op.drop_column("users", "futures_enabled")
    op.drop_column("users", "spot_enabled")
