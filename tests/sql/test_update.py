import pytest
from rick_db import fieldmapper
from rick_db.sql import Update, Select, Literal


@fieldmapper(tablename='test_table')
class SomeTable:
    field = 'field'
    other = 'other_field'


@fieldmapper(tablename='other_table', schema='public')
class SchemaTestTable:
    field = 'field'
    other = 'other_field'


sample_query = Select().from_('test', ['id']).where('field', '=', 'abcd')
sample_record = SomeTable(field='value', other='other_value')

update_cases = [
    ['table1', {'field1': 'value1'}, None, None, 'UPDATE "table1" SET "field1"=?'],
    ['table1', {'f1': 'v1', 'f2': 2}, None, 'public', 'UPDATE "public"."table1" SET "f1"=?, "f2"=?'],
    ['table1', {'field1': 'value1'}, [('id', '=', '5')], None, 'UPDATE "table1" SET "field1"=? WHERE "id" = ?'],
    ['table1', {'f1': 'v1', 'f2': 2}, [('id', '=', '5')], 'public',
     'UPDATE "public"."table1" SET "f1"=?, "f2"=? WHERE "id" = ?'],
    ['table1', {'f1': 'v1', 'f2': 2}, [('id', 'in', sample_query)], None,
     'UPDATE "table1" SET "f1"=?, "f2"=? WHERE "id" in (SELECT "id" FROM "test" WHERE ("field" = ?))'],
    ['table1', {'field1': 'value1'}, [('id', 'is null', None), (Literal('LENGTH(name)'), '>', 3)], None,
     'UPDATE "table1" SET "field1"=? WHERE "id" is null AND LENGTH(name) > ?'],
    [SomeTable, sample_record, [('id', '=', '5')], None,
     'UPDATE "test_table" SET "field"=?, "other_field"=? WHERE "id" = ?'],
    [SomeTable, {SomeTable.field: 'value1'}, [('id', '=', '5')], None,
     'UPDATE "test_table" SET "field"=? WHERE "id" = ?'],
    [SomeTable, {SomeTable.field: 'value1'}, [('id', '=', '5')], 'public',
     'UPDATE "test_table" SET "field"=? WHERE "id" = ?'],
    [SchemaTestTable, {SchemaTestTable.field: 'value1'}, [('id', '=', '5')], None,
     'UPDATE "public"."other_table" SET "field"=? WHERE "id" = ?'],
    [SchemaTestTable, {SchemaTestTable.field: 'value1'}, [('id', '=', '5')], 'public',
     'UPDATE "public"."other_table" SET "field"=? WHERE "id" = ?'],

]
update_cases_or = [
    ['table1', {'field1': 'value1'}, [('id', 'in', sample_query)], None,
     'UPDATE "table1" SET "field1"=? WHERE "id" in (SELECT "id" FROM "test" WHERE ("field" = ?))'],
    ['table1', {'f1': 'v1', 'f2': 2}, [('id', 'is null', None), (Literal('LENGTH(name)'), '>', 3)], None,
     'UPDATE "table1" SET "f1"=?, "f2"=? WHERE "id" is null OR LENGTH(name) > ?'],
    [SomeTable, sample_record, [('id', 'in', sample_query)], None,
     'UPDATE "test_table" SET "field"=?, "other_field"=? WHERE "id" in (SELECT "id" FROM "test" WHERE ("field" = ?))'],
    [SomeTable, {SomeTable.field: 'value1', SomeTable.other: 'value2'},
     [('id', 'is null', None), (Literal('LENGTH(name)'), '>', 3)], None,
     'UPDATE "test_table" SET "field"=?, "other_field"=? WHERE "id" is null OR LENGTH(name) > ?'],
    [SchemaTestTable, {'field': 'value1'}, [('id', 'is null', None), (Literal('LENGTH(name)'), '>', 3)], None,
     'UPDATE "public"."other_table" SET "field"=? WHERE "id" is null OR LENGTH(name) > ?'],
]

update_cases_and_or = [
    ['table1', sample_record, [('id', 'in', sample_query)], [('field', '>', 3)], None,
     'UPDATE "table1" SET "field"=?, "other_field"=? WHERE "id" in (SELECT "id" FROM "test" WHERE ("field" = ?)) OR "field" > ?'],

]


@pytest.mark.parametrize("table, fields, where_list, schema, result", update_cases)
def test_update(table, fields, where_list, schema, result):
    qry = Update().table(table, schema)
    if fields:
        qry.values(fields)
    if where_list:
        for item in where_list:
            field, operator, value = item
            qry.where(field, operator, value)

    sql, _ = qry.assemble()
    assert sql == result


@pytest.mark.parametrize("table, fields, where_list, schema, result", update_cases_or)
def test_update_or(table, fields, where_list, schema, result):
    qry = Update().table(table, schema)
    if fields:
        qry.values(fields)
    if where_list:
        for item in where_list:
            field, operator, value = item
            qry.orwhere(field, operator, value)

    sql, _ = qry.assemble()
    assert sql == result


@pytest.mark.parametrize("table, fields, and_where_list, or_where_list, schema, result", update_cases_and_or)
def test_update_and_or(table, fields, and_where_list, or_where_list, schema, result):
    qry = Update().table(table, schema).values(fields)
    for item in and_where_list:
        field, operator, value = item
        qry.where(field, operator, value)
    for item in or_where_list:
        field, operator, value = item
        qry.orwhere(field, operator, value)
    sql, _ = qry.assemble()
    assert sql == result
