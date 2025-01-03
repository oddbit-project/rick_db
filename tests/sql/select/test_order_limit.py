import pytest

from rick_db.sql import PgSqlDialect, Select, Literal
from .common import TABLE_NAME


def limit():
    return [
        ["10", None, 'SELECT "test_table".* FROM "test_table" LIMIT 10'],
        [10, 15, 'SELECT "test_table".* FROM "test_table" LIMIT 10 OFFSET 15'],
    ]


def order():
    return [
        ["field1", None, 'SELECT "test_table".* FROM "test_table" ORDER BY "field1"'],
        [
            "field1",
            "desc",
            'SELECT "test_table".* FROM "test_table" ORDER BY "field1" desc',
        ],
        [
            Literal("SUM(field1)"),
            "desc",
            'SELECT "test_table".* FROM "test_table" ORDER BY SUM(field1) desc',
        ],
    ]


def page_limit():
    return [
        [1, 10, 'SELECT "test_table".* FROM "test_table" LIMIT 10 OFFSET 0'],
        [2, 10, 'SELECT "test_table".* FROM "test_table" LIMIT 10 OFFSET 10'],
        [10, 25, 'SELECT "test_table".* FROM "test_table" LIMIT 25 OFFSET 225'],
    ]


class TestOrderLimit:
    @pytest.mark.parametrize("limit, offset, result", limit())
    def test_limit(self, limit, offset, result):
        sql, _ = (
            Select(PgSqlDialect())
            .from_(TABLE_NAME, "*")
            .limit(limit, offset)
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize("field, order, result", order())
    def test_order(self, field, order, result):
        sql, _ = (
            Select(PgSqlDialect()).from_(TABLE_NAME, "*").order(field, order).assemble()
        )
        assert sql == result

    @pytest.mark.parametrize("page, page_rows, result", page_limit())
    def test_page(self, page, page_rows, result):
        sql, _ = (
            Select(PgSqlDialect())
            .from_(TABLE_NAME, "*")
            .page(page, page_rows)
            .assemble()
        )
        assert sql == result
