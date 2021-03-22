import pytest
from rick_db import fieldmapper
from rick_db.sql import Select, SqlError, Literal, PgSqlDialect

TABLE_NAME = 'test_table'


@fieldmapper(tablename='test_table')
class SomeTable:
    field = 'field'


@fieldmapper(tablename='other_table', schema='public')
class SchemaTestTable:
    field = 'field'


# Select:from_() ------------------------------------------------------------------------------------------------------
from_cases = [
    # string name
    [TABLE_NAME, None, None, 'SELECT "test_table".* FROM "test_table"'],
    # string name with schema
    [TABLE_NAME, None, 'schema', 'SELECT "test_table".* FROM "schema"."test_table"'],

    # field alias
    [TABLE_NAME, {'field': 'alias'}, None, 'SELECT "field" AS "alias" FROM "test_table"'],
    [TABLE_NAME, [{'field': 'alias'}], None, 'SELECT "field" AS "alias" FROM "test_table"'],
    [TABLE_NAME, {"field1": "alias1", "field2": None}, None, 'SELECT "field1" AS "alias1","field2" FROM "test_table"'],
    [TABLE_NAME, [{"field1": "alias1"}, {"field2": None}], None,
     'SELECT "field1" AS "alias1","field2" FROM "test_table"'],

    # table alias
    [{TABLE_NAME: "myalias"}, None, None, 'SELECT "myalias".* FROM "test_table" AS "myalias"'],
    [{TABLE_NAME: "myalias"}, None, 'public', 'SELECT "myalias".* FROM "public"."test_table" AS "myalias"'],
    # class/object
    [SomeTable, None, None, 'SELECT "test_table".* FROM "test_table"'],
    [SchemaTestTable, None, None, 'SELECT "other_table".* FROM "public"."other_table"'],
    [{SomeTable: "alias"}, None, None, 'SELECT "alias".* FROM "test_table" AS "alias"'],
    [{SchemaTestTable: "alias"}, None, None, 'SELECT "alias".* FROM "public"."other_table" AS "alias"'],
    # columns
    [TABLE_NAME, "field", None, 'SELECT "field" FROM "test_table"'],
    [TABLE_NAME, ["field"], 'schema', 'SELECT "field" FROM "schema"."test_table"'],
    [TABLE_NAME, ["field", "field2"], 'schema', 'SELECT "field","field2" FROM "schema"."test_table"'],
    [TABLE_NAME, "field", 'schema', 'SELECT "field" FROM "schema"."test_table"'],
    [TABLE_NAME, ["field"], 'schema', 'SELECT "field" FROM "schema"."test_table"'],
    [TABLE_NAME, ["field", "field2"], 'schema', 'SELECT "field","field2" FROM "schema"."test_table"'],
    [{TABLE_NAME: "myalias"}, "field", None, 'SELECT "myalias"."field" FROM "test_table" AS "myalias"'],
    [SomeTable, SomeTable.field, None, 'SELECT "field" FROM "test_table"'],
    [SomeTable, [SomeTable.field], None, 'SELECT "field" FROM "test_table"'],
    [SomeTable, [SomeTable.field, "field2"], None, 'SELECT "field","field2" FROM "test_table"'],
    [{Literal('select a,b,c from abc where x>7'): 'tbl1'}, ['a', 'c'], None,
     'SELECT "tbl1"."a","tbl1"."c" FROM (select a,b,c from abc where x>7) AS "tbl1"'],
    [{Literal('select id from abc where x>7'): 'tbl1'}, {Literal('COUNT(*)'): 'total'}, None,
     'SELECT COUNT(*) AS "total" FROM (select id from abc where x>7) AS "tbl1"']
]

from_cases_except = [
    # empty name
    [None, None, None, ''],
    ["", None, 'schema', ''],
    [{}, None, 'schema', ''],
    # empty alias
    [{TABLE_NAME: None}, None, 'schema', ''],
    # multiple names
    [{TABLE_NAME: "myalias", "other_name": "other_alias"}, None, None, ''],
    [["table_a", "table_b"], None, None, ''],
    # bad alias
    [{TABLE_NAME: []}, None, None, ''],
    [{SomeTable: SomeTable}, None, None, ''],
]


