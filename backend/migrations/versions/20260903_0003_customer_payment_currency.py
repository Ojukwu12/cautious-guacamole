"""Store the customer's selected payment currency and amount."""
from alembic import op
import sqlalchemy as sa

revision = "20260903_0003"
down_revision = "20260903_0002"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("transactions_ledger")}
    if "payment_currency" not in columns:
        op.add_column("transactions_ledger", sa.Column("payment_currency", sa.String(10), nullable=True))
    if "payment_amount" not in columns:
        op.add_column("transactions_ledger", sa.Column("payment_amount", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("transactions_ledger", "payment_amount")
    op.drop_column("transactions_ledger", "payment_currency")
