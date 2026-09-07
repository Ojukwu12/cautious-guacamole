"""Add configurable payment methods and mock withdrawals."""
from alembic import op
import sqlalchemy as sa

revision = "20260903_0002"
down_revision = "20260902_0001"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    session_columns = {column["name"] for column in inspector.get_columns("checkout_sessions")}
    if "payment_options" not in user_columns:
        op.add_column("users", sa.Column("payment_options", sa.JSON(), nullable=True))
        op.execute("UPDATE users SET payment_options = '[\"card\", \"bank_transfer\", \"bank_app\", \"crypto\"]' WHERE payment_options IS NULL")
    if "payment_options" not in session_columns:
        op.add_column("checkout_sessions", sa.Column("payment_options", sa.JSON(), nullable=True))
        op.execute("UPDATE checkout_sessions SET payment_options = '[\"card\", \"bank_transfer\", \"bank_app\", \"crypto\"]' WHERE payment_options IS NULL")
    if "withdrawals" not in inspector.get_table_names():
        op.create_table(
            "withdrawals",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column("merchant_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("asset", sa.String(20), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("destination", sa.String(120), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="processing"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    op.drop_table("withdrawals")
    op.drop_column("checkout_sessions", "payment_options")
    op.drop_column("users", "payment_options")