@pytest.mark.parametrize("name, columns, schema, result", from_cases)
def test_from(name, columns, schema, result):
    sql, _ = Select().from_(name, columns, schema).assemble()
    assert sql == result


@pytest.mark.parametrize("name, columns, schema, result", from_cases_except)
def test_from_except(name, columns, schema, result):
    with pytest.raises(SqlError):
        Select().from_(name, columns, schema).assemble()


# Select:join() ------------------------------------------------------------------------------------------------------
join_noalias_cases = [
    ["table2", "table2_id", TABLE_NAME, TABLE_NAME + "_id", None, None, None, None,
     'SELECT "test_table".* FROM "test_table" INNER JOIN "table2" ON "test_table"."test_table_id"="table2"."table2_id"'],
    [SchemaTestTable, SchemaTestTable.field, SomeTable, SomeTable.field, None, None, None, None,
     'SELECT "test_table".* FROM "test_table" INNER JOIN "public"."other_table" ON "test_table"."field"="other_table"."field"'],
    [{"table2": "t"}, "table2_id", TABLE_NAME, TABLE_NAME + "_id", None, None, None, None,
     'SELECT "test_table".* FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id"="t"."table2_id"'],
    [{"table2": "t"}, "table2_id", TABLE_NAME, TABLE_NAME + "_id", '>', None, None, None,
     'SELECT "test_table".* FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"'],
    [{"table2": "t"}, "table2_id", TABLE_NAME, TABLE_NAME + "_id", '>', '*', None, None,
     'SELECT "test_table".*,"t".* FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"'],
    [{"table2": "t"}, "table2_id", TABLE_NAME, TABLE_NAME + "_id", '>', ['t_field_1'], None, None,
     'SELECT "test_table".*,"t"."t_field_1" FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"'],
    [{"table2": "t"}, "table2_id", TABLE_NAME, TABLE_NAME + "_id", '>', ['t_field_1', 't_field_2'], None, None,
     'SELECT "test_table".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" INNER JOIN "table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"'],
    [{"table2": "t"}, "table2_id", TABLE_NAME, TABLE_NAME + "_id", '>', ['t_field_1', 't_field_2'], 'schema', None,
     'SELECT "test_table".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" INNER JOIN "schema"."table2" AS "t" ON "test_table"."test_table_id">"t"."table2_id"'],
    # note: since "FROM" clause does not have a schema, the result query is not completely valid
    [{"table2": "t"}, "table2_id", TABLE_NAME, TABLE_NAME + "_id", '>', ['t_field_1', 't_field_2'], 'schema',
     'other_schema',
     'SELECT "test_table".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" INNER JOIN "schema"."table2" AS "t" ON "other_schema"."test_table"."test_table_id">"t"."table2_id"'],
]

