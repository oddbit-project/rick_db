# Error Classes

RickDb defines three exception classes for different error categories.

## rick_db.**RecordError**

Raised by the object mapper when record operations fail.

```python
from rick_db import RecordError
```

**Raised when:**

- `load()` is called with an unknown attribute name
- `pk()` is called on a record without a primary key definition

```python
from rick_db import fieldmapper, RecordError

@fieldmapper(tablename="users", pk="id_user")
class User:
    id = "id_user"
    name = "name"

try:
    user = User()
    user.load(nonexistent_field="value")
except RecordError as e:
    print("Record error:", e)
```

## rick_db.**DbConnectionError**

Raised for connection and transaction errors.

```python
from rick_db import DbConnectionError
```

**Raised when:**

- `begin()` is called while autocommit is enabled
- `begin()` is called when a transaction is already open

```python
from rick_db import DbConnectionError

try:
    conn.begin()
    conn.begin()  # raises DbConnectionError: transaction already open
except DbConnectionError as e:
    print("Connection error:", e)
```

A backward-compatibility alias `ConnectionError` exists but should not be used in new code, as it
shadows Python's builtin `ConnectionError`:

```python
from rick_db import DbConnectionError

# Preferred
try:
    conn.begin()
except DbConnectionError:
    pass

# Deprecated alias (avoid — shadows builtin)
# from rick_db import ConnectionError
```

## rick_db.sql.**SqlError**

Raised by the query builder for SQL generation errors.

```python
from rick_db.sql import SqlError
```

**Raised when:**

- `where()` receives an invalid field type
- `where()` receives an empty list for `IN`/`NOT IN`
- `group()` detects duplicate group fields
- `assemble()` is called with unbalanced `where_and()`/`where_or()`/`where_end()` blocks
- `Insert.assemble()` detects a field/value count mismatch
- `page()` receives a page number less than 1

```python
from rick_db.sql import Select, PgSqlDialect, SqlError

try:
    # Empty IN list raises SqlError
    Select(PgSqlDialect()).from_("users").where("id", "IN", []).assemble()
except SqlError as e:
    print("SQL error:", e)

try:
    # Unbalanced parentheses
    Select(PgSqlDialect()).from_("users").where_and().where("a", "=", 1).assemble()
except SqlError as e:
    print("SQL error:", e)
```

## Exception hierarchy

All three exceptions extend Python's `Exception` directly:

```
Exception
├── RecordError       (rick_db)
├── DbConnectionError (rick_db)
└── SqlError          (rick_db.sql)
```
