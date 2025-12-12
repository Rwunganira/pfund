"""add budget_used_year1, budget_used_year2, budget_used_year3 columns

Revision ID: add_budget_used_by_year
Revises: d4b0ebf42fa1
Create Date: 2025-12-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_budget_used_by_year'
down_revision = 'd4b0ebf42fa1'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for budget used by year
    # Add as nullable with default 0
    op.add_column('activities', sa.Column('budget_used_year1', sa.Float(), nullable=True, server_default='0'))
    op.add_column('activities', sa.Column('budget_used_year2', sa.Float(), nullable=True, server_default='0'))
    op.add_column('activities', sa.Column('budget_used_year3', sa.Float(), nullable=True, server_default='0'))
    
    # Update existing rows: set budget_used_year1 to current budget_used, year2 and year3 to 0
    # This ensures existing data is migrated correctly
    op.execute("""
        UPDATE activities 
        SET budget_used_year1 = COALESCE(budget_used, 0),
            budget_used_year2 = 0,
            budget_used_year3 = 0
        WHERE budget_used_year1 IS NULL
    """)


def downgrade():
    # Remove the columns
    op.drop_column('activities', 'budget_used_year3')
    op.drop_column('activities', 'budget_used_year2')
    op.drop_column('activities', 'budget_used_year1')

