"""Added Payment_Session_ID in checkout table

Revision ID: b4f25abad163
Revises: 59d17e6243b9
Create Date: 2026-06-28 00:36:36.498427

"""
from alembic import op
import sqlalchemy as sa

revision = 'b4f25abad163'
down_revision = '59d17e6243b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('checkouts', sa.Column('payment_session_id', sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column('checkouts', 'payment_session_id')
