"""Added Payment Session Model

Revision ID: 87f32a03d60c
Revises:
Create Date: 2026-06-27 23:20:17.881945

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

revision = '87f32a03d60c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types owned by the payment service.
    # currency already exists (created by commerce-service migration) — skip it.
    op.execute("CREATE TYPE payment_status AS ENUM ('INITIATED', 'PENDING', 'CAPTURED', 'FAILED', 'REFUND_INITIATED', 'REFUNDED', 'CANCELLED')")
    op.execute("CREATE TYPE payment_method AS ENUM ('UPI', 'CARD', 'NET_BANKING', 'WALLET')")

    op.create_table(
        'payment_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('checkout_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', PGEnum(name='currency', create_type=False), nullable=False),
        sa.Column('status', PGEnum(name='payment_status', create_type=False), nullable=False),
        sa.Column('payment_method', PGEnum(name='payment_method', create_type=False), nullable=True),
        sa.Column('redirect_url', sa.String(length=2048), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_payment_sessions_checkout_id'), 'payment_sessions', ['checkout_id'], unique=False)
    op.create_index(op.f('ix_payment_sessions_user_id'), 'payment_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_payment_sessions_user_id'), table_name='payment_sessions')
    op.drop_index(op.f('ix_payment_sessions_checkout_id'), table_name='payment_sessions')
    op.drop_table('payment_sessions')
    op.execute("DROP TYPE payment_method")
    op.execute("DROP TYPE payment_status")
