# Keyset pagination

`Keyset` provides forward-only cursor pagination for queries where an offset
and total count are unnecessary. Each page is fetched with a parameterized SQL
row-value comparison, such as:

```sql
WHERE (created_at, id_product) > (?, ?)
ORDER BY created_at ASC, id_product ASC
LIMIT ?
```

Unlike `DbGrid.run()`, `Keyset.run()` does not issue a `COUNT(*)` query and
does not support jumping to an arbitrary page.

## Basic usage

```python
from rick_db import Keyset, Repository, fieldmapper


@fieldmapper(tablename="product", pk="id_product")
class Product:
    id = "id_product"
    created_at = "created_at"
    name = "name"


repo = Repository(connection, Product)
keyset = Keyset(repo, [Product.created_at, Product.id])

cursor = None
while True:
    rows, cursor = keyset.run(limit=50, cursor=cursor)
    for row in rows:
        print(row.id, row.name)
    if cursor is None:
        break
```

If `fields` is omitted, the Record primary key is used:

```python
keyset = Keyset(repo)
```

`run()` returns `(rows, next_cursor)`. `next_cursor` is `None` once there is
no following page. Treat cursors as values issued by the keyset and pass them
back unchanged; a cursor for different fields or direction raises
`KeysetError`.

## Base queries

Pass a `Select` through `qry=` for a one-off filter or join. The query must not
already have `ORDER BY`, `LIMIT`, or `OFFSET`; `Keyset` owns the ordering and
the page limit.

```python
published = repo.select().where("published", "=", True)
rows, cursor = keyset.run(limit=50, qry=published)
```

For a reusable query, subclass `Keyset` and override `default_query()`. The
returned `Select` may be cached: Keyset copies it before applying its predicate,
order, and limit.

```python
class PublishedProducts(Keyset):
    def default_query(self):
        return self._repo.select().where("published", "=", True)


keyset = PublishedProducts(repo, [Product.created_at, Product.id])
rows, cursor = keyset.run(limit=50)
```

## Requirements and limits

- Keyset fields must be database fields on the repository Record, selected by
  the base query, non-null, and collectively unique. Add the primary key as a
  final field when the preceding sort fields are not unique.
- Every keyset field has the same direction: `Keyset.ASC` (default) or
  `Keyset.DESC`. Mixed directions are not supported.
- `NULLS FIRST`/`NULLS LAST`, reverse paging, arbitrary page jumps, and a total
  result count are not supported.
- Cursor values support strings, booleans, integers, finite floats, dates,
  times, datetimes, decimals, and UUIDs. Unsupported or malformed values raise
  `KeysetError`.

The integration suite executes this contract against SQLite, PostgreSQL
(connections and pools), and ClickHouse.
