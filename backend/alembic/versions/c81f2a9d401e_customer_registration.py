"""Persist customer registration details without changing existing queue order."""
from alembic import op
import sqlalchemy as sa

revision = "c81f2a9d401e"
down_revision = "9c8679bbfebc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tokens", sa.Column("customer_name", sa.String(120), nullable=True))
    op.add_column("tokens", sa.Column("phone_number", sa.String(10), nullable=True))


def downgrade():
    op.drop_column("tokens", "phone_number")
    op.drop_column("tokens", "customer_name")
