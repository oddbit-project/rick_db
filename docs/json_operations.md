# JSON Operations

RickDb provides comprehensive support for working with JSON data in SQL queries through the `JsonField` and
`PgJsonField` classes, as well as helper methods on the `Select` query builder.

## Overview

JSON support is available at two levels:

- **JsonField** - Base class for JSON operations, works with any dialect that has `json_support` enabled
- **PgJsonField** - PostgreSQL-specific extension with additional operations like `extract_object()`, `path_query()`,
  and JSONB type casting
- **Select helpers** - Convenience methods on the `Select` class: `json_field()`, `json_extract()`, and `json_where()`

## JsonField

The `JsonField` class wraps a JSON column name and provides methods that generate SQL expressions as `Literal` objects,
suitable for use in `Select`, `where()`, and other query builder methods.

```python
from rick_db.sql import JsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
json_field = JsonField('data', pg)
```

When no dialect is provided (or the dialect does not have `json_support`), fallback expressions using `JSON_EXTRACT()`
and `JSON_CONTAINS()` are generated instead.

### Extracting values

```python
from rick_db.sql import JsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = JsonField('data', pg)

# Extract as text using ->> (PostgreSQL)
expr = jf.extract('name')
# output: "data"->>'name'
print(expr)

# Extract with alias
expr = jf.extract('name', 'user_name')
# output: "data"->>'name' AS "user_name"
print(expr)

# Extract as text (same as extract for PostgreSQL)
expr = jf.extract_text('email', 'user_email')
# output: "data"->>'email' AS "user_email"
print(expr)
```

Without a dialect, generic `JSON_EXTRACT()` syntax is used:
```python
from rick_db.sql import JsonField

jf = JsonField('data')

expr = jf.extract('$.name')
# output: JSON_EXTRACT(data, '$.name')
print(expr)
```

### Checking containment and paths

```python
from rick_db.sql import JsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = JsonField('data', pg)

# Check if JSON contains a value (generates parameterized SQL)
expr = jf.contains('test')
# output: "data" @> %s::jsonb
print(expr)

# Check if a path exists
expr = jf.has_path('name')
# output: "data" ?? 'name'
print(expr)
```

### Bracket notation

`JsonField` supports bracket notation for path access. Each bracket returns a new `JsonField`:

```python
from rick_db.sql import JsonField

jf = JsonField('data')

nested = jf['name']
# output: data->>"name"
print(nested)
```

For more details, see the [JsonField](classes/jsonfield.md) class reference.

## PgJsonField

`PgJsonField` extends `JsonField` with PostgreSQL-specific features for JSON and JSONB columns.

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)
```

### Extracting JSON objects

The `extract_object()` method uses the `->` operator, which preserves the JSON type (unlike `->>` which returns text):

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

# Extract as JSON object (preserves type)
expr = jf.extract_object('config')
# output: "data"->'config'
print(expr)

# With alias
expr = jf.extract_object('config', 'cfg')
# output: "data"->'config' AS "cfg"
print(expr)
```

### jsonpath queries (PostgreSQL 12+)

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

expr = jf.path_query('$.name')
# output: "data"::jsonb @? '$.name'
print(expr)
```

### Type casting

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('data', pg)

# Default is JSONB
# output: data::jsonb
print(jf)

# Cast to JSON
jf.as_json()
# output: data::json
print(jf)

# Cast back to JSONB
jf.as_jsonb()
# output: data::jsonb
print(jf)
```

### Bracket notation (PostgreSQL)

`PgJsonField` brackets use the `->` operator (preserving JSON type), unlike `JsonField` which uses `->>`:

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

For more details, see the [PgJsonField](classes/pgjsonfield.md) class reference.

### Array index access

PostgreSQL JSON operators also support numeric indices for arrays:

```python
from rick_db.sql import PgJsonField
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
jf = PgJsonField('tags', pg)

# Extract first element as text
expr = jf.extract(0)
# output: "tags"->>0
print(expr)
```

## Select helper methods

The `Select` query builder provides convenience methods for JSON operations.

### json_field()

Creates a `JsonField` or `PgJsonField` instance bound to the current query's dialect:

```python
from rick_db.sql import Select
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
qry = Select(pg).from_('users')

# Creates a PgJsonField (since dialect is PgSqlDialect)
jf = qry.json_field('user_data')

# With table qualifier
jf = qry.json_field('config', 'users')
```

### json_extract()

Adds a JSON extraction expression to the SELECT column list:

```python
from rick_db.sql import Select
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
qry = Select(pg).from_('users').json_extract('user_data', 'name', 'user_name')
sql, _ = qry.assemble()
# output: SELECT "users".*,"user_data"->>'name' AS "user_name" FROM "users"
print(sql)
```

### json_where()

Adds a WHERE condition on a JSON field:

```python
from rick_db.sql import Select
from rick_db.sql.dialect import PgSqlDialect

pg = PgSqlDialect()
qry = Select(pg).from_('users').json_where('user_data', 'active', '=', True)
sql, values = qry.assemble()
# output: SELECT "users".* FROM "users" WHERE ("user_data"->>'active' = %s)
print(sql)
# values: [True]
print(values)
```

## Complete example

Combining JSON operations in a full query:

```python
from rick_db import fieldmapper
from rick_db.sql import Select, PgJsonField
from rick_db.sql.dialect import PgSqlDialect

@fieldmapper(tablename='users', pk='id_user')
class User:
    id = 'id_user'
    name = 'name'
    profile = 'profile'  # JSONB column

pg = PgSqlDialect()

# Create a JSON field helper
jf = PgJsonField(User.profile, pg)

# Build a query that extracts JSON data and filters by JSON values
qry = (
    Select(pg)
    .from_(User, [User.id, User.name])
    .json_extract(User.profile, 'email', 'user_email')
    .json_where(User.profile, 'active', '=', True)
    .order(User.name)
    .limit(10)
)

sql, values = qry.assemble()
# output: SELECT "id_user","name","profile"->>'email' AS "user_email" FROM "users"
#         WHERE ("profile"->>'active' = %s) ORDER BY "name" ASC LIMIT 10
print(sql)
# values: [True]
print(values)
```

## Dialect support

| Feature | PostgreSQL | MySQL | SQLite | Generic |
|---|---|---|---|---|
| `extract()` | `->>` operator | `JSON_EXTRACT()` | Not built-in | `JSON_EXTRACT()` |
| `extract_text()` | `->>` operator | `JSON_UNQUOTE(JSON_EXTRACT())` | Not built-in | `JSON_EXTRACT()` |
| `extract_object()` | `->` operator | N/A | N/A | N/A |
| `path_query()` | `@?` operator | N/A | N/A | N/A |
| `contains()` | `@>` operator | `JSON_CONTAINS()` | Not built-in | `JSON_CONTAINS()` |
| `has_path()` | `??` operator | `JSON_CONTAINS_PATH()` | Not built-in | `JSON_CONTAINS_PATH()` |
| `as_jsonb()` / `as_json()` | Type casting | N/A | N/A | N/A |

PostgreSQL has native JSON support enabled by default in `PgSqlDialect`. MySQL has JSON support enabled by default
in `MySqlSqlDialect`, using MySQL 5.7+ JSON functions. The `Sqlite3SqlDialect` does not currently enable `json_support`,
so JSON operations will fall back to generic syntax if used with a `JsonField` without a dialect.
