import pytest

from rick_db.sql import Select, PgSqlDialect, Literal
from tests.sql.select.common import TABLE_NAME, SomeRecord, SchemaTestTable


def expr():
    return [
        [None, "SELECT None"],
        [1, "SELECT 1"],
        [[1, 2, 3], "SELECT 1,2,3"],
        ["now()", "SELECT now()"],
        [{"now()": None}, "SELECT now()"],
        [{1: None, 2: "second", 3: "third"}, 'SELECT 1,2 AS "second",3 AS "third"'],
        [{"now()": "datetime"}, 'SELECT now() AS "datetime"'],
    ]


def group_by():
    return [
        [[], 'SELECT "test_table".* FROM "test_table"'],
        ["field", 'SELECT "test_table".* FROM "test_table" GROUP BY "field"'],
        [
            ["field", "other"],
            'SELECT "test_table".* FROM "test_table" GROUP BY "field", "other"',
        ],
        [
            Literal("SUM(field)"),
            'SELECT "test_table".* FROM "test_table" GROUP BY SUM(field)',
        ],
        [
            [Literal("SUM(field)")],
            'SELECT "test_table".* FROM "test_table" GROUP BY SUM(field)',
        ],
        [
            [Literal("SUM(field)"), "other"],
            'SELECT "test_table".* FROM "test_table" GROUP BY SUM(field), "other"',
        ],
    ]


class TestSelect:

    def test_distinct(self):
        sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "field").distinct().assemble()
        assert sql == 'SELECT DISTINCT "field" FROM "test_table"'

    def test_for_update(self):
        sql, _ = (
            Select(PgSqlDialect()).from_(TABLE_NAME, "field").for_update().assemble()
        )
        assert sql == 'SELECT "field" FROM "test_table" FOR UPDATE'
        sql, _ = (
            Select(PgSqlDialect())
            .from_(TABLE_NAME, "field")
            .for_update(False)
            .assemble()
        )
        assert sql == 'SELECT "field" FROM "test_table"'

    @pytest.mark.parametrize("cols, result", expr())
    def test_expr(self, cols, result):
        sql, _ = Select(PgSqlDialect()).expr(cols).assemble()
        assert sql == result

    @pytest.mark.parametrize("cols, result", group_by())
    def test_group(self, cols, result):
        sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "*").group(cols).assemble()
        assert sql == result

    def test_union(self):
        qry_union = Select(PgSqlDialect()).union(
            [
                Select(PgSqlDialect()).from_(SomeRecord),
                Select(PgSqlDialect()).from_(SchemaTestTable),
            ]
        )
        sql, _ = qry_union.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" UNION SELECT "other_table".* FROM "public"."other_table"'
        )