join_alias_cases = [
    ["table2", "table2_id", {TABLE_NAME: "t1"}, TABLE_NAME + "_id", None, None, None, None,
     'SELECT "t1".* FROM "test_table" AS "t1" INNER JOIN "table2" ON "t1"."test_table_id"="table2"."table2_id"'],
    [{SchemaTestTable: "myalias"}, SchemaTestTable.field, {SomeTable: "t1"}, SomeTable.field, None, None, None, None,
     'SELECT "t1".* FROM "test_table" AS "t1" INNER JOIN "public"."other_table" AS "myalias" ON "t1"."field"="myalias"."field"'],
    [{"table2": "t2"}, "table2_id", {TABLE_NAME: "t1"}, TABLE_NAME + "_id", None, None, None, None,
     'SELECT "t1".* FROM "test_table" AS "t1" INNER JOIN "table2" AS "t2" ON "t1"."test_table_id"="t2"."table2_id"'],
    [{"table2": "t2"}, "table2_id", {TABLE_NAME: "t1"}, TABLE_NAME + "_id", None, None, None, None,
     'SELECT "t1".* FROM "test_table" AS "t1" INNER JOIN "table2" AS "t2" ON "t1"."test_table_id"="t2"."table2_id"'],
    [{"table2": "t"}, "table2_id", {TABLE_NAME: "t1"}, TABLE_NAME + "_id", '>', '*', None, None,
     'SELECT "t1".*,"t".* FROM "test_table" AS "t1" INNER JOIN "table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"'],
    [{"table2": "t"}, "table2_id", {TABLE_NAME: "t1"}, TABLE_NAME + "_id", '>', ['t_field_1'], None, None,
     'SELECT "t1".*,"t"."t_field_1" FROM "test_table" AS "t1" INNER JOIN "table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"'],
    [{"table2": "t"}, "table2_id", {TABLE_NAME: "t1"}, TABLE_NAME + "_id", '>', ['t_field_1', 't_field_2'], None, None,
     'SELECT "t1".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" AS "t1" INNER JOIN "table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"'],
    [{"table2": "t"}, "table2_id", {"TABLE_NAME": "t1"}, TABLE_NAME + "_id", '>', ['t_field_1', 't_field_2'], 'schema',
     None,
     'SELECT "t1".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" AS "t1" INNER JOIN "schema"."table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"'],
    # note: since "FROM" clause does not have a schema, the result query is not completely valid
    [{"table2": "t"}, "table2_id", {"TABLE_NAME": "t1"}, TABLE_NAME + "_id", '>', ['t_field_1', 't_field_2'], 'schema',
     'other_schema',
     'SELECT "t1".*,"t"."t_field_1","t"."t_field_2" FROM "test_table" AS "t1" INNER JOIN "schema"."table2" AS "t" ON "t1"."test_table_id">"t"."table2_id"'],
]


@pytest.mark.parametrize(
    "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
    join_noalias_cases)
def test_noalias_join(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result):
    sql, _ = Select().from_(TABLE_NAME, "*") \
        .join(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema) \
        .assemble()
    assert sql == result


@pytest.mark.parametrize(
    "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result", join_alias_cases)
def test_alias_join(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result):
    sql, _ = Select().from_({TABLE_NAME: "t1"}, "*") \
        .join(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema) \
        .assemble()
    assert sql == result


@pytest.mark.parametrize(
    "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
    join_noalias_cases)
def test_noalias_join_left(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema,
                           result):
    result = result.replace('INNER', 'LEFT')
    sql, _ = Select().from_(TABLE_NAME, "*") \
        .join_left(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema) \
        .assemble()
    assert sql == result


@pytest.mark.parametrize(
    "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result", join_alias_cases)
def test_alias_join_left(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema,
                         result):
    result = result.replace('INNER', 'LEFT')
    sql, _ = Select().from_({TABLE_NAME: "t1"}, "*") \
        .join_left(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema) \
        .assemble()
    assert sql == result


@pytest.mark.parametrize(
    "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
    join_noalias_cases)
def test_noalias_join_right(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema,
                            result):
    result = result.replace('INNER', 'RIGHT')
    sql, _ = Select().from_(TABLE_NAME, "*") \
        .join_right(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema) \
        .assemble()
    assert sql == result


@pytest.mark.parametrize(
    "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result", join_alias_cases)
def test_alias_join_right(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema,
                          result):
    result = result.replace('INNER', 'RIGHT')
    sql, _ = Select().from_({TABLE_NAME: "t1"}, "*") \
        .join_right(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema) \
        .assemble()
    assert sql == result


@pytest.mark.parametrize(
    "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result",
    join_noalias_cases)
def test_noalias_join_full(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema,
                           result):
    result = result.replace('INNER', 'FULL')
    sql, _ = Select().from_(TABLE_NAME, "*") \
        .join_full(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema) \
        .assemble()
    assert sql == result


@pytest.mark.parametrize(
    "join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema, result", join_alias_cases)
def test_alias_join_full(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema,
                         result):
    result = result.replace('INNER', 'FULL')
    sql, _ = Select().from_({TABLE_NAME: "t1"}, "*") \
        .join_full(join_table, expr_or_field, expr_table, expr_field, operator, cols, schema, join_schema) \
        .assemble()
    assert sql == result


