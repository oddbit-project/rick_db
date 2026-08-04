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
```

Two rules the API enforces rather than documents:

**Every field sorts in the same direction.** A keyset ordered
`(a ASC, b DESC)` cannot be expressed as a seek predicate at all, so the
direction is a single parameter rather than a per-field one.

**A unique tiebreaker is required.** Seeking on a non-unique column alone
silently skips or repeats rows whenever two of them share a value at a page
boundary. Pass `pk=` and it is appended automatically when absent.

Keyset fields must be non-nullable and orderable scalars (integer, string,
date/time, decimal, UUID). A `NULL` key cannot be seeked past — every
comparison against it is `NULL` — so `Keyset` refuses to build a cursor from
one.

### Cursors

Cursors are opaque. They carry the key values of the last row of a page,
encoded with their types, plus a signature of the ordering that produced them.
A cursor presented to a different keyset — different fields, or the same fields
in the other direction — is rejected rather than silently serving a page from
the middle of an unrelated ordering:

```python
cursor = grid.run_seek(limit=10, keyset=Keyset(Product.id, Keyset.ASC))[1]
grid.run_seek(limit=10, cursor=cursor, keyset=Keyset(Product.id, Keyset.DESC))
# KeysetError: cursor does not belong to this ordering
```

Treat them as tokens to hand back, not as values to construct.

### Repository.seek()

`run_seek()` is built on `Repository.seek()`, which is available directly for
queries that do not go through `DbGrid`:

```python
qry = repo.select().where(Product.active, "=", True).order(Product.id, "ASC")
rows, has_more = repo.seek(qry, limit=20)
```

It fetches one row beyond the limit as a probe and discards it, which is what
makes `has_more` exact. Unlike `Repository.list()`, it issues no `COUNT(*)`.
The query is expected to carry its own ordering and seek predicate — normally
from `Keyset.apply()`.
