"""Persist recall eligibility across pauses, retries and restarts."""
from alembic import op
import sqlalchemy as sa

revision = 'e52a7109bc63'
down_revision = 'd34b1c607a2f'
branch_labels = None
depends_on = None


def upgrade():
    # Existing missed tokens wait for a new actual service completion. Do not
    # invent completion history or consume an opportunity during migration.
    op.add_column('tokens', sa.Column('recall_ready', sa.Boolean(), nullable=False,
                                     server_default=sa.false()))


def downgrade():
    op.drop_column('tokens', 'recall_ready')
