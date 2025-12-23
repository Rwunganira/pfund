"""add_indicator_progress_tracking

Revision ID: 0968a2787c01
Revises: add_indicators
Create Date: 2025-12-23 18:47:43.081527

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0968a2787c01'
down_revision = 'add_indicators'
branch_labels = None
depends_on = None


def upgrade():
    # Add actual achievement values
    op.add_column('indicators', sa.Column('actual_baseline', sa.Text(), nullable=True))
    op.add_column('indicators', sa.Column('actual_year1', sa.Text(), nullable=True))
    op.add_column('indicators', sa.Column('actual_year2', sa.Text(), nullable=True))
    op.add_column('indicators', sa.Column('actual_year3', sa.Text(), nullable=True))
    
    # Add progress percentages
    op.add_column('indicators', sa.Column('progress_year1', sa.Float(), nullable=True))
    op.add_column('indicators', sa.Column('progress_year2', sa.Float(), nullable=True))
    op.add_column('indicators', sa.Column('progress_year3', sa.Float(), nullable=True))
    
    # Add progress status
    op.add_column('indicators', sa.Column('status_year1', sa.String(), nullable=True))
    op.add_column('indicators', sa.Column('status_year2', sa.String(), nullable=True))
    op.add_column('indicators', sa.Column('status_year3', sa.String(), nullable=True))
    
    # Add last progress update timestamp
    op.add_column('indicators', sa.Column('last_progress_update', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('indicators', 'last_progress_update')
    op.drop_column('indicators', 'status_year3')
    op.drop_column('indicators', 'status_year2')
    op.drop_column('indicators', 'status_year1')
    op.drop_column('indicators', 'progress_year3')
    op.drop_column('indicators', 'progress_year2')
    op.drop_column('indicators', 'progress_year1')
    op.drop_column('indicators', 'actual_year3')
    op.drop_column('indicators', 'actual_year2')
    op.drop_column('indicators', 'actual_year1')
    op.drop_column('indicators', 'actual_baseline')
