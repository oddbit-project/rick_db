# Class rick_db.backend.sqlite.**Sqlite3Manager**

This class extends [ManagerInterface](managerinterface.md) to provide a specific SQLite3 implementation.

```python
from rick_db.backend.sqlite import Sqlite3Connection, Sqlite3Manager

conn = Sqlite3Connection(":memory:")
mgr = Sqlite3Manager(conn)
```

### Sqlite3Manager.**\_\_init\_\_(db)**

Creates a new Sqlite3Manager instance. Accepts a `Sqlite3Connection`.

### Supported methods

```python
# List tables and views
tables = mgr.tables()
views = mgr.views()

# Check existence
mgr.table_exists("users")
mgr.view_exists("active_users")

# Inspect table structure
fields = mgr.table_fields("users")            # list of FieldRecord
for f in fields:
    print(f.field, f.type, f.primary)

pk = mgr.table_pk("users")                    # FieldRecord or None
indexes = mgr.table_indexes("users")          # list of FieldRecord
view_fields = mgr.view_fields("my_view")      # list of FieldRecord

# Drop operations
mgr.drop_table("old_table")
mgr.drop_view("old_view")
```

### Unsupported methods

The following methods are **not supported** by SQLite and will either return empty lists or raise `NotImplementedError`:

- `schemas()`
- `databases()`
- `users()`
- `user_groups()`
- `create_database()`
- `database_exists()`
- `drop_database()`
- `create_schema()`
- `schema_exists()`
- `drop_schema()`
- `kill_clients()`
