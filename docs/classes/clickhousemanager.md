# Class rick_db.backend.clickhouse.**ClickHouseManager**

This class extends [ManagerInterface](managerinterface.md) to provide a specific ClickHouse implementation.
It uses ClickHouse `system.*` tables for introspection. The `schema` parameter maps to ClickHouse `database`;
when `None`, the connection's current database is used.

Accepts either a `ClickHouseConnection` or a `ClickHouseConnectionPool`.

```python
from rick_db.backend.clickhouse import ClickHouseConnection, ClickHouseConnectionPool, ClickHouseManager

# With a connection
conn = ClickHouseConnection(host="localhost", port=8123, database="mydb")
mgr = ClickHouseManager(conn)

# With a connection pool (recommended for production)
pool = ClickHouseConnectionPool(host="localhost", port=8123, database="mydb")
mgr = ClickHouseManager(pool)

# With explicit database name
mgr = ClickHouseManager(pool, database="other_db")
```

### ClickHouseManager.**\_\_init\_\_(db, database=None)**

Creates a new ClickHouseManager instance.

- `db` — a `ClickHouseConnection` or `ClickHouseConnectionPool`
- `database` — optional database name override. If not provided, the database is extracted from the connection's client config or the pool's connection parameters.

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

- `create_schema()` — use `create_database()` instead
- `drop_schema()` — use `drop_database()` instead
- `kill_clients()`

The following method returns an empty result (ClickHouse has no group concept):

- `user_groups()` — returns `[]`
