# rick_db

SQL database abstraction layer for Python. **Not an ORM** — follows a schema-first approach where the database structure is managed independently via SQL DDL.

Supports **PostgreSQL** (psycopg2), **SQLite3**, and **ClickHouse** (clickhouse-connect). **MySQL** is supported at the SQL query builder level via `MySqlSqlDialect`.

## Quick Start

### Define Records

The `@fieldmapper` decorator maps Python attributes to database columns:

```python
from rick_db import fieldmapper

@fieldmapper(tablename="users", pk="id_user")
class User:
    id = "id_user"
    name = "name"
    email = "email"
    active = "active"
```

Record instances support `asdict()`, `asrecord()`, `fields()`, `values()`, `pk()`, `has_pk()`, `fromrecord()`, and `load()`.

### Connect

```python
# PostgreSQL
from rick_db.backend.pg import PgConnection, PgConnectionPool

conn = PgConnection(dbname="mydb", user="user", password="pass", host="localhost")
# or with pooling (recommended for production)
pool = PgConnectionPool(dbname="mydb", user="user", password="pass", host="localhost")

# SQLite
from rick_db.backend.sqlite import Sqlite3Connection

conn = Sqlite3Connection("mydb.db")       # file-based
conn = Sqlite3Connection(":memory:")       # in-memory

# ClickHouse
from rick_db.backend.clickhouse import ClickHouseConnection

conn = ClickHouseConnection(host="localhost", port=8123, database="mydb")
```

### Use the Repository

```python
from rick_db import Repository

repo = Repository(conn, User)

# Create
user_id = repo.insert_pk(User(name="Alice", email="alice@example.com"))

# Read
user = repo.fetch_pk(user_id)
users = repo.fetch_all()
users = repo.fetch_where([("name", "=", "Alice")])

# Update
user.name = "Alice Updated"
repo.update(user)

# Delete
repo.delete_pk(user_id)
```

## SQL Query Builder

Fluent builders for SELECT, INSERT, UPDATE, DELETE. All builders require a dialect and produce `(sql, values)` tuples via `.assemble()`.

```python
from rick_db.sql import Select, Insert, Update, Delete, Literal, PgSqlDialect

dialect = PgSqlDialect()   # uses %s placeholders
# or Sqlite3SqlDialect()   # uses ? placeholders
# or MySqlSqlDialect()     # uses %s placeholders, backtick quoting
```

### Select

```python
# Basic
Select(dialect).from_(User).assemble()
Select(dialect).from_(User, [User.id, User.name]).assemble()

# WHERE
Select(dialect).from_(User).where(User.name, "=", "Alice").assemble()

# JOIN
Select(dialect).from_(User).join(Order, User.id, Order, Order.user_id).assemble()

# Aggregation
Select(dialect).from_(User, {Literal("COUNT(*)"): "total"}).group(User.active).assemble()

# Pagination
Select(dialect).from_(User).order(User.name).limit(10, offset=20).assemble()
```

### Insert / Update / Delete

```python
Insert(dialect).into(User(name="Bob", email="bob@test.com")).assemble()
Insert(dialect).into(user).returning([User.id]).assemble()  # PG only

Update(dialect).table(User).values({"name": "Bob"}).where(User.id, "=", 1).assemble()

Delete(dialect).from_(User).where(User.id, "=", 1).assemble()
```

## Repository Extras

```python
# Custom repository
class UserRepository(Repository):
    def __init__(self, db):
        super().__init__(db, User)

    def find_by_email(self, email):
        return self.fetch_one(self.select().where(User.email, "=", email))

# Transactions
with repo.transaction():
    repo.insert_pk(user1)
    repo.insert_pk(user2)
    # auto-commit on success, auto-rollback on exception

# Pagination helper
total, rows = repo.list(repo.select().order(User.id), limit=10, offset=0)

# Raw cursor access
with conn.cursor() as c:
    rows = c.fetchall("SELECT * FROM users WHERE id > %s", (0,), cls=User)
```

## DbGrid

Searchable, filterable, paginated data listings:

```python
from rick_db import DbGrid

grid = DbGrid(repo, search_fields=[User.name, User.email])
total, rows = grid.run(search_text="alice", limit=20, offset=0,
                       sort_fields={User.name: "ASC"},
                       match_fields={User.active: True})
```

Search types: `SEARCH_ANY` (default, `%text%`), `SEARCH_START` (`text%`), `SEARCH_END` (`%text`), `SEARCH_NONE`.

## Migrations

Forward-only migration system (no rollbacks). Managed via CLI or Python API.

### CLI

Configure `rickdb.toml`:

```toml
[db]
engine = "pgsql"
host = "localhost"
port = 5432
user = "myuser"
password = "mypassword"
dbname = "mydb"
```

Commands:

```bash
rickdb init             # install migration table
rickdb list             # list applied migrations
rickdb check <path>     # check pending migrations in path
rickdb migrate <path>   # run pending migrations from path
rickdb flatten <name>   # compress history into one entry
rickdb dto <table> <file>  # generate fieldmapper DTO from table
rickdb <prefix> <cmd>   # use [db_<prefix>] config section
```

### Python API

```python
from rick_db.backend.pg import PgManager, PgMigrationManager

mgr = PgManager(conn)
mm = PgMigrationManager(mgr)
mm.install()
mm.list()
```

## Database Introspection

```python
# PostgreSQL
from rick_db.backend.pg import PgManager
from rick_db.backend.pg.pginfo import PgInfo

mgr = PgManager(conn)
mgr.tables()              # list table names
mgr.table_exists("users") # check existence
mgr.table_fields("users") # column info
mgr.table_pk("users")     # primary key
mgr.views(), mgr.schemas(), mgr.databases(), mgr.users()

info = PgInfo(conn)        # richer introspection
info.list_table_foreign_keys("orders")
info.list_table_sequences("users")
info.get_server_version()

# SQLite
from rick_db.backend.sqlite import Sqlite3Manager

mgr = Sqlite3Manager(conn)
mgr.tables(), mgr.views(), mgr.table_fields("users"), mgr.table_pk("users")

# ClickHouse
from rick_db.backend.clickhouse import ClickHouseManager

mgr = ClickHouseManager(conn)
mgr.tables(), mgr.views(), mgr.table_fields("users"), mgr.table_pk("users")
mgr.databases(), mgr.users()
```

## Profiler

```python
from rick_db.profiler import DefaultProfiler

conn.profiler = DefaultProfiler()
# ... run queries ...
for event in conn.profiler.get_events():
    print(event.query, event.elapsed)
```

## Development

### Running Tests

```bash
# SQLite tests only (no external dependencies)
.venv_test/bin/pytest tests/test_mapper.py tests/test_cache.py tests/sql/ \
    tests/backend/sqlite/ tests/repository/test_sqlite_repository.py \
    tests/dbgrid/test_sqlite_dbgrid.py tests/cursor/test_cursor_sqlite3.py -x -q

# Full suite with PostgreSQL (requires docker)
tox -e py311

# Linting
tox -e flake
```

### Key Design Notes

- `Cursor.exec()` auto-commits outside transactions — this is intentional
- `DbConnectionError` is the correct name; `ConnectionError` alias exists for backward compatibility
- SQLite has no `ILIKE`; DbGrid uses `UPPER()` for case-insensitive search
- Migration `execute()` is not fully transactional between SQL execution and registration
- `DefaultProfiler` is not thread-safe
- Supports Python 3.9+
