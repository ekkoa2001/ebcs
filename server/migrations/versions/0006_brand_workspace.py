"""add products, after-sales emails and brand milestones

Revision ID: 0006_brand_workspace
Revises: 0005_team_tasks
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_brand_workspace"
down_revision = "0005_team_tasks"
branch_labels = None
depends_on = None


def standard_columns(table, title):
    return [
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column(title, sa.String(300), nullable=False),
        sa.Column("created_by", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(40), nullable=False, server_default=""),
        sa.Column("updated_at", sa.String(40), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.String(40), nullable=True),
    ]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("products"):
        op.create_table("products",
            *standard_columns("products", "name"),
            sa.Column("brand", sa.String(200), nullable=False, server_default=""),
            sa.Column("owner", sa.String(64), nullable=False, server_default=""),
            sa.Column("status", sa.String(40), nullable=False, server_default="进行中"),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
        )
    if not inspector.has_table("after_sales_emails"):
        op.create_table("after_sales_emails",
            *standard_columns("after_sales_emails", "title"),
            sa.Column("project_id", sa.String(80), nullable=False),
            sa.Column("preview_text", sa.String(500), nullable=False, server_default=""),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_after_sales_emails_project", "after_sales_emails", ["project_id"])
    if not inspector.has_table("brand_milestones"):
        op.create_table("brand_milestones",
            *standard_columns("brand_milestones", "title"),
            sa.Column("milestone_date", sa.String(20), nullable=False),
            sa.Column("end_date", sa.String(20), nullable=False, server_default=""),
            sa.Column("category", sa.String(40), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="进行中"),
            sa.Column("owner", sa.String(64), nullable=False, server_default=""),
            sa.Column("product", sa.String(200), nullable=False, server_default=""),
            sa.Column("related_item", sa.String(300), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("outcome", sa.Text(), nullable=False, server_default=""),
        )
        op.create_index("ix_brand_milestones_date", "brand_milestones", ["milestone_date"])


def downgrade():
    pass
