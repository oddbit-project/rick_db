import pytest
from rick_db import fieldmapper
from rick_db.sql import Insert

TABLE_NAME = 'test_table'


@fieldmapper(tablename='test_table')
class SomeTable:
    field = 'field'
    other = 'other_field'


@fieldmapper(tablename='other_table', schema='public')
class SchemaTestTable:
    field = 'field'
    other = 'other_field'


insert_cases = [
    ['table1', ['id', ], [32, ], None, None, 'INSERT INTO "table1" ("id") VALUES (?)'],
    ['table1', ['fld1', ' fld2', 'fld3'], [32, 33, 34, ], None, None,
     'INSERT INTO "table1" ("fld1", " fld2", "fld3") VALUES (?, ?, ?)'],
    ['table1', None, {'field1': 'value1', 'field2': 'value2'}, None, None,
     'INSERT INTO "table1" ("field1", "field2") VALUES (?, ?)'],
    ['table1', ['id', ], [32, ], ['id'], None, 'INSERT INTO "table1" ("id") VALUES (?) RETURNING "id"'],
    ['table1', ['f1', 'f2', ], [32, 33, ], ['f1'], None,
     'INSERT INTO "table1" ("f1", "f2") VALUES (?, ?) RETURNING "f1"'],
    ['table1', ['f1', 'f2', ], [32, 33, ], ['f1', 'f2'], None,
     'INSERT INTO "table1" ("f1", "f2") VALUES (?, ?) RETURNING "f1", "f2"'],
    ['table1', ['id', ], [32, ], None, 'public', 'INSERT INTO "public"."table1" ("id") VALUES (?)'],
    [SomeTable, [], SomeTable(field="data"), None, None, 'INSERT INTO "test_table" ("field") VALUES (?)'],
    [SomeTable(field="data"), None, None, None, None, 'INSERT INTO "test_table" ("field") VALUES (?)'],
    [SomeTable(field="data", other="data"), None, None, None, None,
     'INSERT INTO "test_table" ("field", "other_field") VALUES (?, ?)'],
    [SchemaTestTable(field="data", other="data"), None, None, None, None,
     'INSERT INTO "public"."other_table" ("field", "other_field") VALUES (?, ?)'],
]


@pytest.mark.parametrize("table, fields, values, returning, schema, result", insert_cases)
def test_insert(table, fields, values, returning, schema, result):
    qry = Insert().into(table, schema)
    if fields is not None:
        qry.fields(fields)
    if values is not None:
        qry.values(values)
    if returning is not None:
        qry.returning(returning)
    sql, insert_values = qry.assemble()
    assert sql == result
    if values is not None:
        if isinstance(values, SomeTable) or isinstance(values, SchemaTestTable):
            values = values.asrecord()
        assert len(insert_values) == len(values)
