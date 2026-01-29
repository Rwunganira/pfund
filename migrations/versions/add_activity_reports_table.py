"""add activity_reports table

Revision ID: add_activity_reports
Revises: cc81a4559d2e
Create Date: 2025-01-29

"""
from alembic import op
import sqlalchemy as sa


revision = "add_activity_reports"
down_revision = "cc81a4559d2e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "activity_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id", name="uq_activity_reports_activity_id"),
    )
    op.create_index(op.f("ix_activity_reports_activity_id"), "activity_reports", ["activity_id"], unique=True)
    op.create_index(op.f("ix_activity_reports_created_by"), "activity_reports", ["created_by"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_activity_reports_created_by"), table_name="activity_reports")
    op.drop_index(op.f("ix_activity_reports_activity_id"), table_name="activity_reports")
    op.drop_table("activity_reports")
