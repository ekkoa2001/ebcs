"""create normalized creative hooks on every database

Revision ID: 0003_creative_hooks
Revises: 0002_business
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_creative_hooks"
down_revision = "0002_business"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if sa.inspect(bind).has_table("creative_hooks"):
        return
    op.create_table(
        "creative_hooks",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, server_default=""),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("hook_type", sa.String(120), nullable=False, server_default=""),
        sa.Column("product", sa.String(200), nullable=False, server_default=""),
        sa.Column("audience", sa.String(200), nullable=False, server_default=""),
        sa.Column("scene", sa.String(200), nullable=False, server_default=""),
        sa.Column("reference_material", sa.Text(), nullable=False, server_default=""),
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
    op.create_index("ix_creative_hooks_created_at", "creative_hooks", ["created_at"])
    op.create_index("ix_creative_hooks_created_by", "creative_hooks", ["created_by"])
    op.create_index("ix_creative_hooks_status", "creative_hooks", ["status"])


def downgrade():
    bind = op.get_bind()
    if sa.inspect(bind).has_table("creative_hooks"):
        op.drop_table("creative_hooks")
