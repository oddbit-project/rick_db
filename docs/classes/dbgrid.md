# Class rick_db.sql.**DbGrid**

### Const DbGrid.**SEARCH_NONE**
No search to be done.

### Const DbGrid.**SEARCH_ANY**
Find matches with a different start or ending.

### Const DbGrid.**SEARCH_START**
Find matches tha start with the expression.

### Const DbGrid.**SEARCH_END**
Find matches tha end with the expression.

### DbGrid.**\_\_init\_\_(repo: Repository, search_fields: list = None, search_type: int = None, case_sensitive=False)**

Initialize a DbGrid() object, using the [Repository](repository.md) *repo*, a list of field names to be searched in *search_fields*,
with the search type *search_type* (see [SEARCH_NONE](#const-dbgridsearch_none), [SEARCH_ANY](#const-dbgridsearch_any), 
[SEARCH_START](#const-dbgridsearch_start), [SEARCH_END](#const-dbgridsearch_end)), and if *case_sensitive* is True,
a case-sensitive search is performed.

### DbGrid.**default_query()**:

Build and returns the Select() object to be used internally for DbGrid. This method can be overridden for specific implementations.

### DbGrid.**default_sort()**:

Build and returns the default sort dictionary. It can be overridden for specific implementations.

### DbGrid.**run(qry: Select = None, search_text: str = None, match_fields: dict = None, limit: int = None, offset: int = None, sort_fields: dict = None, search_fields: list = None)**:

Executes a query and returns a tuple with the total row count matching the query, and the records within the specified range 
defined by *offset* and *limit*, sorted by *sort_fields*.

If *qry* is None, [DbGrid.default_query()](#dbgriddefault_query) is used. If *search_text* is specified, a **LIKE/ILIKE**
search is performed in the searchable fields defined in the constructor. Specific search fields can be specified, within
the set of fields specified in the constructor. *match_fields* is an optional {field_name:value} dict to perform exact 
match (field=value).

Example:
```python
from rick_db import fieldmapper, Repository, DbGrid
from rick_db.conn.pg import PgConnection


@fieldmapper(tablename="product", pk="id_product")
class Product:
    id = "id_product"
    short_description = "short_description"
    brand = "brand_id"


db_config = {
    "dbname": "products",
    "user": "someUser",
    "password": "somePassword",
    "host": "localhost",
    "port": 5432,
}

# create connection
conn = PgConnection(**db_config)

# create a repository
repo = Repository(conn, Product)

# create a grid
grid = DbGrid(
    repo,  # repository to use
    [Product.short_description],  # fields to perform text search
    DbGrid.SEARCH_ANY,  # type of search
)

# retrieve first 10 results
# total will have the total row count that matches the filters, without limit
total, rows = grid.run(search_text="bag", match_fields={Product.brand: 12}, limit=10)
print("total matches:", total)
for r in rows:
    print(r.id, r.short_description)

# retrieve second page of results
total, rows = grid.run(
    search_text="bag", match_fields={Product.brand: 12}, limit=10, offset=10
)
for r in rows:
    print(r.id, r.short_description)
```