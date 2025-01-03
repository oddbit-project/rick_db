from rick_db import fieldmapper

TABLE_NAME = "test_table"


@fieldmapper(tablename="test_table")
class SomeRecord:
    field = "field"


@fieldmapper(tablename="other_table", schema="public")
class SchemaTestTable:
    field = "field"
