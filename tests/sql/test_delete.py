import pytest
from rick_db import fieldmapper
from rick_db.sql import Delete, Select, Literal

TABLE_NAME = "test_table"


@fieldmapper(tablename="test_table")
class SomeRecord:
    field = "field"
    other = "other_field"


@fieldmapper(tablename="other_table", schema="public")
class SomeSchemaRecord:
    field = "field"
    other = "other_field"


def delete_cases():
    sample_query = Select().from_("test", ["id"]).where("field", "=", "abcd")
    return [
        ["table1", None, None, 'DELETE FROM "table1"'],
        ["table1", None, "public", 'DELETE FROM "public"."table1"'],
        ["table1", [("id", "=", "5")], None, 'DELETE FROM "table1" WHERE "id" = ?'],
        [
            "table1",
            [("id", "=", "5")],
            "public",
            'DELETE FROM "public"."table1" WHERE "id" = ?',
        ],
        [
            "table1",
            [("id", "in", sample_query)],
            None,
            'DELETE FROM "table1" WHERE "id" in (SELECT "id" FROM "test" WHERE ("field" = ?))',
        ],
        [
            "table1",
            [("id", "is null", None), (Literal("LENGTH(name)"), ">", 3)],
            None,
            'DELETE FROM "table1" WHERE "id" is null AND LENGTH(name) > ?',
        ],
        [
            SomeRecord,
            [("id", "=", "5")],
            None,
            'DELETE FROM "test_table" WHERE "id" = ?',
        ],
        [
            SomeRecord,
            [("id", "=", "5")],
            "public",
            'DELETE FROM "test_table" WHERE "id" = ?',
        ],
        [
            SomeSchemaRecord,
            [("id", "=", "5")],
            None,
            'DELETE FROM "public"."other_table" WHERE "id" = ?',
        ],
        [
            SomeSchemaRecord,
            [("id", "=", "5")],
            "public",
            'DELETE FROM "public"."other_table" WHERE "id" = ?',
        ],
    ]


def delete_cases_or():
    sample_query = Select().from_("test", ["id"]).where("field", "=", "abcd")
    return [
        [
            "table1",
            [("id", "in", sample_query)],
            None,
            'DELETE FROM "table1" WHERE "id" in (SELECT "id" FROM "test" WHERE ("field" = ?))',
        ],
        [
            "table1",
            [("id", "is null", None), (Literal("LENGTH(name)"), ">", 3)],
            None,
            'DELETE FROM "table1" WHERE "id" is null OR LENGTH(name) > ?',
        ],
        [
            SomeRecord,
            [("id", "in", sample_query)],
            None,
            'DELETE FROM "test_table" WHERE "id" in (SELECT "id" FROM "test" WHERE ("field" = ?))',
        ],
        [
            SomeRecord,
            [("id", "is null", None), (Literal("LENGTH(name)"), ">", 3)],
            None,
            'DELETE FROM "test_table" WHERE "id" is null OR LENGTH(name) > ?',
        ],
        [
            SomeSchemaRecord,
            [("id", "is null", None), (Literal("LENGTH(name)"), ">", 3)],
            None,
            'DELETE FROM "public"."other_table" WHERE "id" is null OR LENGTH(name) > ?',
        ],
    ]


def delete_cases_and_or():
    sample_query = Select().from_("test", ["id"]).where("field", "=", "abcd")
    return [
        [
            "table1",
            [("id", "in", sample_query)],
            [("field", ">", 3)],
            None,
            'DELETE FROM "table1" WHERE "id" in (SELECT "id" FROM "test" WHERE ("field" = ?)) OR "field" > ?',
        ],
    ]


class TestDelete:

    @pytest.mark.parametrize("table, where_list, schema, result", delete_cases())
    def test_delete(self, table, where_list, schema, result):
        qry = Delete().from_(table, schema)
        if where_list:
            for item in where_list:
                field, operator, value = item
                qry.where(field, operator, value)

        sql, _ = qry.assemble()
        assert sql == result

    @pytest.mark.parametrize("table, where_list, schema, result", delete_cases_or())
    def test_delete_or(self, table, where_list, schema, result):
        qry = Delete().from_(table, schema)
        for item in where_list:
            field, operator, value = item
            qry.orwhere(field, operator, value)

        sql, _ = qry.assemble()
        assert sql == result

    @pytest.mark.parametrize(
        "table, and_where_list, or_where_list, schema, result", delete_cases_and_or()
    )
    def test_delete_and_or(self, table, and_where_list, or_where_list, schema, result):
        qry = Delete().from_(table, schema)
        for item in and_where_list:
            field, operator, value = item
            qry.where(field, operator, value)
        for item in or_where_list:
            field, operator, value = item
            qry.orwhere(field, operator, value)
        sql, _ = qry.assemble()
        assert sql == result
