"""add_marketplace_extensions_and_payment_intents

Revision ID: b5f305e6f141
Revises: 5410a3febd57
Create Date: 2026-11-06 14:26:58.820008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5f305e6f141'
down_revision: Union[str, Sequence[str], None] = '5410a3febd57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Columns for providers
    if 'providers' in existing_tables:
        provider_cols = {col['name'] for col in inspector.get_columns('providers')}
        if 'is_platform_managed' not in provider_cols:
            op.add_column('providers', sa.Column('is_platform_managed', sa.Integer(), nullable=False, server_default='0'))
        if 'updated_at' not in provider_cols:
            op.add_column('providers', sa.Column('updated_at', sa.String(64), nullable=True))

    # 2. Columns for orders
    if 'orders' in existing_tables:
        order_cols = {col['name'] for col in inspector.get_columns('orders')}
        if 'rejection_reason' not in order_cols:
            op.add_column('orders', sa.Column('rejection_reason', sa.Text(), nullable=True))
        if 'payment_intent_id' not in order_cols:
            op.add_column('orders', sa.Column('payment_intent_id', sa.String(64), nullable=True))

    # 3. payment_intents table
    if 'payment_intents' not in existing_tables:
        op.create_table(
            'payment_intents',
            sa.Column('id', sa.String(64), primary_key=True),
            sa.Column('order_id', sa.String(64), nullable=False, index=True),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('currency', sa.String(20), nullable=False, server_default='USD'),
            sa.Column('status', sa.String(50), nullable=False, index=True),
            sa.Column('gateway', sa.String(50), nullable=False),
            sa.Column('external_reference', sa.String(255), nullable=True),
            sa.Column('failure_reason', sa.Text(), nullable=True),
            sa.Column('metadata', sa.Text(), nullable=True),
            sa.Column('created_at', sa.String(64), nullable=False),
            sa.Column('updated_at', sa.String(64), nullable=False),
            sa.Column('verified_at', sa.String(64), nullable=True),
        )

    # 4. request_attachments table
    if 'request_attachments' not in existing_tables:
        op.create_table(
            'request_attachments',
            sa.Column('id', sa.String(64), primary_key=True),
            sa.Column('order_id', sa.String(64), nullable=False, index=True),
            sa.Column('owner_id', sa.String(64), nullable=False),
            sa.Column('filename', sa.String(255), nullable=False),
            sa.Column('content_type', sa.String(100), nullable=True),
            sa.Column('storage_path', sa.String(500), nullable=False),
            sa.Column('created_at', sa.String(64), nullable=False),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'request_attachments' in existing_tables:
        op.drop_table('request_attachments')
    if 'payment_intents' in existing_tables:
        op.drop_table('payment_intents')

    if 'orders' in existing_tables:
        order_cols = {col['name'] for col in inspector.get_columns('orders')}
        if 'payment_intent_id' in order_cols:
            op.drop_column('orders', 'payment_intent_id')
        if 'rejection_reason' in order_cols:
            op.drop_column('orders', 'rejection_reason')

    if 'providers' in existing_tables:
        provider_cols = {col['name'] for col in inspector.get_columns('providers')}
        if 'updated_at' in provider_cols:
            op.drop_column('providers', 'updated_at')
        if 'is_platform_managed' in provider_cols:
            op.drop_column('providers', 'is_platform_managed')
