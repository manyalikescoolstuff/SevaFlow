"""Bind idempotent hardware/staff commands to their original payload."""
from alembic import op
import sqlalchemy as sa

revision = 'd34b1c607a2f'
down_revision = 'c81f2a9d401e'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('idempotency_records', sa.Column('request_hash', sa.String(64), nullable=True))

def downgrade():
    op.drop_column('idempotency_records', 'request_hash')
