import pytest

from rick_db.sql import Literal, PgSqlDialect, Select
from tests.sql.select.common import SchemaTestTable, SomeRecord, TABLE_NAME


def having():
    return [
        # literals
        [
            Literal("COUNT(field) > 5"),
            None,
            None,
            None,
            'SELECT "test_table".* FROM "test_table" HAVING (COUNT(field) > 5)',
        ],
        [
            Literal("COUNT(field)"),
            ">",
            5,
            None,
            'SELECT "test_table".* FROM "test_table" HAVING (COUNT(field) > %s)',
        ],
        [
            Literal("COUNT(field)"),
            ">",
            5,
            "public",
            'SELECT "test_table".* FROM "test_table" HAVING (COUNT(field) > %s)',
        ],
        # strings
        [
            "field1",
            None,
            None,
            None,
            'SELECT "test_table".* FROM "test_table" HAVING ("field1")',
        ],
        [
            "field1",
            "IS",
            "NULL",
            None,
            'SELECT "test_table".* FROM "test_table" HAVING ("field1" IS %s)',
        ],
        [
            "field1 IS NULL",
            None,
            None,
            None,
            'SELECT "test_table".* FROM "test_table" HAVING ("field1 IS NULL")',
        ],
        # dict format {TableName:FieldName}
        [
            {SomeRecord: SomeRecord.field},
            ">",
            5,
            None,
            'SELECT "test_table".* FROM "test_table" HAVING ("test_table"."field" > %s)',
        ],
        [
            {SchemaTestTable: SchemaTestTable.field},
            ">",
            5,
            None,
            'SELECT "test_table".* FROM "test_table" HAVING ("public"."other_table"."field" > %s)',
        ],
    ]


class TestHaving:

    @pytest.mark.parametrize("field, operator, value, schema, result", having())
    def test_having(self, field, operator, value, schema, result):
        sql, _ = (
            Select(PgSqlDialect())
            .from_(TABLE_NAME, "*")
            .having(field, operator, value, schema)
            .assemble()
        )
        assert sql == result
