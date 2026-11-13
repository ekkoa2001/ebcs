"""add team tasks

Revision ID: 0005_team_tasks
Revises: 0004_product_entries
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_team_tasks"
down_revision = "0004_product_entries"
branch_labels = None
depends_on = None

def upgrade():
    if sa.inspect(op.get_bind()).has_table("team_tasks"): return
    op.create_table("team_tasks",
        sa.Column("id",sa.String(80),primary_key=True), sa.Column("title",sa.String(300),nullable=False),
        sa.Column("entity_type",sa.String(40),nullable=False,server_default=""), sa.Column("entity_id",sa.String(80),nullable=False,server_default=""),
        sa.Column("assignee",sa.String(64),nullable=False,server_default=""), sa.Column("owner",sa.String(64),nullable=False,server_default=""),
        sa.Column("due_date",sa.String(20),nullable=False,server_default=""), sa.Column("status",sa.String(40),nullable=False,server_default="待处理"),
        sa.Column("priority",sa.String(20),nullable=False,server_default="普通"), sa.Column("notes",sa.Text(),nullable=False,server_default=""),
        sa.Column("created_by",sa.String(64),nullable=False,server_default=""), sa.Column("created_at",sa.String(40),nullable=False,server_default=""),
        sa.Column("updated_at",sa.String(40),nullable=False,server_default=""), sa.Column("version",sa.Integer(),nullable=False,server_default="1"),
        sa.Column("deleted_at",sa.String(40),nullable=True))

def downgrade():
    if sa.inspect(op.get_bind()).has_table("team_tasks"): op.drop_table("team_tasks")
