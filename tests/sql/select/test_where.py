import pytest

from rick_db.sql import Select, Literal, PgSqlDialect
from tests.sql.select.common import SomeRecord, TABLE_NAME


def where_simple():
    return [
        # field names
        [
            "field1",
            "=",
            32,
            'SELECT "test_table".* FROM "test_table" WHERE ("field1" = %s)',
        ],
        [
            "field1",
            ">",
            32,
            'SELECT "test_table".* FROM "test_table" WHERE ("field1" > %s)',
        ],
        [
            {"test_table": "field1"},
            "=",
            32,
            'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field1" = %s)',
        ],
        [
            {SomeRecord: SomeRecord.field},
            "=",
            32,
            'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field" = %s)',
        ],
        [
            "field1",
            "in",
            "(1,2,3,4,5,6)",
            'SELECT "test_table".* FROM "test_table" WHERE ("field1" in %s)',
        ],
        [
            "field1",
            "in (1,2,3,4,5,6)",
            None,
            'SELECT "test_table".* FROM "test_table" WHERE ("field1" in (1,2,3,4,5,6))',
        ],
        # expressions
        [
            Literal("MAX(field1)"),
            ">",
            32,
            'SELECT "test_table".* FROM "test_table" WHERE (MAX(field1) > %s)',
        ],
        [
            Literal("TOP(field1)"),
            "is null",
            None,
            'SELECT "test_table".* FROM "test_table" WHERE (TOP(field1) is null)',
        ],
        [
            Literal(SomeRecord.field + " is null or field > 0"),
            None,
            None,
            'SELECT "test_table".* FROM "test_table" WHERE (field is null or field > 0)',
        ],
        [
            SomeRecord.field,
            "in",
            Select().from_("test", ["id"]).where(Literal("SUM(total)"), ">", 0),
            'SELECT "test_table".* FROM "test_table" WHERE ("field" in (SELECT "id" FROM "test" WHERE (SUM(total) > ?)))',
        ],
    ]


def where_and():
    return [
        [
            "field1",
            ">",
            12,
            "field1",
            "<",
            16,
            'SELECT "test_table".* FROM "test_table" WHERE ("field1" > %s) AND ("field1" < %s)',
        ],
        [
            {"test_table": "field1"},
            ">",
            12,
            {"test_table": "field1"},
            "<",
            16,
            'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field1" > %s) AND ("test_table"."field1" < %s)',
        ],
        [
            {SomeRecord: SomeRecord.field},
            ">",
            12,
            {SomeRecord: SomeRecord.field},
            "<",
            16,
            'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field" > %s) AND ("test_table"."field" < %s)',
        ],
    ]


def where_or():
    return [
        [
            "field1",
            ">",
            12,
            "field1",
            "<",
            16,
            'SELECT "test_table".* FROM "test_table" WHERE ("field1" > %s) OR ("field1" < %s)',
        ],
        [
            {"test_table": "field1"},
            ">",
            12,
            {"test_table": "field1"},
            "<",
            16,
            'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field1" > %s) OR ("test_table"."field1" < %s)',
        ],
        [
            {SomeRecord: SomeRecord.field},
            ">",
            12,
            {SomeRecord: SomeRecord.field},
            "<",
            16,
            'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field" > %s) OR ("test_table"."field" < %s)',
        ],
    ]


