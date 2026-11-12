from pathlib import Path

from alembic import op

revision = "0002_business"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    schema = Path(__file__).resolve().parents[2] / "app" / "pg_schema.sql"
    for statement in schema.read_text(encoding="utf-8").split(";"):
        statement = statement.strip()
        if statement:
            op.execute(statement)


def downgrade():
    pass
