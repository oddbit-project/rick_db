# Class rick_db.sql.**SqlDialect**

Base Dialect Class. Implements schema, table and field quoting specifics to be used primarily within the query builder.

### SqlDialect.**table(table_name, alias=None, schema=None)**

Quotes a table name, with an optional *alias* and *schema*.

Example:
```python
# get dialect from a PgConnection() object
dialect = conn.dialect()

# output: "tbl"
print(dialect.table('tbl', None, None)) 

# output: "schema"."tbl" AS "alias"   
print(dialect.table('tbl', 'alias', 'schema'))
```

### SqlDialect.**field(field, field_alias=None, table=None, schema=None)**

Quotes a field name, with an optional *field_alias*, *table* and *schema*. If field_alias is a list or tuple, a CAST()
is performed instead, using the first item as type. If the list or tuple contains 2 items, the first one is used as type,
and the second one as alias.

Example:
```python
# get dialect from a PgConnection() object
dialect = conn.dialect()

# output: "field"
print(dialect.field('field', None))

# output: "field" AS "alias"
print(dialect.field('field', 'alias')) 

# output: CAST("field" AS text)
print(dialect.field('field', ['text']))

# output: CAST("field" AS text) AS "alias"
print(dialect.field('field', ['text', 'alias']))

# output: CAST(COUNT(*) AS int) AS "total"
print(dialect.field(Literal('COUNT(*)'), ['int', 'total'])) 

# output: "table"."field" AS "alias"
print(dialect.field('field', 'alias', 'table'))

# output: "public"."table"."field" AS "alias"
print(dialect.field('field', 'alias', 'table', 'public')) 

```

