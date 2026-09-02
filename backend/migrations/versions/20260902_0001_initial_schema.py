"""Create Verve Gate tables and migrate Phase 2 columns."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260902_0001"
down_revision = None
branch_labels = None
depends_on = None


def _columns(table_name):
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)} if table_name in inspector.get_table_names() else set()


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("role", sa.String(20), nullable=True, server_default="merchant"),
            sa.Column("api_key", sa.String(64), nullable=True, unique=True),
            sa.Column("webhook_url", sa.String(500), nullable=True),
            sa.Column("webhook_secret", sa.String(128), nullable=True),
            sa.Column("settlement_asset", sa.String(20), nullable=True, server_default="NGN"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    else:
        existing = _columns("users")
        for name, column in {
            "webhook_url": sa.Column("webhook_url", sa.String(500), nullable=True),
            "webhook_secret": sa.Column("webhook_secret", sa.String(128), nullable=True),
            "settlement_asset": sa.Column("settlement_asset", sa.String(20), server_default="NGN", nullable=True),
        }.items():
            if name not in existing:
                op.add_column("users", column)
        op.execute("UPDATE users SET settlement_asset = 'NGN' WHERE settlement_asset IS NULL")

    if "transactions_ledger" not in tables:
        op.create_table(
            "transactions_ledger",
            sa.Column("tx_id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("fiat_amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(20), nullable=False),
            sa.Column("settlement_value", sa.Float(), nullable=False),
            sa.Column("current_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("previous_hash", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    elif "currency" in _columns("transactions_ledger"):
        op.alter_column("transactions_ledger", "currency", type_=sa.String(20), existing_type=sa.String(3))

    if "checkout_sessions" not in tables:
        op.create_table(
            "checkout_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("fiat_amount", sa.Float(), nullable=False),
            sa.Column("fiat_currency", sa.String(3), nullable=False),
            sa.Column("settlement_asset", sa.String(20), nullable=False),
            sa.Column("exchange_rate", sa.Float(), nullable=False),
            sa.Column("quote_id", sa.String(64), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    op.drop_table("checkout_sessions")