# Select:join_cross() --------------------------------------------------------------------------------------------------

join_cross = [
    ["table2", None, None, 'SELECT "test_table".* FROM "test_table" CROSS JOIN "table2"'],
    [{"table2": "myalias"}, None, None, 'SELECT "test_table".* FROM "test_table" CROSS JOIN "table2" AS "myalias"'],
    ["table2", 'field1', None, 'SELECT "test_table".*,"table2"."field1" FROM "test_table" CROSS JOIN "table2"'],
    ["table2", ['field1', 'field2'], 'schema',
     'SELECT "test_table".*,"table2"."field1","table2"."field2" FROM "test_table" CROSS JOIN "schema"."table2"'],
    [{"table2": "alias"}, ['field1', 'field2'], 'schema',
     'SELECT "test_table".*,"alias"."field1","alias"."field2" FROM "test_table" CROSS JOIN "schema"."table2" AS "alias"'],
    [{"table2": "alias"}, [{'field1': 'field_alias'}, 'field2'], 'schema',
     'SELECT "test_table".*,"alias"."field1" AS "field_alias","alias"."field2" FROM "test_table" CROSS JOIN "schema"."table2" AS "alias"']
]


@pytest.mark.parametrize("table, cols, schema, result", join_cross)
def test_join_cross(table, cols, schema, result):
    sql, _ = Select().from_(TABLE_NAME, "*").join_cross(table, cols, schema).assemble()
    assert sql == result


# Select:join_natural() --------------------------------------------------------------------------------------------------

join_natural = [
    ["table2", None, None, 'SELECT "test_table".* FROM "test_table" NATURAL JOIN "table2"'],
    [{"table2": "myalias"}, None, None, 'SELECT "test_table".* FROM "test_table" NATURAL JOIN "table2" AS "myalias"'],
    ["table2", 'field1', None, 'SELECT "test_table".*,"table2"."field1" FROM "test_table" NATURAL JOIN "table2"'],
    ["table2", ['field1', 'field2'], 'schema',
     'SELECT "test_table".*,"table2"."field1","table2"."field2" FROM "test_table" NATURAL JOIN "schema"."table2"'],
    [{"table2": "alias"}, ['field1', 'field2'], 'schema',
     'SELECT "test_table".*,"alias"."field1","alias"."field2" FROM "test_table" NATURAL JOIN "schema"."table2" AS "alias"']
]


@pytest.mark.parametrize("table, cols, schema, result", join_natural)
def test_join_natural(table, cols, schema, result):
    sql, _ = Select().from_(TABLE_NAME, "*").join_natural(table, cols, schema).assemble()
    assert sql == result


# Select:where() -------------------------------------------------------------------------------------------------------

sample_qry = Select().from_("test", ['id']).where(Literal('SUM(total)'), '>', 0)

where_simple = [
    # field names
    ["field1", "=", 32, 'SELECT "test_table".* FROM "test_table" WHERE ("field1" = %s)'],
    ["field1", ">", 32, 'SELECT "test_table".* FROM "test_table" WHERE ("field1" > %s)'],
    [{"test_table": "field1"}, "=", 32, 'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field1" = %s)'],
    [{SomeTable: SomeTable.field}, "=", 32,
     'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field" = %s)'],
    ["field1", 'in', '(1,2,3,4,5,6)', 'SELECT "test_table".* FROM "test_table" WHERE ("field1" in %s)'],
    ["field1", 'in (1,2,3,4,5,6)', None, 'SELECT "test_table".* FROM "test_table" WHERE ("field1" in (1,2,3,4,5,6))'],
    # expressions
    [Literal("MAX(field1)"), '>', 32, 'SELECT "test_table".* FROM "test_table" WHERE (MAX(field1) > %s)'],
    [Literal("TOP(field1)"), 'is null', None, 'SELECT "test_table".* FROM "test_table" WHERE (TOP(field1) is null)'],
    [Literal(SomeTable.field + " is null or field > 0"), None, None,
     'SELECT "test_table".* FROM "test_table" WHERE (field is null or field > 0)'],
    [SomeTable.field, 'in', sample_qry,
     'SELECT "test_table".* FROM "test_table" WHERE ("field" in (SELECT "id" FROM "test" WHERE (SUM(total) > ?)))'],
]

