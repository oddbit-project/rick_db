import pytest

from rick_db.sql import PgSqlDialect, SqlDialect
from rick_db.sql.common import Literal

TABLE_NAME = 'test_table'

# SqlDialect -----------------------------------------------------------------------------------------------------------
sql_dialect_table = [
    ["name", None, None, '"name"'],
    ["name", "alias", None, '"name" AS "alias"'],
    ["name", "alias", "schema", '"schema"."name" AS "alias"'],
    ["name", None, "schema", '"schema"."name"'],
]


@pytest.mark.parametrize("table_name, alias, schema, result", sql_dialect_table)
def test_sqldialect_table(table_name, alias, schema, result):
    assert PgSqlDialect().table(table_name, alias, schema) == result


sql_dialect_field = [
    # simple fields
    ["field", None, None, None, '"field"'],
    ["field", "alias", None, None, '"field" AS "alias"'],
    ["field", "alias", "table", None, '"table"."field" AS "alias"'],
    ["field", "alias", "table", "schema", '"schema"."table"."field" AS "alias"'],
    # field literals
    [Literal("TOP(field)"), None, None, None, 'TOP(field)'],
    [Literal("TOP(field)"), "alias", None, None, 'TOP(field) AS "alias"'],
    [Literal("TOP(field)"), "alias", "table", "schema", 'TOP(field) AS "alias"'],  # table and schema are ignored
    # field alias and casting
    ["field", ["text"], None, None, 'CAST("field" AS text)'],
    ["field", ["text"], "table", None, 'CAST("table"."field" AS text)'],
    ["field", ["text"], "table", "schema", 'CAST("schema"."table"."field" AS text)'],
    ["field", ["text", "alias"], None, None, 'CAST("field" AS text) AS "alias"'],
    ["field", ["text", "alias"], "table", None, 'CAST("table"."field" AS text) AS "alias"'],
    ["field", ["text", "alias"], "table", "schema", 'CAST("schema"."table"."field" AS text) AS "alias"'],
]


@pytest.mark.parametrize("field, field_alias, table, schema, result", sql_dialect_field)
def test_sqlitedialect_field(field, field_alias, table, schema, result):
    assert SqlDialect().field(field, field_alias, table, schema) == result


# PgSqlDialect ---------------------------------------------------------------------------------------------------------
pg_dialect_table = [
    ["name", None, None, '"name"'],
    ["name", "alias", None, '"name" AS "alias"'],
    ["name", "alias", "schema", '"schema"."name" AS "alias"'],
    ["name", None, "schema", '"schema"."name"'],
]


@pytest.mark.parametrize("table_name, alias, schema, result", pg_dialect_table)
def test_pgsqldialect_table(table_name, alias, schema, result):
    assert PgSqlDialect().table(table_name, alias, schema) == result


pg_dialect_field = [
    # simple fields
    ["field", None, None, None, '"field"'],
    ["field", "alias", None, None, '"field" AS "alias"'],
    ["field", "alias", "table", None, '"table"."field" AS "alias"'],
    ["field", "alias", "table", "schema", '"schema"."table"."field" AS "alias"'],
    # field literals
    [Literal("TOP(field)"), None, None, None, 'TOP(field)'],
    [Literal("TOP(field)"), "alias", None, None, 'TOP(field) AS "alias"'],
    [Literal("TOP(field)"), "alias", "table", "schema", 'TOP(field) AS "alias"'],  # table and schema are ignored
    # field alias and casting
    ["field", ["text"], None, None, '"field"::text'],
    ["field", ["text"], "table", None, '"table"."field"::text'],
    ["field", ["text"], "table", "schema", '"schema"."table"."field"::text'],
    ["field", ["text", "alias"], None, None, '"field"::text AS "alias"'],
    ["field", ["text", "alias"], "table", None, '"table"."field"::text AS "alias"'],
    ["field", ["text", "alias"], "table", "schema", '"schema"."table"."field"::text AS "alias"'],
]


@pytest.mark.parametrize("field, field_alias, table, schema, result", pg_dialect_field)
def test_pgsqldialect_field(field, field_alias, table, schema, result):
    assert PgSqlDialect().field(field, field_alias, table, schema) == result
