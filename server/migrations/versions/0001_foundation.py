"""foundation tables for sessions, roles and audit

Revision ID: 0001_foundation
Revises:
Create Date: 2026-11-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sessions",
        sa.Column("token", sa.String(128), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("csrf", sa.String(128), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("active_at", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payload", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_sessions_username", "sessions", ["username"])
    op.create_table(
        "roles",
        sa.Column("name", sa.String(32), primary_key=True),
        sa.Column("label", sa.String(32), nullable=False),
    )
    op.create_table(
        "permissions",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("description", sa.String(200), nullable=False),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role_name", sa.String(32), sa.ForeignKey("roles.name"), nullable=False),
        sa.Column("permission_code", sa.String(64), sa.ForeignKey("permissions.code"), nullable=False),
        sa.UniqueConstraint("role_name", "permission_code"),
    )
    op.create_index("ix_role_permissions_role_name", "role_permissions", ["role_name"])
    op.create_index("ix_role_permissions_permission_code", "role_permissions", ["permission_code"])
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("time", sa.String(19), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("module", sa.String(40), nullable=False, server_default="v1"),
        sa.Column("action", sa.String(300), nullable=False),
        sa.Column("object_type", sa.String(40), nullable=False, server_default=""),
        sa.Column("object_id", sa.String(80), nullable=False, server_default=""),
        sa.Column("result", sa.String(20), nullable=False, server_default="success"),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(300), nullable=False, server_default=""),
        sa.Column("repeat_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_activity_logs_time", "activity_logs", ["time"])
    op.create_index("ix_activity_logs_actor", "activity_logs", ["actor"])


def downgrade():
    op.drop_table("activity_logs")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("sessions")
