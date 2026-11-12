import importlib.util
from pathlib import Path


def migration_module():
    path = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0002_business.py"
    spec = importlib.util.spec_from_file_location("business_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def table_name(statement, pattern):
    match = pattern.match(statement)
    return match.group(1).strip('"').lower() if match else None


def test_foreign_key_dependencies_are_created_first():
    module = migration_module()
    schema = Path(__file__).resolve().parents[1] / "app" / "pg_schema.sql"
    statements = module.ordered_statements(schema.read_text(encoding="utf-8"))
    positions = {
        name: index
        for index, statement in enumerate(statements)
        if (name := table_name(statement, module.CREATE_TABLE))
    }

    for statement in statements:
        source = table_name(statement, module.CREATE_TABLE)
        if not source:
            continue
        for target in module.REFERENCE.findall(statement):
            target = target.strip('"').lower()
            if target in positions:
                assert positions[target] < positions[source], f"{target} must exist before {source}"


def test_cycle_is_reported():
    module = migration_module()
    sql = """
    CREATE TABLE a (id INT PRIMARY KEY, b_id INT REFERENCES b(id));
    CREATE TABLE b (id INT PRIMARY KEY, a_id INT REFERENCES a(id));
    """
    try:
        module.ordered_statements(sql)
    except RuntimeError as error:
        assert "Circular table dependency" in str(error)
    else:
        raise AssertionError("A dependency cycle must stop the migration")