where_and = [
    ["field1", ">", 12, "field1", "<", 16,
     'SELECT "test_table".* FROM "test_table" WHERE ("field1" > %s) AND ("field1" < %s)'],
    [{"test_table": "field1"}, ">", 12, {"test_table": "field1"}, "<", 16,
     'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field1" > %s) AND ("test_table"."field1" < %s)'],
    [{SomeTable: SomeTable.field}, ">", 12, {SomeTable: SomeTable.field}, "<", 16,
     'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field" > %s) AND ("test_table"."field" < %s)'],

]

where_or = [
    ["field1", ">", 12, "field1", "<", 16,
     'SELECT "test_table".* FROM "test_table" WHERE ("field1" > %s) OR ("field1" < %s)'],
    [{"test_table": "field1"}, ">", 12, {"test_table": "field1"}, "<", 16,
     'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field1" > %s) OR ("test_table"."field1" < %s)'],
    [{SomeTable: SomeTable.field}, ">", 12, {SomeTable: SomeTable.field}, "<", 16,
     'SELECT "test_table".* FROM "test_table" WHERE ("test_table"."field" > %s) OR ("test_table"."field" < %s)'],
]


@pytest.mark.parametrize("field, operator, value, result", where_simple)
def test_where_simple(field, operator, value, result):
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "*").where(field, operator, value).assemble()
    assert sql == result


@pytest.mark.parametrize("field, operator, value,field1, operator1, value1, result", where_and)
def test_where(field, operator, value, field1, operator1, value1, result):
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "*") \
        .where(field, operator, value) \
        .where(field1, operator1, value1) \
        .assemble()
    assert sql == result


@pytest.mark.parametrize("field, operator, value,field1, operator1, value1, result", where_or)
def test_orwhere(field, operator, value, field1, operator1, value1, result):
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "*") \
        .where(field, operator, value) \
        .orwhere(field1, operator1, value1) \
        .assemble()
    assert sql == result


# Select:limit() -------------------------------------------------------------------------------------------------------

limit = [
    ['10', None, 'SELECT "test_table".* FROM "test_table" LIMIT 10'],
    [10, 15, 'SELECT "test_table".* FROM "test_table" LIMIT 10 OFFSET 15'],
]


@pytest.mark.parametrize("limit, offset, result", limit)
def test_limit(limit, offset, result):
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "*").limit(limit, offset).assemble()
    assert sql == result


# Select:order() -------------------------------------------------------------------------------------------------------

order = [
    ["field1", None, 'SELECT "test_table".* FROM "test_table" ORDER BY "field1"'],
    ["field1", 'desc', 'SELECT "test_table".* FROM "test_table" ORDER BY "field1" desc'],
    [Literal('SUM(field1)'), 'desc', 'SELECT "test_table".* FROM "test_table" ORDER BY SUM(field1) desc']
]


@pytest.mark.parametrize("field, order, result", order)
def test_order(field, order, result):
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "*").order(field, order).assemble()
    assert sql == result


# Select:page() -------------------------------------------------------------------------------------------------------

page_limit = [
    [1, 10, 'SELECT "test_table".* FROM "test_table" LIMIT 10 OFFSET 0'],
    [2, 10, 'SELECT "test_table".* FROM "test_table" LIMIT 10 OFFSET 10'],
    [10, 25, 'SELECT "test_table".* FROM "test_table" LIMIT 25 OFFSET 225'],
]


@pytest.mark.parametrize("page, page_rows, result", page_limit)
def test_page(page, page_rows, result):
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "*").page(page, page_rows).assemble()
    assert sql == result


# Select:distinct() ----------------------------------------------------------------------------------------------------

def test_distinct():
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "field").distinct().assemble()
    assert sql == 'SELECT DISTINCT "field" FROM "test_table"'


# Select:for_update() ----------------------------------------------------------------------------------------------------

