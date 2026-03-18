# Class rick_db.backend.pg.**PgManager**

This class extends [ManagerInterface](managerinterface.md) to provide a specific PostgreSQL implementation.

```python
from rick_db.backend.pg import PgManager, PgConnection

conn = PgConnection(dbname="mydb", user="user", password="pass", host="localhost")
mgr = PgManager(conn)
```

### PgManager.**\_\_init\_\_(db)**

Creates a new PgManager instance. Accepts a `PgConnection` or `PgConnectionPool`.

### Supported methods

All [ManagerInterface](managerinterface.md) methods are supported:

```python
# List tables and views
tables = mgr.tables()                         # list table names in default schema
tables = mgr.tables(schema="myschema")        # list tables in specific schema
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

# Schema and database management
schemas = mgr.schemas()
databases = mgr.databases()
users = mgr.users()
groups = mgr.user_groups("myuser")

# Create/drop operations
mgr.create_database("newdb")
mgr.create_schema("myschema")
mgr.drop_table("old_table", cascade=True)
mgr.drop_view("old_view")
mgr.drop_schema("myschema", cascade=True)
mgr.drop_database("olddb")
mgr.kill_clients("mydb")                      # terminate all connections to a database
```

### PostgreSQL-specific notes

- Default schema is `"public"` (available as `PgManager.SCHEMA_DEFAULT`)
- `schemas()` returns namespace names from `pg_catalog.pg_namespace`
- `kill_clients()` uses `pg_terminate_backend()` to terminate connections

### See also

- [PgInfo](../classes/pgmanager.md#pginfo) for richer PostgreSQL introspection
- [ManagerInterface](managerinterface.md) for the full method reference

## PgInfo

`PgInfo` provides detailed PostgreSQL introspection beyond what `PgManager` offers. It queries
`information_schema` and `pg_catalog` tables for server-level and database-level metadata.

```python
from rick_db.backend.pg.pginfo import PgInfo

info = PgInfo(conn)
```

### PgInfo.**\_\_init\_\_(db)**

Creates a new PgInfo instance. Accepts a `PgConnection` or `PgConnectionPool`.

### Server information

| Method | Returns | Description |
|--------|---------|-------------|
| `get_server_version()` | `str` | PostgreSQL server version string |
| `list_server_databases()` | `list[DatabaseRecord]` | All databases on the server |
| `list_server_roles()` | `list[RoleRecord]` | All roles |
| `list_server_users()` | `list[UserRecord]` | All users (roles with login) |
| `list_server_groups()` | `list[GroupRecord]` | All groups (roles without login) |
| `list_user_groups(user_name)` | `list[GroupRecord]` | Groups for a specific user |
| `list_server_tablespaces()` | `list[TableSpaceRecord]` | All tablespaces |
| `list_server_settings()` | `list[SettingRecord]` | Server configuration settings |

### Database information

| Method | Returns | Description |
|--------|---------|-------------|
| `list_database_namespaces()` | `list[NamespaceRecord]` | All namespaces in current database |
| `list_database_schemas()` | `list[NamespaceRecord]` | All schemas (alias for namespaces) |
| `list_database_tables(schema=None)` | `list[TableRecord]` | Base tables |
| `list_database_views(schema=None)` | `list[TableRecord]` | Views |
| `list_database_temporary_tables(schema=None)` | `list[TableRecord]` | Local temporary tables |
| `list_database_foreign_tables(schema=None)` | `list[TableRecord]` | Foreign tables |

### Table information

| Method | Returns | Description |
|--------|---------|-------------|
| `list_table_columns(table_name, schema=None)` | `list[ColumnRecord]` | Detailed column information |
| `list_table_pk(table_name, schema=None)` | `ConstraintRecord` or `None` | Primary key constraint |
| `list_table_indexes(table_name, schema=None)` | `list[FieldRecord]` | Indexed fields |
| `list_table_foreign_keys(table_name, schema=None)` | `list[ForeignKeyRecord]` | Foreign key relationships |
| `list_table_sequences(table_name, schema=None)` | `list[SequenceRecord]` | Associated sequences |
| `list_identity_columns(table_name, schema=None)` | `list[IdentityRecord]` | Identity columns |
| `table_exists(table_name, table_type=None, schema=None)` | `bool` | Check table existence by type |

### Table type constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PgInfo.TYPE_BASE` | `"BASE TABLE"` | Regular table |
| `PgInfo.TYPE_VIEW` | `"VIEW"` | View |
| `PgInfo.TYPE_FOREIGN` | `"FOREIGN TABLE"` | Foreign table |
| `PgInfo.TYPE_LOCAL` | `"LOCAL TEMPORARY"` | Temporary table |

### Example

```python
from rick_db.backend.pg import PgConnection
from rick_db.backend.pg.pginfo import PgInfo

conn = PgConnection(dbname="mydb", user="user", password="pass", host="localhost")
info = PgInfo(conn)

# Server info
print("Version:", info.get_server_version())
for db in info.list_server_databases():
    print("Database:", db.name)

# Table details
for col in info.list_table_columns("users"):
    print(col.field, col.type)

# Foreign keys
for fk in info.list_table_foreign_keys("orders"):
    print("{}.{} -> {}.{}".format(fk.table, fk.column, fk.foreign_table, fk.foreign_column))

# Sequences
for seq in info.list_table_sequences("users"):
    print("Sequence:", seq.name)
```
