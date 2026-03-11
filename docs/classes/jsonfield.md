# Class rick_db.sql.**JsonField**

Specialized class for working with JSON/JSONB fields in SQL queries. Generates SQL expressions as `Literal` objects
that can be used in `Select`, `where()`, and other query builder methods.

When a dialect with `json_support` is provided, dialect-specific operators are used. Otherwise, generic `JSON_EXTRACT()`
/ `JSON_CONTAINS()` syntax is generated as fallback.

See also: [PgJsonField](pgjsonfield.md) for PostgreSQL-specific extensions, and [JSON Operations](../json_operations.md)
for usage examples.

### JsonField.**\_\_init\_\_(field_name, dialect=None)**

Create a JsonField for the given *field_name*. An optional *dialect* can be provided to enable dialect-specific SQL
generation.

```python
from rick_db.sql import JsonField
from rick_db.sql.dialect import PgSqlDialect

# Without dialect (generic SQL)
jf = JsonField('data')

# With PostgreSQL dialect
jf = JsonField('data', PgSqlDialect())
```

### JsonField.**extract(path, alias=None)**

Extract a value from the JSON field. Returns a `Literal` SQL expression.

- *path* - JSON path or key name to extract
- *alias* - optional alias for the result

```python
from rick_db.sql import JsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = JsonField('data', pg)

expr = jf.extract('name')
# output: "data"->>'name'
print(expr)

expr = jf.extract('name', 'user_name')
# output: "data"->>'name' AS "user_name"
print(expr)
```

Without a dialect:
```python
from rick_db.sql import JsonField

jf = JsonField('data')

expr = jf.extract('$.name')
# output: JSON_EXTRACT(data, '$.name')
print(expr)
```

### JsonField.**extract_text(path, alias=None)**

Extract a value as text from the JSON field. Returns a `Literal` SQL expression.
For PostgreSQL, this produces the same output as `extract()` (both use the `->>` operator).

- *path* - JSON path or key name to extract
- *alias* - optional alias for the result

```python
from rick_db.sql import JsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = JsonField('data', pg)

expr = jf.extract_text('email', 'user_email')
# output: "data"->>'email' AS "user_email"
print(expr)
```

### JsonField.**contains(value)**

Check if the JSON field contains a value. Returns a `Literal` SQL expression with a parameter placeholder.
The *value* argument is not interpolated into the SQL; it should be passed separately for parameter binding.

- *value* - value to check for (used for parameter binding)

```python
from rick_db.sql import JsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = JsonField('data', pg)

expr = jf.contains('test')
# output: "data" @> %s::jsonb
print(expr)
```

### JsonField.**has_path(path)**

Check if a path exists in the JSON field. Returns a `Literal` SQL expression.

- *path* - path to check for existence

```python
from rick_db.sql import JsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = JsonField('data', pg)

expr = jf.has_path('name')
# output: "data" ?? 'name'
print(expr)
```

### JsonField.**\_\_getitem\_\_(key)**

Bracket notation for JSON path access. Returns a new `JsonField` representing the nested path.

Uses the `->>` operator to build the path expression.

```python
from rick_db.sql import JsonField

jf = JsonField('data')

nested = jf['name']
# output: data->>"name"
print(nested)
```

### JsonField.**\_\_str\_\_()**

Returns the field name string.

```python
from rick_db.sql import JsonField

jf = JsonField('data')
# output: data
print(jf)
```