def test_for_update():
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "field").for_update().assemble()
    assert sql == 'SELECT "field" FROM "test_table" FOR UPDATE'
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "field").for_update(False).assemble()
    assert sql == 'SELECT "field" FROM "test_table"'


# Select:expr() ----------------------------------------------------------------------------------------------------

expr = [
    [None, 'SELECT None'],
    [1, 'SELECT 1'],
    [[1, 2, 3], 'SELECT 1,2,3'],
    ['now()', 'SELECT now()'],
    [{'now()': None}, 'SELECT now()'],
    [{1: None, 2: 'second', 3: 'third'}, 'SELECT 1,2 AS "second",3 AS "third"'],
    [{'now()': 'datetime'}, 'SELECT now() AS "datetime"'],
]


@pytest.mark.parametrize("cols, result", expr)
def test_expr(cols, result):
    sql, _ = Select(PgSqlDialect()).expr(cols).assemble()
    assert sql == result


# Select:group() ----------------------------------------------------------------------------------------------------

group_by = [
    [[], 'SELECT "test_table".* FROM "test_table"'],
    ['field', 'SELECT "test_table".* FROM "test_table" GROUP BY "field"'],
    [['field', 'other'], 'SELECT "test_table".* FROM "test_table" GROUP BY "field", "other"'],
    [Literal('SUM(field)'), 'SELECT "test_table".* FROM "test_table" GROUP BY SUM(field)'],
    [[Literal('SUM(field)')], 'SELECT "test_table".* FROM "test_table" GROUP BY SUM(field)'],
    [[Literal('SUM(field)'), 'other'], 'SELECT "test_table".* FROM "test_table" GROUP BY SUM(field), "other"'],
]


@pytest.mark.parametrize("cols, result", group_by)
def test_group(cols, result):
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "*").group(cols).assemble()
    assert sql == result


# Select:having() ----------------------------------------------------------------------------------------------------

having = [
    # literals
    [Literal('COUNT(field) > 5'), None, None, None,
     'SELECT "test_table".* FROM "test_table" HAVING (COUNT(field) > 5)'],
    [Literal('COUNT(field)'), '>', 5, None, 'SELECT "test_table".* FROM "test_table" HAVING (COUNT(field) > %s)'],
    [Literal('COUNT(field)'), '>', 5, 'public', 'SELECT "test_table".* FROM "test_table" HAVING (COUNT(field) > %s)'],
    # strings
    ['field1', None, None, None, 'SELECT "test_table".* FROM "test_table" HAVING ("field1")'],
    ['field1', 'IS', 'NULL', None, 'SELECT "test_table".* FROM "test_table" HAVING ("field1" IS %s)'],
    ['field1 IS NULL', None, None, None, 'SELECT "test_table".* FROM "test_table" HAVING ("field1 IS NULL")'],
    # dict format {TableName:FieldName}
    [{SomeTable: SomeTable.field}, '>', 5, None,
     'SELECT "test_table".* FROM "test_table" HAVING ("test_table"."field" > %s)'],
    [{SchemaTestTable: SchemaTestTable.field}, '>', 5, None,
     'SELECT "test_table".* FROM "test_table" HAVING ("public"."other_table"."field" > %s)']
]


@pytest.mark.parametrize("field, operator, value, schema, result", having)
def test_having(field, operator, value, schema, result):
    sql, _ = Select(PgSqlDialect()).from_(TABLE_NAME, "*").having(field, operator, value, schema).assemble()
    assert sql == result


# Select:union() ----------------------------------------------------------------------------------------------------

def test_union():
    qry_union = Select(PgSqlDialect()).union([
        Select(PgSqlDialect()).from_(SomeTable),
        Select(PgSqlDialect()).from_(SchemaTestTable),
    ])
    sql, _ = qry_union.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" UNION SELECT "other_table".* FROM "public"."other_table"'


# Select:where_and() -----------------------------------------------------------------------------------------------

