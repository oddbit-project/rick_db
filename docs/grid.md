# DbGrid

[DbGrid](classes/dbgrid.md) is a helper class to aid the creation of table-like listings(grids). It provides a clean,
programmatic way of searching a given database object (or use a custom query) with string search, exact matching and
pagination. 

It returns the total row count (without applying pagination), and the filtered row subset matching the pagination results.

Example:

```python
from rick_db import fieldmapper, Repository, DbGrid
from rick_db.backend.pg import PgConnectionPool


@fieldmapper(tablename='product', pk='id_product')
class Product:
    id = 'id_product'
    short_description = 'short_description'
    brand = 'brand_id'


db_config = {
    "dbname": "products",
    "user": "someUser",
    "password": "somePassword",
    "host": "localhost",
    "port": 5432
}

# create connection
pool = PgConnectionPool(**db_config)

# create a repository
repo = Repository(pool, Product)

# create a grid
grid = DbGrid(
    repo,                           # repository to use
    [Product.short_description],    # fields to perform text search
    DbGrid.SEARCH_ANY               # type of search
)

# retrieve first 10 results
# total will have the total row count that matches the filters, without limit
total, rows = grid.run(search_text='bag', match_fields={Product.brand: 12}, limit=10)
print("total matches:", total)
for r in rows:
    print(r.id, r.short_description)

# retrieve second page of results
total, rows = grid.run(search_text='bag', match_fields={Product.brand: 12}, limit=10, offset=10)
for r in rows:
    print(r.id, r.short_description)
```

### Search types

The `search_type` parameter controls how text search patterns are generated:

| Constant | Value | Pattern | Description |
|----------|-------|---------|-------------|
| `DbGrid.SEARCH_ANY` | 1 | `%text%` | Match anywhere in the field (default) |
| `DbGrid.SEARCH_START` | 2 | `text%` | Match at the beginning of the field |
| `DbGrid.SEARCH_END` | 3 | `%text` | Match at the end of the field |
| `DbGrid.SEARCH_NONE` | 0 | — | Disable text search |

### Sorting

The `sort_fields` parameter accepts a dict of `{field: direction}` pairs, where direction is `"ASC"` or `"DESC"`:

```python
total, rows = grid.run(sort_fields={Product.name: "ASC", Product.id: "DESC"}, limit=20)
```

### Limitations

**SQLite3**

On SQLite3, case-insensitive search is done via UPPER(), since no ILIKE equivalent is available.
This may trigger a full table scan and will not use indexes if they are available for the specific field. Additionally,
this method only works with ASCII chars.

It is therefore recommended to avoid the usage of case-sensitive search with this driver.

As an option, one can instead use COLLATE NOCASE on the creation of the required fields, and use DbGrid with case_sensitive=True.
This way, search will be case-insensitive on the fields created with the COLLATE NOCASE option.


## Keyset pagination

`run()` paginates with `LIMIT`/`OFFSET` and reports a total row count. That is
the right shape for a grid with page numbers, but the cost of a page grows with
its depth — the database produces every row up to the offset and discards it —
and the total requires a `COUNT(*)` over the whole filtered set.

`run_seek()` paginates by *keyset* (also called cursor or seek pagination)
instead. It answers "the N rows after this cursor" rather than "N rows at
offset M", so the database seeks straight to the cursor position on the index
and reads forward:

```python
from rick_db import DbGrid, Keyset

grid = DbGrid(repo, search_fields=[Product.name])

# first page
rows, cursor = grid.run_seek(limit=20)

# subsequent pages
while cursor is not None:
    rows, cursor = grid.run_seek(limit=20, cursor=cursor)
```

A `None` cursor means there are no more rows. `search_text` and `match_fields`
work exactly as they do in `run()`.

### Choosing between run() and run_seek()

| | `run()` | `run_seek()` |
|---|---|---|
| Cost of page *n* | grows with *n* | constant |
| Total row count | yes | no |
| Jump to an arbitrary page | yes | no |
| Stable while rows are inserted | no | yes |
| Arbitrary sort per request | yes | fixed by the keyset |

The stability difference matters more than it looks. With `OFFSET`, a row
inserted above the current page shifts everything down by one, so a user
scrolling a busy table sees a row twice or misses one entirely. A keyset
cursor names a position in the data rather than a count of rows, so it is
unaffected.

### Keysets

`Keyset` declares the ordering and, with it, the seek predicate:

```python
# the default: primary key, ascending
rows, cursor = grid.run_seek(limit=20)

# newest first, with the pk as a tiebreaker
ks = Keyset([Product.created], Keyset.DESC, pk=Product.id)
rows, cursor = grid.run_seek(limit=20, keyset=ks)

# fields that are already unique
ks = Keyset([Product.sku], unique=True)
```

Three rules the API enforces rather than documents, because all three failure
modes are silent — the walk still ends cleanly, so the caller believes it saw
every row:

**Every field sorts in the same direction.** A keyset ordered
`(a ASC, b DESC)` cannot be expressed as a seek predicate at all, so the
direction is a single parameter rather than a per-field one.

