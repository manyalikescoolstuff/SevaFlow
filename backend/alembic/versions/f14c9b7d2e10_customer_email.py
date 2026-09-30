"""Store customer email for confirmation delivery."""
from alembic import op
import sqlalchemy as sa

revision = 'f14c9b7d2e10'
down_revision = 'e52a7109bc63'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('tokens', sa.Column('email', sa.String(254), nullable=True))

def downgrade():
    op.drop_column('tokens', 'email')