class TestWhere:

    @pytest.mark.parametrize("field, operator, value, result", where_simple())
    def test_where_simple(self, field, operator, value, result):
        sql, _ = (
            Select(PgSqlDialect())
            .from_(TABLE_NAME, "*")
            .where(field, operator, value)
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize(
        "field, operator, value,field1, operator1, value1, result", where_and()
    )
    def test_where(self, field, operator, value, field1, operator1, value1, result):
        sql, _ = (
            Select(PgSqlDialect())
            .from_(TABLE_NAME, "*")
            .where(field, operator, value)
            .where(field1, operator1, value1)
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize(
        "field, operator, value,field1, operator1, value1, result", where_or()
    )
    def test_orwhere(self, field, operator, value, field1, operator1, value1, result):
        sql, _ = (
            Select(PgSqlDialect())
            .from_(TABLE_NAME, "*")
            .where(field, operator, value)
            .orwhere(field1, operator1, value1)
            .assemble()
        )
        assert sql == result

    def test_where_and(self):
        # test with AND group in the beginning
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where_and()
            .where("field1", "=", 1)
            .where("field2", "=", 2)
            .where_end()
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) )'
        )
        assert values == [1, 2]

        # AND group and parameter
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where("field3", "=", 3)
            .where_and()
            .where("field1", "=", 1)
            .where("field2", "=", 2)
            .where_end()
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ("field3" = %s) AND ( ("field1" = %s) AND ("field2" '
            "= %s) )"
        )
        assert values == [3, 1, 2]

        # AND group and two parameters
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where("field3", "=", 3)
            .where_and()
            .where("field1", "=", 1)
            .where("field2", "=", 2)
            .where_end()
            .where("field4", "=", 4)
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ("field3" = %s) AND ( ("field1" = %s) AND ("field2" '
            '= %s) ) AND ("field4" = %s)'
        )
        assert values == [3, 1, 2, 4]

        # nested AND group
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where_and()
            .where("field1", "=", 1)
            .where_and()
            .where("field2", "=", 2)
            .orwhere("field3", "=", 3)
            .where_end()
            .where("field4", "=", 4)
            .where_end()
            .where("field5", "=", 5)
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ( ("field2" = %s) OR ("field3" '
            '= %s) ) AND ("field4" = %s) ) AND ("field5" = %s)'
        )
        assert values == [1, 2, 3, 4, 5]

        # Two AND groups
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where_and()
            .where("field1", "=", 1)
            .where("field2", "=", 2)
            .where_end()
            .where_and()
            .where("field3", "=", 3)
            .orwhere("field4", "=", 4)
            .where_end()
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) ) AND ( ('
            '"field3" = %s) OR ("field4" = %s) )'
        )
        assert values == [1, 2, 3, 4]

    def test_where_or(self):
        # test with OR group in the beginning
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where_or()
            .where("field1", "=", 1)
            .where("field2", "=", 2)
            .where_end()
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) )'
        )
        assert values == [1, 2]

        # OR group and parameter
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where("field3", "=", 3)
            .where_or()
            .where("field1", "=", 1)
            .where("field2", "=", 2)
            .where_end()
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ("field3" = %s) OR ( ("field1" = %s) AND ("field2" = '
            "%s) )"
        )
        assert values == [3, 1, 2]

        # OR group and two parameters
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where("field3", "=", 3)
            .where_or()
            .where("field1", "=", 1)
            .where("field2", "=", 2)
            .where_end()
            .where("field4", "=", 4)
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ("field3" = %s) OR ( ("field1" = %s) AND ("field2" = '
            '%s) ) AND ("field4" = %s)'
        )
        assert values == [3, 1, 2, 4]

        # nested OR group
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where_or()
            .where("field1", "=", 1)
            .where_or()
            .where("field2", "=", 2)
            .orwhere("field3", "=", 3)
            .where_end()
            .where("field4", "=", 4)
            .where_end()
            .where("field5", "=", 5)
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) OR ( ("field2" = %s) OR ("field3" '
            '= %s) ) AND ("field4" = %s) ) AND ("field5" = %s)'
        )
        assert values == [1, 2, 3, 4, 5]

        # Two OR groups
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where_or()
            .where("field1", "=", 1)
            .where("field2", "=", 2)
            .where_end()
            .where_or()
            .where("field3", "=", 3)
            .orwhere("field4", "=", 4)
            .where_end()
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) ) OR ( ('
            '"field3" = %s) OR ("field4" = %s) )'
        )
        assert values == [1, 2, 3, 4]

    def test_where_and_or(self):
        # test with both AND and OR groups
        qry = (
            Select(PgSqlDialect())
            .from_(SomeRecord)
            .where_and()
            .where("field1", "=", 1)
            .where("field2", "=", 2)
            .where_end()
            .where_or()
            .where("field3", "=", 3)
            .where("field4", "=", 4)
            .where_end()
        )

        sql, values = qry.assemble()
        assert (
            sql
            == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) ) OR ( ('
            '"field3" = %s) AND ("field4" = %s) )'
        )
        assert values == [1, 2, 3, 4]
