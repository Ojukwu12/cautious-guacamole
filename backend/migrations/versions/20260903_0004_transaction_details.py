"""Store transaction method and status."""
from alembic import op
import sqlalchemy as sa

revision = "20260903_0004"
down_revision = "20260903_0003"
branch_labels = None
depends_on = None

def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("transactions_ledger")}
    if "payment_method" not in columns:
        op.add_column("transactions_ledger", sa.Column("payment_method", sa.String(30), nullable=True))
    if "status" not in columns:
        op.add_column("transactions_ledger", sa.Column("status", sa.String(20), nullable=True, server_default="completed"))
    op.execute("UPDATE transactions_ledger SET status = 'completed' WHERE status IS NULL")

def downgrade():
    op.drop_column("transactions_ledger", "status")
    op.drop_column("transactions_ledger", "payment_method")