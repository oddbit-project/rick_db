import pytest
from rick_db.sql import Select, SqlError, Literal
from .common import TABLE_NAME, SomeRecord, SchemaTestTable


def from_cases():
    return [
        # string name
        [TABLE_NAME, None, None, 'SELECT "test_table".* FROM "test_table"'],
        # string name with schema
        [
            TABLE_NAME,
            None,
            "schema",
            'SELECT "test_table".* FROM "schema"."test_table"',
        ],
        # field alias
        [
            TABLE_NAME,
            {"field": "alias"},
            None,
            'SELECT "field" AS "alias" FROM "test_table"',
        ],
        [
            TABLE_NAME,
            [{"field": "alias"}],
            None,
            'SELECT "field" AS "alias" FROM "test_table"',
        ],
        [
            TABLE_NAME,
            {"field1": "alias1", "field2": None},
            None,
            'SELECT "field1" AS "alias1","field2" FROM "test_table"',
        ],
        [
            TABLE_NAME,
            [{"field1": "alias1"}, {"field2": None}],
            None,
            'SELECT "field1" AS "alias1","field2" FROM "test_table"',
        ],
        # table alias
        [
            {TABLE_NAME: "myalias"},
            None,
            None,
            'SELECT "myalias".* FROM "test_table" AS "myalias"',
        ],
        [
            {TABLE_NAME: "myalias"},
            None,
            "public",
            'SELECT "myalias".* FROM "public"."test_table" AS "myalias"',
        ],
        # class/object
        [SomeRecord, None, None, 'SELECT "test_table".* FROM "test_table"'],
        [
            SchemaTestTable,
            None,
            None,
            'SELECT "other_table".* FROM "public"."other_table"',
        ],
        [
            {SomeRecord: "alias"},
            None,
            None,
            'SELECT "alias".* FROM "test_table" AS "alias"',
        ],
        [
            {SchemaTestTable: "alias"},
            None,
            None,
            'SELECT "alias".* FROM "public"."other_table" AS "alias"',
        ],
        # columns
        [TABLE_NAME, "field", None, 'SELECT "field" FROM "test_table"'],
        [TABLE_NAME, ["field"], "schema", 'SELECT "field" FROM "schema"."test_table"'],
        [
            TABLE_NAME,
            ["field", "field2"],
            "schema",
            'SELECT "field","field2" FROM "schema"."test_table"',
        ],
        [TABLE_NAME, "field", "schema", 'SELECT "field" FROM "schema"."test_table"'],
        [TABLE_NAME, ["field"], "schema", 'SELECT "field" FROM "schema"."test_table"'],
        [
            TABLE_NAME,
            ["field", "field2"],
            "schema",
            'SELECT "field","field2" FROM "schema"."test_table"',
        ],
        [
            {TABLE_NAME: "myalias"},
            "field",
            None,
            'SELECT "myalias"."field" FROM "test_table" AS "myalias"',
        ],
        [SomeRecord, SomeRecord.field, None, 'SELECT "field" FROM "test_table"'],
        [SomeRecord, [SomeRecord.field], None, 'SELECT "field" FROM "test_table"'],
        [
            SomeRecord,
            [SomeRecord.field, "field2"],
            None,
            'SELECT "field","field2" FROM "test_table"',
        ],
        [
            {Literal("select a,b,c from abc where x>7"): "tbl1"},
            ["a", "c"],
            None,
            'SELECT "tbl1"."a","tbl1"."c" FROM (select a,b,c from abc where x>7) AS "tbl1"',
        ],
        [
            {Literal("select id from abc where x>7"): "tbl1"},
            {Literal("COUNT(*)"): "total"},
            None,
            'SELECT COUNT(*) AS "total" FROM (select id from abc where x>7) AS "tbl1"',
        ],
    ]


def from_cases_except():
    return [
        # empty name
        [None, None, None, ""],
        ["", None, "schema", ""],
        [{}, None, "schema", ""],
        # empty alias
        [{TABLE_NAME: None}, None, "schema", ""],
        # multiple names
        [{TABLE_NAME: "myalias", "other_name": "other_alias"}, None, None, ""],
        [["table_a", "table_b"], None, None, ""],
        # bad alias
        [{TABLE_NAME: []}, None, None, ""],
        [{SomeRecord: SomeRecord}, None, None, ""],
    ]


class TestFrom:

    @pytest.mark.parametrize("name, columns, schema, result", from_cases())
    def test_from(self, name, columns, schema, result):
        sql, _ = Select().from_(name, columns, schema).assemble()
        assert sql == result

    @pytest.mark.parametrize("name, columns, schema, result", from_cases_except())
    def test_from_except(self, name, columns, schema, result):
        with pytest.raises(SqlError):
            Select().from_(name, columns, schema).assemble()
