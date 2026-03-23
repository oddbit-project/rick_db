# ClickHouse SQL Builders

ClickHouse does not support standard SQL `UPDATE` and `DELETE` statements. Instead, it uses
`ALTER TABLE ... UPDATE` and `ALTER TABLE ... DELETE` mutation syntax. RickDb provides
`ClickHouseUpdate` and `ClickHouseDelete` builders that generate the correct syntax.

## Class rick_db.backend.clickhouse.**ClickHouseUpdate**

Extends [Update](update.md). Generates `ALTER TABLE ... UPDATE ... WHERE` instead of
`UPDATE ... SET ... WHERE`.

```python
from rick_db.backend.clickhouse import ClickHouseUpdate
from rick_db.sql import ClickHouseSqlDialect

dialect = ClickHouseSqlDialect()

qry, values = (
    ClickHouseUpdate(dialect)
    .table("events")
    .values({"status": "processed"})
    .where("id", "=", 42)
    .assemble()
)
# ALTER TABLE "events" UPDATE "status"=%s WHERE "id" = %s
print(qry)
```

All [Update](update.md) methods are available (`table()`, `values()`, `where()`, `orwhere()`).
Only `assemble()` is overridden to produce `ALTER TABLE` syntax. `returning()` is not supported
by ClickHouse.

## Class rick_db.backend.clickhouse.**ClickHouseDelete**

Extends [Delete](delete.md). Generates `ALTER TABLE ... DELETE WHERE` instead of
`DELETE FROM ... WHERE`.

```python
from rick_db.backend.clickhouse import ClickHouseDelete
from rick_db.sql import ClickHouseSqlDialect

dialect = ClickHouseSqlDialect()

qry, values = (
    ClickHouseDelete(dialect)
    .from_("events")
    .where("status", "=", "expired")
    .assemble()
)
# ALTER TABLE "events" DELETE WHERE "status" = %s
print(qry)
```

All [Delete](delete.md) methods are available (`from_()`, `where()`, `orwhere()`).
Only `assemble()` is overridden to produce `ALTER TABLE` syntax.

## Class rick_db.backend.clickhouse.**ClickHouseRepository**

Extends [Repository](repository.md). Overrides mutation methods to use ClickHouse-specific
SQL builders.

```python
from rick_db import fieldmapper
from rick_db.backend.clickhouse import (
    ClickHouseConnection,
    ClickHouseConnectionPool,
    ClickHouseRepository,
)

@fieldmapper(tablename="events", pk="id")
class Event:
    id = "id"
    event_type = "event_type"
    amount = "amount"

# With a direct connection
conn = ClickHouseConnection(host="localhost", port=8123, database="mydb")
repo = ClickHouseRepository(conn, Event)

# With a connection pool (recommended for production)
pool = ClickHouseConnectionPool(host="localhost", port=8123, database="mydb")
with pool.connection() as conn:
    repo = ClickHouseRepository(conn, Event)
    events = repo.fetch_all()
```

### Overridden methods

| Method | Difference from base Repository |
|--------|--------------------------------|
| `insert_pk(record)` | Always returns `None` (ClickHouse has no `RETURNING` or auto-increment) |
| `update(record, pk_value=None)` | Uses `ALTER TABLE ... UPDATE` syntax |
| `update_where(record, where_list)` | Uses `ALTER TABLE ... UPDATE` syntax |
| `delete_pk(pk_value)` | Uses `ALTER TABLE ... DELETE` syntax |
| `delete_where(where_clauses)` | Uses `ALTER TABLE ... DELETE` syntax |

All read methods (`fetch_all()`, `fetch_pk()`, `fetch_where()`, `fetch_one()`, `fetch()`, `select()`, `list()`)
are inherited from the base [Repository](repository.md) unchanged.

### Important notes

- ClickHouse mutations (`ALTER TABLE ... UPDATE/DELETE`) are **asynchronous** by default. They are
  scheduled and executed in the background. Use `MUTATIONS_SYNC` settings if synchronous behavior is needed.
- `insert_pk()` always returns `None`. You must supply primary key values explicitly when inserting.
- `transaction()` context manager works without errors but provides **no atomicity guarantees**.
