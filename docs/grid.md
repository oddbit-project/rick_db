# DbGrid

[DbGrid](classes/dbgrid.md) is a helper class to aid the creation of table-like listings(grids). It provides a clean,
programmatic way of searching a given database object (or use a custom query) with string search, exact matching and
pagination. 

It returns the total row count (without applying pagination), and the filtered row subset matching the pagination results.

Example:

```python
from rick_db import fieldmapper, Repository, DbGrid
from rick_db.conn.pg import PgConnection


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
conn = PgConnection(**db_config)

# create a repository
repo = Repository(conn, Product)

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

### Limitations:

**Sqlite3**

On Sqlite3, case-insensitive search is done via UPPER(), since no ILIKE equivalent is available. 
This is may trigger a full table scan and will not use indexes if they are available for the specific field. Additionally,
this method only works with ASCII chars. 

It its therefore recommended to avoid the usage of case-sensitive search with this driver.

As an option, one can instead use COLLATE NOCASE on the creation of the required fields, and use DbGrid with case_sensitive=True.
This way, search will be case insensitive on the fields created with the COLLATE NOCASE option.  