def test_where_and():
    # test with AND group in the beginning
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where_and() \
        .where('field1', '=', 1) \
        .where('field2', '=', 2) \
        .where_end()

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) )'
    assert values == [1, 2]

    # AND group and parameter
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where('field3', '=', 3) \
        .where_and() \
        .where('field1', '=', 1) \
        .where('field2', '=', 2) \
        .where_end()

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ("field3" = %s) AND ( ("field1" = %s) AND ("field2" ' \
                  '= %s) )'
    assert values == [3, 1, 2]

    # AND group and two parameters
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where('field3', '=', 3) \
        .where_and() \
        .where('field1', '=', 1) \
        .where('field2', '=', 2) \
        .where_end() \
        .where('field4', '=', 4)

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ("field3" = %s) AND ( ("field1" = %s) AND ("field2" ' \
                  '= %s) ) AND ("field4" = %s)'
    assert values == [3, 1, 2, 4]

    # nested AND group
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where_and() \
        .where('field1', '=', 1) \
        .where_and() \
        .where('field2', '=', 2) \
        .orwhere('field3', '=', 3) \
        .where_end() \
        .where('field4', '=', 4) \
        .where_end() \
        .where('field5', '=', 5)

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ( ("field2" = %s) OR ("field3" ' \
                  '= %s) ) AND ("field4" = %s) ) AND ("field5" = %s)'
    assert values == [1, 2, 3, 4, 5]

    # Two AND groups
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where_and() \
        .where('field1', '=', 1) \
        .where('field2', '=', 2) \
        .where_end() \
        .where_and() \
        .where('field3', '=', 3) \
        .orwhere('field4', '=', 4) \
        .where_end()

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) ) AND ( (' \
                  '"field3" = %s) OR ("field4" = %s) )'
    assert values == [1, 2, 3, 4]


def test_where_or():
    # test with OR group in the beginning
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where_or() \
        .where('field1', '=', 1) \
        .where('field2', '=', 2) \
        .where_end()

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) )'
    assert values == [1, 2]

    # OR group and parameter
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where('field3', '=', 3) \
        .where_or() \
        .where('field1', '=', 1) \
        .where('field2', '=', 2) \
        .where_end()

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ("field3" = %s) OR ( ("field1" = %s) AND ("field2" = ' \
                  '%s) )'
    assert values == [3, 1, 2]

    # OR group and two parameters
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where('field3', '=', 3) \
        .where_or() \
        .where('field1', '=', 1) \
        .where('field2', '=', 2) \
        .where_end() \
        .where('field4', '=', 4)

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ("field3" = %s) OR ( ("field1" = %s) AND ("field2" = ' \
                  '%s) ) AND ("field4" = %s)'
    assert values == [3, 1, 2, 4]

    # nested OR group
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where_or() \
        .where('field1', '=', 1) \
        .where_or() \
        .where('field2', '=', 2) \
        .orwhere('field3', '=', 3) \
        .where_end() \
        .where('field4', '=', 4) \
        .where_end() \
        .where('field5', '=', 5)

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) OR ( ("field2" = %s) OR ("field3" ' \
                  '= %s) ) AND ("field4" = %s) ) AND ("field5" = %s)'
    assert values == [1, 2, 3, 4, 5]

    # Two OR groups
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where_or() \
        .where('field1', '=', 1) \
        .where('field2', '=', 2) \
        .where_end() \
        .where_or() \
        .where('field3', '=', 3) \
        .orwhere('field4', '=', 4) \
        .where_end()

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) ) OR ( (' \
                  '"field3" = %s) OR ("field4" = %s) )'
    assert values == [1, 2, 3, 4]


def test_where_and_or():
    # test with both AND and OR groups
    qry = Select(PgSqlDialect()).from_(SomeTable) \
        .where_and() \
        .where('field1', '=', 1) \
        .where('field2', '=', 2) \
        .where_end() \
        .where_or() \
        .where('field3', '=', 3) \
        .where('field4', '=', 4) \
        .where_end()

    sql, values = qry.assemble()
    assert sql == 'SELECT "test_table".* FROM "test_table" WHERE ( ("field1" = %s) AND ("field2" = %s) ) OR ( (' \
                  '"field3" = %s) AND ("field4" = %s) )'
    assert values == [1, 2, 3, 4]
