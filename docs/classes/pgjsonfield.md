# Class rick_db.sql.**PgJsonField**

PostgreSQL-specific JSON field implementation that extends [JsonField](jsonfield.md) with additional operations
for JSONB columns, including object extraction, jsonpath queries, and type casting.

See also: [JSON Operations](../json_operations.md) for usage examples.

### PgJsonField.**\_\_init\_\_(field_name, dialect=None, is_jsonb=True)**

Create a PgJsonField for the given *field_name*. An optional *dialect* enables dialect-specific SQL generation.
*is_jsonb* controls whether the field is treated as JSONB (default) or JSON.

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()

# JSONB field (default)
jf = PgJsonField('data', pg)

# JSON field
jf = PgJsonField('data', pg, is_jsonb=False)
```

### PgJsonField.**extract(path, alias=None)**

*Inherited from [JsonField](jsonfield.md).* Extract a value as text using the `->>` operator.

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

expr = jf.extract('name')
# output: "data"->>'name'
print(expr)

expr = jf.extract('name', 'user_name')
# output: "data"->>'name' AS "user_name"
print(expr)

# Numeric index for array access
jf_tags = PgJsonField('tags', pg)
expr = jf_tags.extract(0)
# output: "tags"->>0
print(expr)
```

### PgJsonField.**extract_text(path, alias=None)**

*Inherited from [JsonField](jsonfield.md).* Extract a value as text. For PostgreSQL, produces the same output
as `extract()`.

### PgJsonField.**extract_object(path, alias=None)**

Extract a JSON object using the `->` operator. Unlike `extract()` / `extract_text()`, this preserves the JSON type
in the result.

- *path* - key name or array index
- *alias* - optional alias for the result

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

expr = jf.extract_object('config')
# output: "data"->'config'
print(expr)

expr = jf.extract_object('config', 'cfg')
# output: "data"->'config' AS "cfg"
print(expr)
```

### PgJsonField.**path_query(path, alias=None)**

PostgreSQL jsonpath query using the `@?` operator (requires PostgreSQL 12+).

- *path* - jsonpath expression
- *alias* - optional alias for the result

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

expr = jf.path_query('$.name')
# output: "data"::jsonb @? '$.name'
print(expr)
```

### PgJsonField.**as_jsonb()**

Set the field type to JSONB. Affects the type cast suffix in `__str__()`. Returns `self`.

### PgJsonField.**as_json()**

Set the field type to JSON. Affects the type cast suffix in `__str__()`. Returns `self`.

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

# Default is JSONB
# output: data::jsonb
print(jf)

jf.as_json()
# output: data::json
print(jf)

jf.as_jsonb()
# output: data::jsonb
print(jf)
```

### PgJsonField.**contains(value)**

*Inherited from [JsonField](jsonfield.md).* Check if the JSONB field contains a value using the `@>` operator.

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

expr = jf.contains('test')
# output: "data" @> %s::jsonb
print(expr)
```

### PgJsonField.**has_path(path)**

*Inherited from [JsonField](jsonfield.md).* Check if a key exists using the `??` operator.

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

expr = jf.has_path('name')
# output: "data" ?? 'name'
print(expr)
```

### PgJsonField.**\_\_getitem\_\_(key)**

Bracket notation using the `->` operator (preserves JSON type). Returns a new `PgJsonField`.

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

# Single level
nested = jf['address']
# output: data->"address"::jsonb
print(nested)

# Nested access
nested = jf['address']['city']
# output: data->"address"->"city"::jsonb
print(nested)
```

### PgJsonField.**\_\_str\_\_()**

Returns the field name with a type cast suffix (`::jsonb` or `::json`).

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()

jf = PgJsonField('data', pg)
# output: data::jsonb
print(jf)

jf = PgJsonField('data', pg, is_jsonb=False)
# output: data::json
print(jf)
```
