# rick_db

SQL database abstraction layer for Python. **Not an ORM** — follows a schema-first approach where the database structure is managed independently via SQL DDL.

Supports **PostgreSQL** (psycopg2), **SQLite3**, and **ClickHouse** (clickhouse-connect). **MySQL** is supported at the SQL query builder level via `MySqlSqlDialect`.

## Table of Contents

- [Quick Start](#quick-start) — Define Records, Connect, Use the Repository
- [SQL Query Builder](#sql-query-builder) — Dialects and setup
  - [Select](#select) — Basic queries and column selection
    - [Column aliases](#column-aliases) — Dict syntax, type casting
    - [WHERE conditions](#where-conditions) — Operators, IN/NOT IN, subqueries, field comparison
    - [AND / OR WHERE](#and--or-where) — Combining conditions
    - [Grouped WHERE with parentheses](#grouped-where-with-parentheses) — Nested AND/OR blocks
    - [Literal expressions](#literal-expressions) — Raw SQL via `Literal` / `L`
    - [Fn helper functions](#fn-helper-functions) — Aggregate, math, and general SQL functions
    - [GROUP BY and HAVING](#group-by-and-having) — Aggregation and filtering groups
    - [JOINs](#joins) — Inner, left, right, full, cross, natural, lateral
    - [ORDER BY, LIMIT, pagination](#order-by-limit-pagination) — Sorting and paging
    - [UNION](#union) — Combining result sets
    - [FOR UPDATE](#for-update) — Row locking
    - [Anonymous expressions](#anonymous-expressions-no-from) — SELECT without FROM
  - [Insert](#insert) — From objects, dicts, explicit fields, RETURNING
  - [Update](#update) — Values, literals, subqueries, WHERE, RETURNING
  - [Delete](#delete) — WHERE, IN/NOT IN, subqueries
  - [WITH (Common Table Expressions)](#with-common-table-expressions) — CTEs, recursive, materialized
- [Repository Extras](#repository-extras) — Custom repos, transactions, pagination, raw cursor
- [DbGrid](#dbgrid) — Searchable, filterable, paginated listings
- [Migrations](#migrations) — CLI and Python API
- [Database Introspection](#database-introspection) — PostgreSQL, SQLite, ClickHouse
- [Profiler](#profiler) — Query profiling
- [Development](#development) — Tests and design notes

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
from rick_db.backend.clickhouse import ClickHouseConnection, ClickHouseConnectionPool

conn = ClickHouseConnection(host="localhost", port=8123, database="mydb")
# or with pooling (recommended for production)
pool = ClickHouseConnectionPool(host="localhost", port=8123, database="mydb")
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

# Fetch with a dataclass instead of fieldmapper record
from dataclasses import dataclass

@dataclass
class UserInfo:
    name: str
    email: str

users = repo.fetch_where([("active", "=", True)], cols=["name", "email"], cls=UserInfo)
user = repo.fetch_one(repo.select(cols=["name", "email"]), cls=UserInfo)
```

## SQL Query Builder

Fluent builders for SELECT, INSERT, UPDATE, DELETE, and WITH (CTEs). All builders use a **fluent interface** — each method returns `self`, so calls can be chained. Every builder requires a **dialect** instance that controls placeholder syntax and identifier quoting. The final `.assemble()` call returns a `(sql, values)` tuple suitable for passing directly to a database cursor.

All scalar values passed to `where()`, `values()`, etc. become parameterized placeholders — never interpolated into the SQL string. Use `Literal` when you need raw SQL expressions that bypass parameterization.

```python
from rick_db.sql import Select, Insert, Update, Delete, With, Literal, Fn, PgSqlDialect

dialect = PgSqlDialect()   # uses %s placeholders
# or Sqlite3SqlDialect()   # uses ? placeholders
# or MySqlSqlDialect()     # uses %s placeholders, backtick quoting
```

### Select

#### Basic queries and column selection

`from_(table, cols=None, schema=None)` sets the table and optionally selects specific columns. The `table` argument accepts a string table name, a fieldmapper class or instance, a `Select` subquery, or a `Literal`. The `cols` argument accepts a list (specific columns), a dict (columns with aliases — see next section), or `None` (defaults to `*`).

```python
# All columns
Select(dialect).from_(User).assemble()

# Specific columns (list)
Select(dialect).from_(User, [User.id, User.name]).assemble()

# DISTINCT
Select(dialect).from_(User, [User.name]).distinct().assemble()
```

#### Column aliases

Pass a dict as the `cols` argument to `from_()` or any join method. Dict keys are field names (or `Fn`/`Literal` expressions), and values control aliasing:

- `None` — no alias, include the column as-is
- `"alias_name"` — adds `AS "alias_name"`
- `["cast_type"]` — casts the column (PG uses `::`, others use `CAST()`)
- `["cast_type", "alias_name"]` — cast + alias

```python
Select(dialect).from_(User, {User.id: "user_id", User.name: None}).assemble()
# SELECT "id_user" AS "user_id", "name" FROM "users"

# Alias with type casting (list value: [cast_type] or [cast_type, alias])
Select(dialect).from_(User, {User.id: ["int"], User.name: ["varchar", "user_name"]}).assemble()
# PG: SELECT "id_user"::int, "name"::varchar AS "user_name" FROM "users"
```

#### WHERE conditions

`where(field, operator=None, value=None)` adds a WHERE clause. The `field` can be a string column name, a fieldmapper attribute, a dict `{table: field}` for table-qualified references, or a `Literal` for raw expressions. The `operator` is any SQL comparison operator as a string. The `value` can be a scalar (parameterized), a list (expands to `IN`/`NOT IN`), a `Select` subquery, a dict `{table: field}` for cross-table comparison, or a `Literal`. For unary operators like `IS NULL`, omit the value.

```python
# Comparison operators: =, !=, <>, >, <, >=, <=
Select(dialect).from_(User).where(User.name, "=", "Alice").assemble()

# IS NULL / IS NOT NULL (no value needed)
Select(dialect).from_(User).where(User.email, "is null").assemble()
Select(dialect).from_(User).where(User.email, "is not null").assemble()

# LIKE / ILIKE (ILIKE not available on SQLite)
Select(dialect).from_(User).where(User.name, "like", "%alice%").assemble()

# IN / NOT IN with list (parameterized)
Select(dialect).from_(User).where(User.id, "in", [1, 2, 3]).assemble()
Select(dialect).from_(User).where(User.id, "not in", [4, 5]).assemble()

# IN with subquery
subquery = Select(dialect).from_(Order, [Order.user_id])
Select(dialect).from_(User).where(User.id, "in", subquery).assemble()

# Compare against another table's field (dict value)
Select(dialect).from_(User).where(User.id, "=", {"orders": "user_id"}).assemble()
# WHERE "id_user" = "orders"."user_id"
```

#### AND / OR WHERE

Multiple `where()` calls are concatenated with `AND`. Use `orwhere()` to join with `OR` instead. Both methods accept the same arguments. The first condition in a chain has no conjunction prefix.

```python
# Multiple .where() calls are joined with AND
Select(dialect).from_(User)\
    .where(User.active, "=", True)\
    .where(User.name, "like", "A%")\
    .assemble()
# WHERE "active" = %s AND "name" LIKE %s

# .orwhere() joins with OR
Select(dialect).from_(User)\
    .where(User.name, "=", "Alice")\
    .orwhere(User.name, "=", "Bob")\
    .assemble()
# WHERE "name" = %s OR "name" = %s
```

#### Grouped WHERE with parentheses

For complex boolean logic, use `where_and()` or `where_or()` to open a parenthesized group, and `where_end()` to close it. `where_and()` groups conditions joined by `AND` inside parentheses; `where_or()` groups conditions joined by `OR`. Groups can be nested. The builder tracks open/close balance — calling `.assemble()` on an unbalanced query raises an error via `validate()`.

```python
# (name = 'Alice' AND active = true) OR email LIKE '%@admin%'
Select(dialect).from_(User)\
    .where_and()\
        .where(User.name, "=", "Alice")\
        .where(User.active, "=", True)\
    .where_end()\
    .orwhere(User.email, "like", "%@admin%")\
    .assemble()

# active = true AND (name = 'Alice' OR name = 'Bob')
Select(dialect).from_(User)\
    .where(User.active, "=", True)\
    .where_or()\
        .where(User.name, "=", "Alice")\
        .where(User.name, "=", "Bob")\
    .where_end()\
    .assemble()
```

#### Literal expressions

`Literal` (also importable as `L`) wraps a raw SQL string that is emitted as-is — no quoting, no parameterization. Use it for SQL expressions, function calls, or any fragment the builder can't construct natively. `Literal` can be used anywhere a field name, table name, column, or value is accepted.

```python
from rick_db.sql import Literal

# Literal in WHERE
Select(dialect).from_(User).where(Literal("LENGTH(name)"), ">", 5).assemble()

# Literal as column
Select(dialect).from_(User, [User.name, Literal("COUNT(*) AS total")]).assemble()

# Literal as table
Select(dialect).from_(Literal("generate_series(1, 10) AS n")).assemble()
```

#### Fn helper functions

`Fn` is a convenience class with static methods that return `Literal` instances for common SQL functions. Since they return `Literal`, they can be used anywhere a `Literal` is accepted — as column expressions, in `having()`, in `where()`, etc. Functions are nestable: pass one `Fn` call as the argument to another.

```python
from rick_db.sql import Fn

# Aggregate functions
Fn.count()           # COUNT(*)
Fn.count("id")       # COUNT(id)
Fn.sum("amount")     # SUM(amount)
Fn.avg("price")      # AVG(price)
Fn.min("created")    # MIN(created)
Fn.max("created")    # MAX(created)

# Math functions
Fn.abs("balance")              # ABS(balance)
Fn.ceil("price")               # CEIL(price)
Fn.floor("price")              # FLOOR(price)
Fn.round("price", 2)           # ROUND(price, 2)
Fn.power("base", 3)            # POWER(base, 3)
Fn.sqrt("area")                # SQRT(area)
Fn.mod("value", 3)             # MOD(value, 3)
Fn.sign("balance")             # SIGN(balance)
Fn.trunc("price", 2)           # TRUNC(price, 2)

# General functions
Fn.coalesce("name", "'N/A'")   # COALESCE(name, 'N/A')
Fn.cast("id", "text")          # CAST(id AS text)

# Nesting
Fn.round(Fn.avg("price"), 2)   # ROUND(AVG(price), 2)

# Use with column aliases (dict syntax)
Select(dialect).from_(User, {
    User.name: None,
    Fn.count(): "cnt",
    Fn.sum("amount"): "total",
    Fn.round(Fn.avg("price"), 2): "avg_price",
}).group(User.name).assemble()
```

#### GROUP BY and HAVING

`group(fields)` adds a GROUP BY clause. Accepts a single field name, a `Literal`, or a list of fields/Literals. Duplicate fields are detected and raise an error. `having(field, operator, value)` filters grouped results — it has the same signature as `where()`. Multiple `having()` calls are joined with AND.

```python
Select(dialect).from_(User, {User.active: None, Fn.count(): "total"})\
    .group(User.active)\
    .having(Fn.count(), ">", 5)\
    .assemble()

# Multiple group fields
Select(dialect).from_(User, [User.active, User.name])\
    .group([User.active, User.name])\
    .assemble()
```

#### JOINs

All join methods follow the signature `join_*(table, field, expr_table, expr_field, operator=None, cols=None, schema=None, expr_schema=None)`:

- `table` — the table to join (string, fieldmapper class, or object)
- `field` — the join column on the joined table
- `expr_table` — the table to join against (the existing table in the query)
- `expr_field` — the join column on the existing table
- `operator` — join operator (defaults to `=`)
- `cols` — columns to select from the joined table (list or dict for aliases)
- `schema` / `expr_schema` — schema qualifiers for each table

`join()` is an alias for `join_inner()`. Cross and natural joins only take `(table, cols, schema)` since they have no ON clause. Lateral joins take `(subquery, alias, join_expr)` where `join_expr` is a `Literal` for the ON condition.

```python
# INNER JOIN (join() is an alias for join_inner())
Select(dialect).from_(User)\
    .join(Order, User.id, Order, Order.user_id)\
    .assemble()

# JOIN with columns from joined table
Select(dialect).from_(User, [User.name])\
    .join(Order, User.id, Order, Order.user_id, cols=[Order.total])\
    .assemble()

# LEFT / RIGHT / FULL OUTER JOIN
Select(dialect).from_(User)\
    .join_left(Order, User.id, Order, Order.user_id)\
    .assemble()
Select(dialect).from_(User)\
    .join_right(Order, User.id, Order, Order.user_id)\
    .assemble()
Select(dialect).from_(User)\
    .join_full(Order, User.id, Order, Order.user_id)\
    .assemble()

# CROSS JOIN / NATURAL JOIN
Select(dialect).from_(User).join_cross(Order).assemble()
Select(dialect).from_(User).join_natural(Order).assemble()

# JOIN with custom operator
Select(dialect).from_(User)\
    .join(Order, User.id, Order, Order.user_id, operator="!=")\
    .assemble()

# JOIN with schema
Select(dialect).from_(User)\
    .join(Order, User.id, Order, Order.user_id, schema="public", expr_schema="public")\
    .assemble()

# LATERAL JOIN (PostgreSQL)
subquery = Select(dialect).from_(Order, [Order.total]).where(Order.user_id, "=", Literal('"users"."id_user"'))
Select(dialect).from_(User)\
    .join_inner_lateral(subquery, "recent_orders", Literal("true"))\
    .assemble()
Select(dialect).from_(User)\
    .join_left_lateral(subquery, "recent_orders", Literal("true"))\
    .assemble()
```

#### ORDER BY, LIMIT, pagination

`order(fields, order=ASC)` adds ORDER BY. Accepts a single field, a list of fields (all same direction), or a dict `{field: "ASC"|"DESC"}` for mixed ordering. `limit(n, offset=None)` sets LIMIT/OFFSET directly. `page(page_number, rows_per_page)` is a convenience that calculates the offset from a 1-indexed page number (first page is 1).

```python
# Order ASC (default) / DESC
Select(dialect).from_(User).order(User.name).assemble()
Select(dialect).from_(User).order(User.name, Select.ORDER_DESC).assemble()

# Multiple order fields with dict
Select(dialect).from_(User).order({User.name: "ASC", User.id: "DESC"}).assemble()

# Limit and offset
Select(dialect).from_(User).limit(10, offset=20).assemble()

# Page helper (1-indexed page number, rows per page)
Select(dialect).from_(User).page(3, 10).assemble()  # page 3 -> offset=20, limit=10
```

#### UNION

`union(queries, union_type=UNION)` combines multiple SELECT queries. Accepts a list of `Select` objects or raw SQL strings. Use `Select.UNION` (default, deduplicates) or `Select.UNION_ALL` (keeps duplicates).

```python
q1 = Select(dialect).from_(User, [User.name]).where(User.active, "=", True)
q2 = Select(dialect).from_(User, [User.name]).where(User.active, "=", False)
Select(dialect).union([q1, q2]).assemble()
Select(dialect).union([q1, q2], Select.UNION_ALL).assemble()
```

#### FOR UPDATE

`for_update()` appends `FOR UPDATE` to the query for row-level locking within a transaction.

```python
Select(dialect).from_(User).where(User.id, "=", 1).for_update().assemble()
```

#### Anonymous expressions (no FROM)

`expr(cols)` generates a SELECT without a FROM clause — useful for computed values, database functions, or existence checks. Accepts a string, list, dict (with aliases), or `Literal`.

```python
Select(dialect).expr(Literal("1")).assemble()               # SELECT 1
Select(dialect).expr({Fn.count(): "total"}).assemble()      # SELECT COUNT(*) AS "total"
```

### Insert

`Insert` builds INSERT statements. The simplest usage passes a fieldmapper instance to `into()`, which extracts fields and values automatically. For more control, use `fields()` and `values()` separately. `values()` also accepts a dict (keys become field names). `returning()` adds a RETURNING clause (PostgreSQL, SQLite 3.35+).

```python
# From fieldmapper object (extracts fields/values automatically)
Insert(dialect).into(User(name="Bob", email="bob@test.com")).assemble()

# Explicit fields and values
Insert(dialect).into(User).fields(["name", "email"]).values(["Bob", "bob@test.com"]).assemble()

# From dict
Insert(dialect).into(User).values({"name": "Bob", "email": "bob@test.com"}).assemble()

# RETURNING (PostgreSQL, SQLite 3.35+)
Insert(dialect).into(user).returning([User.id]).assemble()
Insert(dialect).into(user).returning([User.id, User.name]).assemble()
```

### Update

`Update` builds UPDATE statements. `table()` sets the target — if passed a fieldmapper instance, it extracts fields, values, and adds a WHERE clause on the primary key automatically. `values()` accepts a dict of `{field: value}` pairs; values can be scalars (parameterized), `Literal` expressions (e.g. for incrementing), or `Select` subqueries. `where()` and `orwhere()` work identically to Select, including IN/NOT IN with lists and subqueries. `returning()` adds a RETURNING clause (PostgreSQL).

```python
# Basic update
Update(dialect).table(User).values({"name": "Bob"}).where(User.id, "=", 1).assemble()

# From fieldmapper object
Update(dialect).table(user).assemble()  # uses object's fields/values, WHERE on pk

# Literal expression in value (e.g. increment)
Update(dialect).table(User).values({"counter": Literal('"counter" + 1')}).where(User.id, "=", 1).assemble()

# Subquery in value
sub = Select(dialect).from_(Order, [Fn.max("total")]).where(Order.user_id, "=", Literal('"users"."id_user"'))
Update(dialect).table(User).values({"max_order": sub}).where(User.id, "=", 1).assemble()

# WHERE IN / NOT IN
Update(dialect).table(User).values({"active": False}).where(User.id, "in", [1, 2, 3]).assemble()
Update(dialect).table(User).values({"active": True}).where(User.id, "not in", [4, 5]).assemble()

# OR WHERE
Update(dialect).table(User).values({"active": False})\
    .where(User.name, "=", "Alice")\
    .orwhere(User.name, "=", "Bob")\
    .assemble()

# RETURNING (PostgreSQL)
Update(dialect).table(User).values({"name": "Bob"}).where(User.id, "=", 1)\
    .returning([User.id, User.name]).assemble()
```

### Delete

`Delete` builds DELETE statements. `from_()` sets the target table (string or fieldmapper class). `where()` and `orwhere()` filter rows to delete — same signature as Select, supporting IN/NOT IN with lists and subqueries.

```python
# Basic delete
Delete(dialect).from_(User).where(User.id, "=", 1).assemble()

# WHERE IN / NOT IN
Delete(dialect).from_(User).where(User.id, "in", [1, 2, 3]).assemble()
Delete(dialect).from_(User).where(User.id, "not in", [4, 5]).assemble()

# WHERE with subquery
inactive = Select(dialect).from_(Log, [Log.user_id]).where(Log.last_seen, "<", "2020-01-01")
Delete(dialect).from_(User).where(User.id, "in", inactive).assemble()

# OR WHERE
Delete(dialect).from_(User)\
    .where(User.active, "=", False)\
    .orwhere(User.email, "is null")\
    .assemble()
```

### WITH (Common Table Expressions)

`With` builds CTE (Common Table Expression) queries. `clause(name, with_query, columns=None, materialized=True)` adds a named CTE — `with_query` is a `Select` or `Literal`, `columns` optionally defines explicit column names, and `materialized=False` adds `NOT MATERIALIZED`. Multiple `clause()` calls add multiple CTEs. `query()` sets the main SELECT that references the CTEs. `recursive()` enables `WITH RECURSIVE`.

```python
# Basic CTE
cte_query = Select(dialect).from_(User, [User.id, User.name]).where(User.active, "=", True)
main_query = Select(dialect).from_(Literal("active_users"))
With(dialect).clause("active_users", cte_query).query(main_query).assemble()

# Multiple CTEs
With(dialect)\
    .clause("active_users", active_query)\
    .clause("recent_orders", orders_query)\
    .query(main_query)\
    .assemble()

# RECURSIVE CTE
With(dialect).recursive()\
    .clause("tree", recursive_query, columns=["id", "parent_id", "depth"])\
    .query(main_query)\
    .assemble()

# NOT MATERIALIZED
With(dialect).clause("tmp", subquery, materialized=False).query(main_query).assemble()
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

# ClickHouse (accepts connection or pool)
from rick_db.backend.clickhouse import ClickHouseManager

mgr = ClickHouseManager(conn)
mgr = ClickHouseManager(pool)  # also works with ClickHouseConnectionPool
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
- `DefaultProfiler` is thread-safe (protected by lock); `get_events()` returns a snapshot copy
- Supports Python 3.9+
