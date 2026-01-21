"""Add unique constraint to activity_id in indicators for one-to-one relationship

Revision ID: cc81a4559d2e
Revises: 0f5775b0d0d2
Create Date: 2026-01-21 14:18:43.067848

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cc81a4559d2e'
down_revision = '0f5775b0d0d2'
branch_labels = None
depends_on = None


def upgrade():
    # Add unique constraint to activity_id for one-to-one relationship
    with op.batch_alter_table('indicators', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_indicators_activity_id', ['activity_id'])


def downgrade():
    # Remove unique constraint
    with op.batch_alter_table('indicators', schema=None) as batch_op:
        batch_op.drop_constraint('uq_indicators_activity_id', type_='unique')
