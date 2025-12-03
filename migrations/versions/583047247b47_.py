"""empty message

Revision ID: 583047247b47
Revises: 
Create Date: 2025-12-01 15:34:36.254033

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '583047247b47'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Only adjust the users table for this migration.
    # Check if 'confirmed' column already exists (for production databases)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    confirmed_exists = 'confirmed' in columns
    
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Only add 'confirmed' column if it doesn't exist
        if not confirmed_exists:
            batch_op.add_column(sa.Column('confirmed', sa.Boolean(), nullable=True))
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=False,
               autoincrement=True)
        batch_op.alter_column('username',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=False)
        batch_op.alter_column('email',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
        batch_op.alter_column('password_hash',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=False)
        batch_op.alter_column('role',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=False)
    
    # Check if unique constraint already exists before creating
    constraints = [c['name'] for c in inspector.get_unique_constraints('users')]
    if 'uq_users_email' not in constraints:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_users_email', ['email'])

    # ### end Alembic commands ###


def downgrade():
    # Reverse changes to the users table.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('uq_users_email', type_='unique')
        batch_op.alter_column('role',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=False)
        batch_op.alter_column('password_hash',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=False)
        batch_op.alter_column('email',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
        batch_op.alter_column('username',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=False)
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=True,
               autoincrement=True)
        batch_op.drop_column('confirmed')

