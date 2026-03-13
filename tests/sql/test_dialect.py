import pytest

from rick_db.sql import PgSqlDialect, SqlDialect
from rick_db.sql.common import Literal

TABLE_NAME = "test_table"


def sql_dialect_table():
    return [
        ["name", None, None, '"name"'],
        ["name", "alias", None, '"name" AS "alias"'],
        ["name", "alias", "schema", '"schema"."name" AS "alias"'],
        ["name", None, "schema", '"schema"."name"'],
    ]


def sql_dialect_database():
    return [
        ["name", None, '"name"'],
        ["name", "alias", '"name" AS "alias"'],
    ]


def sql_dialect_field():
    return [
        # simple fields
        ["field", None, None, None, '"field"'],
        ["field", "alias", None, None, '"field" AS "alias"'],
        ["field", "alias", "table", None, '"table"."field" AS "alias"'],
        ["field", "alias", "table", "schema", '"schema"."table"."field" AS "alias"'],
        # field literals
        [Literal("TOP(field)"), None, None, None, "TOP(field)"],
        [Literal("TOP(field)"), "alias", None, None, 'TOP(field) AS "alias"'],
        [
            Literal("TOP(field)"),
            "alias",
            "table",
            "schema",
            'TOP(field) AS "alias"',
        ],  # table and schema are ignored
        # field alias and casting
        ["field", ["text"], None, None, 'CAST("field" AS text)'],
        ["field", ["text"], "table", None, 'CAST("table"."field" AS text)'],
        [
            "field",
            ["text"],
            "table",
            "schema",
            'CAST("schema"."table"."field" AS text)',
        ],
        ["field", ["text", "alias"], None, None, 'CAST("field" AS text) AS "alias"'],
        [
            "field",
            ["text", "alias"],
            "table",
            None,
            'CAST("table"."field" AS text) AS "alias"',
        ],
        [
            "field",
            ["text", "alias"],
            "table",
            "schema",
            'CAST("schema"."table"."field" AS text) AS "alias"',
        ],
    ]


def pg_dialect_table():
    return [
        ["name", None, None, '"name"'],
        ["name", "alias", None, '"name" AS "alias"'],
        ["name", "alias", "schema", '"schema"."name" AS "alias"'],
        ["name", None, "schema", '"schema"."name"'],
    ]


def pg_dialect_field():
    return [
        # simple fields
        ["field", None, None, None, '"field"'],
        ["field", "alias", None, None, '"field" AS "alias"'],
        ["field", "alias", "table", None, '"table"."field" AS "alias"'],
        ["field", "alias", "table", "schema", '"schema"."table"."field" AS "alias"'],
        # field literals
        [Literal("TOP(field)"), None, None, None, "TOP(field)"],
        [Literal("TOP(field)"), "alias", None, None, 'TOP(field) AS "alias"'],
        [
            Literal("TOP(field)"),
            "alias",
            "table",
            "schema",
            'TOP(field) AS "alias"',
        ],  # table and schema are ignored
        # field alias and casting
        ["field", ["text"], None, None, '"field"::text'],
        ["field", ["text"], "table", None, '"table"."field"::text'],
        ["field", ["text"], "table", "schema", '"schema"."table"."field"::text'],
        ["field", ["text", "alias"], None, None, '"field"::text AS "alias"'],
        ["field", ["text", "alias"], "table", None, '"table"."field"::text AS "alias"'],
        [
            "field",
            ["text", "alias"],
            "table",
            "schema",
            '"schema"."table"."field"::text AS "alias"',
        ],
    ]


class TestSqlDialect:
    @pytest.mark.parametrize("table_name, alias, schema, result", sql_dialect_table())
    def test_sqldialect_table(self, table_name, alias, schema, result):
        assert PgSqlDialect().table(table_name, alias, schema) == result

    @pytest.mark.parametrize("db_name, alias, result", sql_dialect_database())
    def test_sqldialect_database(self, db_name, alias, result):
        assert PgSqlDialect().database(db_name, alias) == result

    @pytest.mark.parametrize(
        "field, field_alias, table, schema, result", sql_dialect_field()
    )
    def test_sqlitedialect_field(self, field, field_alias, table, schema, result):
        assert SqlDialect().field(field, field_alias, table, schema) == result

    def test_identifier_escaping_table(self):
        d = SqlDialect()
        # embedded double-quote must be doubled (SQL standard)
        assert d.table('tab"le') == '"tab""le"'
        assert d.table("safe") == '"safe"'
        # alias and schema are also escaped
        assert d.table("t", alias='a"lias') == '"t" AS "a""lias"'
        assert d.table("t", schema='s"ch') == '"s""ch"."t"'

    def test_identifier_escaping_field(self):
        d = SqlDialect()
        assert d.field('fi"eld') == '"fi""eld"'
        assert d.field("f", field_alias='a"l') == '"f" AS "a""l"'
        assert d.field("f", table='t"bl') == '"t""bl"."f"'

    def test_identifier_escaping_database(self):
        d = SqlDialect()
        assert d.database('db"name') == '"db""name"'
        assert d.database("db", alias='a"l') == '"db" AS "a""l"'

    def test_identifier_escaping_pg(self):
        d = PgSqlDialect()
        assert d.table('tab"le') == '"tab""le"'
        assert d.field('fi"eld') == '"fi""eld"'
        assert d.database('db"name') == '"db""name"'

    @pytest.mark.parametrize("table_name, alias, schema, result", pg_dialect_table())
    def test_pgsqldialect_table(self, table_name, alias, schema, result):
        assert PgSqlDialect().table(table_name, alias, schema) == result

    @pytest.mark.parametrize(
        "field, field_alias, table, schema, result", pg_dialect_field()
    )
    def test_pgsqldialect_field(self, field, field_alias, table, schema, result):
        assert PgSqlDialect().field(field, field_alias, table, schema) == result
