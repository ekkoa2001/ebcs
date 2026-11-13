"""create normalized product entries on every database

Revision ID: 0004_product_entries
Revises: 0003_creative_hooks
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_product_entries"
down_revision = "0003_creative_hooks"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if sa.inspect(bind).has_table("product_entries"):
        return
    op.create_table(
        "product_entries",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("hook_id", sa.String(80), sa.ForeignKey("creative_hooks.id"), nullable=False),
        sa.Column("code", sa.String(80), nullable=False, server_default=""),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("entry_type", sa.String(120), nullable=False, server_default=""),
        sa.Column("entry_time", sa.String(80), nullable=False, server_default=""),
        sa.Column("transition_logic", sa.Text(), nullable=False, server_default=""),
        sa.Column("selling_points", sa.Text(), nullable=False, server_default=""),
        sa.Column("visual_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("product", sa.String(200), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(40), nullable=False, server_default="待筛选"),
        sa.Column("is_example", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(64), nullable=False, server_default=""),
        sa.Column("owner", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(40), nullable=False, server_default=""),
        sa.Column("updated_at", sa.String(40), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.String(40), nullable=True),
        sa.Column("legacy_json", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_product_entries_hook", "product_entries", ["hook_id"])
    op.create_index("ix_product_entries_created_at", "product_entries", ["created_at"])


def downgrade():
    bind = op.get_bind()
    if sa.inspect(bind).has_table("product_entries"):
        op.drop_table("product_entries")
