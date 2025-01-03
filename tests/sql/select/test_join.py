import pytest

from rick_db.sql import PgSqlDialect, Select, Literal
from tests.sql.select.common import TABLE_NAME, SomeRecord, SchemaTestTable


def join_noalias_cases():
    return [
        [
            "table2",
            "table2_id",
            TABLE_NAME,
            TABLE_NAME + "_id",
            None,
            None,
            None,
            None,
            'SELECT "test_table".* FROM "test_table" INNER JOIN "table2" ON "test_table"."test_table_id"="table2"."table2_id"',
        ],
        [
            SchemaTestTable,
            SchemaTestTable.field,
            SomeRecord,
            SomeRecord.field,
            None,
            None,
            None,
            None,
            'SELECT "test_table".* FROM "test_table" INNER JOIN "public"."other_table" ON "test_table"."field"="other_table"."field"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            TABLE_NAME,
            TABLE_NAME + "_id",
            None,
            None,
            None,
            None,
            'SELECT "test_table".* FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id"="t"."table2_id"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            TABLE_NAME,
            TABLE_NAME + "_id",
            ">",
            None,
            None,
            None,
            'SELECT "test_table".* FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            TABLE_NAME,
            TABLE_NAME + "_id",
            ">",
            "*",
            None,
            None,
            'SELECT "test_table".*,"t".* FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            TABLE_NAME,
            TABLE_NAME + "_id",
            ">",
            ["t_field_1"],
            None,
            None,
            'SELECT "test_table".*,"t"."t_field_1" FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            TABLE_NAME,
            TABLE_NAME + "_id",
            ">",
            ["t_field_1", "t_field_2"],
            None,
            None,
            'SELECT "test_table".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            TABLE_NAME,
            TABLE_NAME + "_id",
            ">",
            ["t_field_1", "t_field_2"],
            "schema",
            None,
            'SELECT "test_table".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" INNER JOIN "schema"."table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"',
        ],
        # note: since "FROM" clause does not have a schema, the result query is not completely valid
        [
            {"table2": "t"},
            "table2_id",
            TABLE_NAME,
            TABLE_NAME + "_id",
            ">",
            ["t_field_1", "t_field_2"],
            "schema",
            "other_schema",
            'SELECT "test_table".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" INNER JOIN "schema"."table2" AS "t" ON "other_schema"."test_table"."test_table_id">"t"."table2_id"',
        ],
        # join select expression as table
        [
            Select(PgSqlDialect()).from_("table_foo", ["id", "name"]),
            "id",
            TABLE_NAME,
            TABLE_NAME + "_id",
            None,
            None,
            None,
            None,
            'SELECT "test_table".* FROM "test_table" INNER JOIN (SELECT "id","name" FROM "table_foo") AS "t" ON "test_table"."test_table_id"="t"."id"',
        ],
        # Literal for multi-expression join
        [
            "table2",
            Literal("table2.id=test_table.id AND table2.name=test_table.name"),
            None,
            None,
            None,
            None,
            None,
            None,
            'SELECT "test_table".* FROM "test_table" INNER JOIN "table2" ON (table2.id=test_table.id AND table2.name=test_table.name)',
        ],
    ]


def join_alias_cases():
    return [
        [
            "table2",
            "table2_id",
            {TABLE_NAME: "t1"},
            TABLE_NAME + "_id",
            None,
            None,
            None,
            None,
            'SELECT "t1".* FROM "test_table" AS "t1" INNER JOIN "table2" ON "t1"."test_table_id"="table2"."table2_id"',
        ],
        [
            {SchemaTestTable: "myalias"},
            SchemaTestTable.field,
            {SomeRecord: "t1"},
            SomeRecord.field,
            None,
            None,
            None,
            None,
            'SELECT "t1".* FROM "test_table" AS "t1" INNER JOIN "public"."other_table" AS "myalias" ON "t1"."field"="myalias"."field"',
        ],
        [
            {"table2": "t2"},
            "table2_id",
            {TABLE_NAME: "t1"},
            TABLE_NAME + "_id",
            None,
            None,
            None,
            None,
            'SELECT "t1".* FROM "test_table" AS "t1" INNER JOIN "table2" AS "t2" ON "t1"."test_table_id"="t2"."table2_id"',
        ],
        [
            {"table2": "t2"},
            "table2_id",
            {TABLE_NAME: "t1"},
            TABLE_NAME + "_id",
            None,
            None,
            None,
            None,
            'SELECT "t1".* FROM "test_table" AS "t1" INNER JOIN "table2" AS "t2" ON "t1"."test_table_id"="t2"."table2_id"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            {TABLE_NAME: "t1"},
            TABLE_NAME + "_id",
            ">",
            "*",
            None,
            None,
            'SELECT "t1".*,"t".* FROM "test_table" AS "t1" INNER JOIN "table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            {TABLE_NAME: "t1"},
            TABLE_NAME + "_id",
            ">",
            ["t_field_1"],
            None,
            None,
            'SELECT "t1".*,"t"."t_field_1" FROM "test_table" AS "t1" INNER JOIN "table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            {TABLE_NAME: "t1"},
            TABLE_NAME + "_id",
            ">",
            ["t_field_1", "t_field_2"],
            None,
            None,
            'SELECT "t1".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" AS "t1" INNER JOIN "table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"',
        ],
        [
            {"table2": "t"},
            "table2_id",
            {"TABLE_NAME": "t1"},
            TABLE_NAME + "_id",
            ">",
            ["t_field_1", "t_field_2"],
            "schema",
            None,
            'SELECT "t1".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" AS "t1" INNER JOIN "schema"."table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"',
        ],
        # note: since "FROM" clause does not have a schema, the result query is not completely valid
        [
            {"table2": "t"},
            "table2_id",
            {"TABLE_NAME": "t1"},
            TABLE_NAME + "_id",
            ">",
            ["t_field_1", "t_field_2"],
            "schema",
            "other_schema",
            'SELECT "t1".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" AS "t1" INNER JOIN "schema"."table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"',
        ],
    ]


