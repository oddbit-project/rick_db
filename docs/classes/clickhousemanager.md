# Class rick_db.backend.clickhouse.**ClickHouseManager**

This class extends [ManagerInterface](managerinterface.md) to provide a specific ClickHouse implementation.
It uses ClickHouse `system.*` tables for introspection. The `schema` parameter maps to ClickHouse `database`;
when `None`, the connection's current database is used.

```python
from rick_db.backend.clickhouse import ClickHouseConnection, ClickHouseManager

conn = ClickHouseConnection(host="localhost", port=8123, database="mydb")
mgr = ClickHouseManager(conn)
```

### ClickHouseManager.**\_\_init\_\_(db)**

Creates a new ClickHouseManager instance. Accepts a `ClickHouseConnection`.

### Supported methods

```python
# List tables and views
tables = mgr.tables()
views = mgr.views()

# Check existence
mgr.table_exists("events")
mgr.view_exists("events_summary")

# Inspect table structure
fields = mgr.table_fields("events")           # list of FieldRecord
for f in fields:
    print(f.field, f.type, f.primary)

pk = mgr.table_pk("events")                   # FieldRecord or None
indexes = mgr.table_indexes("events")         # list of FieldRecord

# Database management
databases = mgr.databases()
mgr.database_exists("mydb")
mgr.create_database("newdb")
mgr.drop_database("olddb")

# Users
users = mgr.users()

# Drop operations
mgr.drop_table("old_table")
mgr.drop_view("old_view")
```

### Schema/database equivalence

In ClickHouse, databases serve the role of schemas. The following methods delegate accordingly:

- `schemas()` — delegates to `databases()`
- `schema_exists(name)` — delegates to `database_exists(name)`

### Unsupported methods

The following methods are **not supported** and will raise `NotImplementedError`:

- `user_groups()`
- `create_schema()`
- `drop_schema()`
- `kill_clients()`
