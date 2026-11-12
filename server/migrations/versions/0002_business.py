from pathlib import Path
import re

from alembic import op

revision = "0002_business"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


CREATE_TABLE = re.compile(
    r"^CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([\w\"]+)",
    re.IGNORECASE,
)
REFERENCE = re.compile(r"REFERENCES\s+([\w\"]+)", re.IGNORECASE)


def ordered_statements(sql: str) -> list[str]:
    """Put CREATE TABLE statements before objects that depend on them.

    pg_schema.sql is generated alphabetically, while PostgreSQL requires a
    referenced table to exist before a foreign key is declared.  Keep the SQL
    readable and make the migration responsible for dependency order.
    """
    statements = [item.strip() for item in sql.split(";") if item.strip()]
    tables: dict[str, str] = {}
    remaining: list[str] = []
    for statement in statements:
        match = CREATE_TABLE.match(statement)
        if match:
            tables[match.group(1).strip('"').lower()] = statement
        else:
            remaining.append(statement)

    ordered: list[str] = []
    pending = dict(tables)
    while pending:
        progressed = False
        for name, statement in list(pending.items()):
            dependencies = {
                value.strip('"').lower()
                for value in REFERENCE.findall(statement)
                if value.strip('"').lower() in tables
            }
            if dependencies.isdisjoint(pending.keys()):
                ordered.append(statement)
                del pending[name]
                progressed = True
        if not progressed:
            cycle = ", ".join(sorted(pending))
            raise RuntimeError(f"Circular table dependency in pg_schema.sql: {cycle}")

    return ordered + remaining


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    schema = Path(__file__).resolve().parents[2] / "app" / "pg_schema.sql"
    for statement in ordered_statements(schema.read_text(encoding="utf-8")):
        op.execute(statement)


def downgrade():
    pass