**The ordering must be unique.** Seeking on a non-unique ordering skips or
repeats rows whenever two of them share a value at a page boundary. Uniqueness
cannot be detected at runtime, so it has to be stated: pass `pk=` to append a
tiebreaker, or `unique=True` to assert the fields already are. A keyset with
neither is refused at construction.

> **`unique=True` is your assertion, not a check.** Nothing verifies it, and if
> the fields are not in fact unique you get exactly the silent row loss the flag
> exists to prevent. Prefer `pk=`, which appends a column the database already
> guarantees is unique. Reach for `unique=True` only when the leading fields
> carry a unique constraint of their own.

**The keyset owns the ordering.** The query must not already carry an
`ORDER BY`: the keyset appends its terms, so a pre-existing sort would lead and
leave the seek predicate advancing on a trailing term. That is refused rather
than merged. For the same reason the query must not carry its own
`LIMIT`/`OFFSET`, which paging would silently replace. This applies to a query
passed as `qry=` **and** to one returned by a `default_query()` override — the
error names the ordering, not where it came from.

**Keyset fields must be NOT NULL**, and orderable scalars (integer, string,
date/time, decimal, UUID). This one the database has to guarantee and nothing
here checks it: a `NULL` key cannot be seeked past, because every comparison
against it is `NULL`, so those rows are excluded by the predicate on every page
after the first and the walk simply ends short with no error.

An earlier revision screened returned rows for NULLs. It was removed rather than
kept, because it was worse than nothing: whether it fired depended entirely on
where the backend sorts NULLs — never on ClickHouse, which sorts them last in
both directions, and on only one of the two directions elsewhere — so it caught
some cases, cost a full row scan per page, rejected legitimate projection
queries, and offered reassurance it could not deliver. Use `NOT NULL` columns.

**Joins work, because the fields are table-qualified.** `DbGrid` binds a keyset
to the Record's table, so `ORDER BY "grid"."id_grid"` and the matching seek
predicate are unambiguous even when the joined side carries the same column
name. Unqualified they would not be — `ORDER BY` resolves against the output
columns while `WHERE` does not, so the query would pass on the first page and
fail on the second.

Driving `Repository.seek()` directly, name the table yourself:

```python
ks = Keyset(Product.id, Keyset.ASC, unique=True, table="product")
```

or call `keyset.qualified("product")`. The keyset must name a column of the
table being paged; joining in a column to sort by is not supported.

### Cursors

A cursor carries the key values of the last row of a page, encoded with their
types, plus an unkeyed checksum of the ordering that produced it. A cursor
presented to a different keyset — different fields, or the same fields in the
other direction — is rejected rather than silently serving a page from the
middle of an unrelated ordering:

```python
cursor = grid.run_seek(limit=10, keyset=Keyset(Product.id, Keyset.ASC, unique=True))[1]
grid.run_seek(limit=10, cursor=cursor, keyset=Keyset(Product.id, Keyset.DESC, unique=True))
# KeysetError: cursor does not belong to this ordering
```

Treat them as tokens to hand back, not as values to construct.

`KeysetError` subclasses `ValueError`, so a handler can catch either. Note it
is not the only thing `run_seek()` raises: a bad `limit` or an unknown field is
a plain `ValueError` (a programmer error, not client input), `Repository.seek()`
raises `RepositoryError`, and a forged cursor carrying a value whose type does
not match the column surfaces as a driver exception. Catch by what you intend to
turn into a 400 rather than by breadth.

**The checksum is an integrity check against client mistakes, not a security
boundary.** It is not keyed, and the payload is base64 rather than encrypted,
so a cursor is readable and a client can mint one for an ordering it knows.
That reaches nothing extra — `match_fields`, `search_text` and any predicate on
the query are still `AND`-ed with the seek — but it does mean a hostile cursor
can carry a value whose type does not match the column, which surfaces as a
backend error rather than a `KeysetError`. Wrap `run_seek()` accordingly if
cursors arrive from untrusted input.

### Repository.seek()

`run_seek()` is built on `Repository.seek()`, which is available directly for
queries that do not go through `DbGrid`:

```python
ks = Keyset(Product.id, Keyset.ASC, unique=True)

cursor = None
while True:
    qry = repo.select().where(Product.active, "=", True)
    rows, has_more = repo.seek(ks.apply(qry, cursor), limit=20)
    process(rows)                      # every page, including the last
    if not has_more:
        break
    cursor = ks.encode(rows[-1])
```

Note the shape: the last page still carries rows, so process them *before*
testing `has_more`. `DbGrid.run_seek()`'s `while cursor is not None` form does
not have this trap, because the final page comes back with a `None` cursor
alongside its rows.

The query is rebuilt inside the loop because `Keyset.apply()` adds its terms in
place; reusing one query object across pages would accumulate an `ORDER BY`
term and a `WHERE` group per page. `DbGrid.run_seek()` copies the query for
you, so this only applies when driving `Repository.seek()` directly.

It fetches one row beyond the limit as a probe and discards it, which is what
makes `has_more` exact. Unlike `Repository.list()`, it issues no `COUNT(*)`.
The query is expected to carry its own ordering and seek predicate — normally
from `Keyset.apply()`.
