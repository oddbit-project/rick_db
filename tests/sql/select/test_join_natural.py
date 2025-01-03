import pytest

from rick_db.sql import Select
from tests.sql.select.common import TABLE_NAME


def join_natural():
    return [
        [
            "table2",
            None,
            None,
            'SELECT "test_table".* FROM "test_table" NATURAL JOIN "table2"',
        ],
        [
            {"table2": "myalias"},
            None,
            None,
            'SELECT "test_table".* FROM "test_table" NATURAL JOIN "table2" AS "myalias"',
        ],
        [
            "table2",
            "field1",
            None,
            'SELECT "test_table".*,"table2"."field1" FROM "test_table" NATURAL JOIN "table2"',
        ],
        [
            "table2",
            ["field1", "field2"],
            "schema",
            'SELECT "test_table".*,"table2"."field1","table2"."field2" FROM "test_table" NATURAL JOIN "schema"."table2"',
        ],
        [
            {"table2": "alias"},
            ["field1", "field2"],
            "schema",
            'SELECT "test_table".*,"alias"."field1","alias"."field2" FROM "test_table" NATURAL JOIN "schema"."table2" AS "alias"',
        ],
    ]


class TestJoinNatural:
    @pytest.mark.parametrize("table, cols, schema, result", join_natural())
    def test_join_natural(self, table, cols, schema, result):
        sql, _ = (
            Select().from_(TABLE_NAME, "*").join_natural(table, cols, schema).assemble()
        )
        assert sql == result
