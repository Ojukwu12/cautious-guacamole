"""Add platform fee fields and password reset tokens."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260907_0005"
down_revision = "20260903_0004"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in ("transactions_ledger", "checkout_sessions"):
        columns = {column["name"] for column in inspector.get_columns(table)}
        for name in ("platform_fee_percentage", "platform_fee_value", "customer_total"):
            if name not in columns:
                op.add_column(table, sa.Column(name, sa.Float(), nullable=True, server_default="0"))
    op.execute("UPDATE transactions_ledger SET platform_fee_percentage = 3, platform_fee_value = 0, customer_total = COALESCE(payment_amount, 0) WHERE platform_fee_percentage IS NULL")
    op.execute("UPDATE checkout_sessions SET platform_fee_percentage = 3, platform_fee_value = 0, customer_total = fiat_amount WHERE platform_fee_percentage IS NULL")
    if "password_reset_tokens" not in inspector.get_table_names():
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    op.drop_table("password_reset_tokens")
    for table in ("transactions_ledger", "checkout_sessions"):
        for name in ("customer_total", "platform_fee_value", "platform_fee_percentage"):
            op.drop_column(table, name)