class TestJoin:

    @pytest.mark.parametrize(
        "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
        join_noalias_cases(),
    )
    def test_noalias_join(
        self,
        join_table,
        expr_or_field,
        expr_table,
        expr_field,
        operator,
        cols,
        schema,
        join_schema,
        result,
    ):
        sql, _ = (
            Select()
            .from_(TABLE_NAME, "*")
            .join(
                join_table,
                expr_or_field,
                expr_table,
                expr_field,
                operator,
                cols,
                schema,
                join_schema,
            )
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize(
        "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
        join_alias_cases(),
    )
    def test_alias_join(
        self,
        join_table,
        expr_or_field,
        expr_table,
        expr_field,
        operator,
        cols,
        schema,
        join_schema,
        result,
    ):
        sql, _ = (
            Select()
            .from_({TABLE_NAME: "t1"}, "*")
            .join(
                join_table,
                expr_or_field,
                expr_table,
                expr_field,
                operator,
                cols,
                schema,
                join_schema,
            )
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize(
        "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
        join_noalias_cases(),
    )
    def test_noalias_join_left(
        self,
        join_table,
        expr_or_field,
        expr_table,
        expr_field,
        operator,
        cols,
        schema,
        join_schema,
        result,
    ):
        result = result.replace("INNER", "LEFT")
        sql, _ = (
            Select()
            .from_(TABLE_NAME, "*")
            .join_left(
                join_table,
                expr_or_field,
                expr_table,
                expr_field,
                operator,
                cols,
                schema,
                join_schema,
            )
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize(
        "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
        join_alias_cases(),
    )
    def test_alias_join_left(
        self,
        join_table,
        expr_or_field,
        expr_table,
        expr_field,
        operator,
        cols,
        schema,
        join_schema,
        result,
    ):
        result = result.replace("INNER", "LEFT")
        sql, _ = (
            Select()
            .from_({TABLE_NAME: "t1"}, "*")
            .join_left(
                join_table,
                expr_or_field,
                expr_table,
                expr_field,
                operator,
                cols,
                schema,
                join_schema,
            )
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize(
        "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
        join_noalias_cases(),
    )
    def test_noalias_join_right(
        self,
        join_table,
        expr_or_field,
        expr_table,
        expr_field,
        operator,
        cols,
        schema,
        join_schema,
        result,
    ):
        result = result.replace("INNER", "RIGHT")
        sql, _ = (
            Select()
            .from_(TABLE_NAME, "*")
            .join_right(
                join_table,
                expr_or_field,
                expr_table,
                expr_field,
                operator,
                cols,
                schema,
                join_schema,
            )
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize(
        "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
        join_alias_cases(),
    )
    def test_alias_join_right(
        self,
        join_table,
        expr_or_field,
        expr_table,
        expr_field,
        operator,
        cols,
        schema,
        join_schema,
        result,
    ):
        result = result.replace("INNER", "RIGHT")
        sql, _ = (
            Select()
            .from_({TABLE_NAME: "t1"}, "*")
            .join_right(
                join_table,
                expr_or_field,
                expr_table,
                expr_field,
                operator,
                cols,
                schema,
                join_schema,
            )
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize(
        "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
        join_noalias_cases(),
    )
    def test_noalias_join_full(
        self,
        join_table,
        expr_or_field,
        expr_table,
        expr_field,
        operator,
        cols,
        schema,
        join_schema,
        result,
    ):
        result = result.replace("INNER", "FULL")
        sql, _ = (
            Select()
            .from_(TABLE_NAME, "*")
            .join_full(
                join_table,
                expr_or_field,
                expr_table,
                expr_field,
                operator,
                cols,
                schema,
                join_schema,
            )
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize(
        "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
        join_alias_cases(),
    )
    def test_alias_join_full(
        self,
        join_table,
        expr_or_field,
        expr_table,
        expr_field,
        operator,
        cols,
        schema,
        join_schema,
        result,
    ):
        result = result.replace("INNER", "FULL")
        sql, _ = (
            Select()
            .from_({TABLE_NAME: "t1"}, "*")
            .join_full(
                join_table,
                expr_or_field,
                expr_table,
                expr_field,
                operator,
                cols,
                schema,
                join_schema,
            )
            .assemble()
        )
        assert sql == result
