"""Initial Postgres schema

Revision ID: 9c8679bbfebc
Revises: 
Create Date: 2026-09-28 09:03:56.865443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c8679bbfebc'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Independent tables first
    op.create_table('services',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('expected_duration_sec', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('staff',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_staff_username'), 'staff', ['username'], unique=True)

    op.create_table('event_logs',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('entity_type', sa.String(), nullable=False),
    sa.Column('entity_id', sa.String(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('actor_id', sa.String(), nullable=True),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_logs_entity_id'), 'event_logs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_event_logs_event_type'), 'event_logs', ['event_type'], unique=False)

    op.create_table('idempotency_records',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('device_id', sa.String(), nullable=False),
    sa.Column('hardware_request_id', sa.String(), nullable=False),
    sa.Column('response_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('device_id', 'hardware_request_id', name='uq_idempotency_device_request')
    )
    op.create_index(op.f('ix_idempotency_records_device_id'), 'idempotency_records', ['device_id'], unique=False)
    op.create_index(op.f('ix_idempotency_records_hardware_request_id'), 'idempotency_records', ['hardware_request_id'], unique=False)

    # 2. Queues table (depends on services)
    op.create_table('queues',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('service_id', sa.String(), nullable=False),
    sa.Column('current_sequence', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('service_id')
    )

    # 3. Counters table (without foreign key to tokens yet)
    op.create_table('counters',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('label', sa.String(), nullable=False),
    sa.Column('service_id', sa.String(), nullable=False),
    sa.Column('queue_id', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('staff_id', sa.String(), nullable=True),
    sa.Column('current_token_id', sa.String(), nullable=True),
    sa.Column('served_today', sa.Integer(), nullable=False),
    sa.Column('avg_service_time_sec', sa.Integer(), nullable=False),
    sa.Column('serving_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['queue_id'], ['queues.id'], ),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
    sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_counter_active_token', 'counters', ['current_token_id'], unique=True, postgresql_where=sa.text('current_token_id IS NOT NULL'))

    # 4. Tokens table (without foreign key to counters yet)
    op.create_table('tokens',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('display_number', sa.String(), nullable=False),
    sa.Column('queue_id', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('hardware_reservation_id', sa.String(), nullable=False),
    sa.Column('claim_secret_hash', sa.String(), nullable=False),
    sa.Column('recovery_credential_hash', sa.String(), nullable=True),
    sa.Column('claim_session_id', sa.String(), nullable=True),
    sa.Column('tracking_secret_hash', sa.String(), nullable=True),
    sa.Column('scan_sequence', sa.BigInteger(), nullable=True),
    sa.Column('sort_key', sa.BigInteger(), nullable=True),
    sa.Column('recall_attempts', sa.Integer(), nullable=False),
    sa.Column('missed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('missed_counter_id', sa.String(), nullable=True),
    sa.Column('reservation_expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('registered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('called_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('serving_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['queue_id'], ['queues.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('claim_session_id')
    )
    op.create_index('ix_token_missed_counter', 'tokens', ['missed_counter_id', 'missed_at'], unique=False, postgresql_where=sa.text("status IN ('MISSED')"))
    op.create_index('ix_token_queue_status_sort', 'tokens', ['queue_id', 'status', 'sort_key'], unique=False)
    op.create_index(op.f('ix_tokens_display_number'), 'tokens', ['display_number'], unique=False)
    op.create_index(op.f('ix_tokens_hardware_reservation_id'), 'tokens', ['hardware_reservation_id'], unique=True)
    op.create_index(op.f('ix_tokens_queue_id'), 'tokens', ['queue_id'], unique=False)
    op.create_index(op.f('ix_tokens_scan_sequence'), 'tokens', ['scan_sequence'], unique=False)
    op.create_index(op.f('ix_tokens_sort_key'), 'tokens', ['sort_key'], unique=False)
    op.create_index(op.f('ix_tokens_status'), 'tokens', ['status'], unique=False)

    # 5. Add cross/circular foreign keys after both tables exist
    op.create_foreign_key('fk_counters_current_token_id', 'counters', 'tokens', ['current_token_id'], ['id'])
    op.create_foreign_key('fk_tokens_missed_counter_id', 'tokens', 'counters', ['missed_counter_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_tokens_missed_counter_id', 'tokens', type_='foreignkey')
    op.drop_constraint('fk_counters_current_token_id', 'counters', type_='foreignkey')

    op.drop_index(op.f('ix_tokens_status'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_sort_key'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_scan_sequence'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_queue_id'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_hardware_reservation_id'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_display_number'), table_name='tokens')
    op.drop_index('ix_token_queue_status_sort', table_name='tokens')
    op.drop_index('ix_token_missed_counter', table_name='tokens', postgresql_where=sa.text("status IN ('MISSED')"))
    op.drop_table('tokens')

    op.drop_index('ix_counter_active_token', table_name='counters', postgresql_where=sa.text('current_token_id IS NOT NULL'))
    op.drop_table('counters')

    op.drop_table('queues')
    op.drop_index(op.f('ix_idempotency_records_hardware_request_id'), table_name='idempotency_records')
    op.drop_index(op.f('ix_idempotency_records_device_id'), table_name='idempotency_records')
    op.drop_table('idempotency_records')

    op.drop_index(op.f('ix_event_logs_event_type'), table_name='event_logs')
    op.drop_index(op.f('ix_event_logs_entity_id'), table_name='event_logs')
    op.drop_table('event_logs')

    op.drop_index(op.f('ix_staff_username'), table_name='staff')
    op.drop_table('staff')

    op.drop_table('services')

