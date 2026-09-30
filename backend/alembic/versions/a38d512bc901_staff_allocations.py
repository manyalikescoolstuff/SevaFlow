"""Admin-managed dated staff allocations."""
from alembic import op
import sqlalchemy as sa

revision = 'a38d512bc901'
down_revision = 'f14c9b7d2e10'
branch_labels = depends_on = None

def upgrade():
    op.create_table('staff_allocations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('staff_id', sa.String(), sa.ForeignKey('staff.id'), nullable=False),
        sa.Column('counter_id', sa.String(), sa.ForeignKey('counters.id'), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('source_counter_id', sa.String(), sa.ForeignKey('counters.id')),
        sa.Column('replaced_staff_id', sa.String(), sa.ForeignKey('staff.id')),
        sa.Column('created_by', sa.String(), sa.ForeignKey('staff.id'), nullable=False))

def downgrade():
    op.drop_table('staff_allocations')
