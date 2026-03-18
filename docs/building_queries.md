# Building Queries

RickDb's Query Builder can generate SELECT, INSERT, DELETE and UPDATE queries. It also provides schema support (including
cross-schema operations), JOIN support, JSON operations, and recognizes [Record](object_mapper.md) objects for table and schema 
identification.

The query builder provides SQL generation using a fluent interface, suitable for most cases. Different database support
is handled via dialect objects (extending from SqlDialect): `PgSqlDialect` for PostgreSQL, `Sqlite3SqlDialect` for
SQLite, `ClickHouseSqlDialect` for ClickHouse, and `MySqlSqlDialect` for MySQL. The query builder itself will only
generate a SQL string and a parameter value list; it is up to the developer to use the generated SQL in the appropriate
database context.

## Select

Selects are by far the most common statements, and can be easily built using a [Select](classes/select.md) query builder
object. Check the class documentation for more details on all available methods.

Simple Select() examples:

```python
from rick_db.sql import Select, PgSqlDialect

# SELECT ALL
qry, _ = Select(PgSqlDialect()).from_("table").assemble()
# output: SELECT "table".* FROM "table"
print(qry)

# SELECT from 2 tables, with specific columns
qry, _ = (
    Select(PgSqlDialect())
    .from_("table1", ["table1_field"])
    .from_("table2", ["table2_field"])
    .assemble()
)
# output: SELECT "table1_field","table2_field" FROM "table1", "table2"
print(qry)

# SELECT WHERE
qry, values = Select(PgSqlDialect()).from_("table").where("id", "=", 7).assemble()
# output: SELECT "table".* FROM "table" WHERE ("id" = %s)
print(qry)
```

Table aliasing is also supported, as well as schema names:
```python
from rick_db.sql import Select, PgSqlDialect

# SELECT w/ table alias and schema
qry, _ = Select(PgSqlDialect()).from_({'table': 't1'}, schema='data').assemble()
# output: SELECT "t1".* FROM "data"."table" AS "t1"
print(qry)
```

And, of course, columns can be aliased too:
```python
from rick_db.sql import Select, PgSqlDialect

# SELECT w/ column alias
qry, _ = Select(PgSqlDialect()).from_('table', {'id': 'id_table'}).assemble()
# output: SELECT "id" AS "id_table" FROM "table"
print(qry)


# SELECT w/ column alias, and non aliased field
qry, _ = Select(PgSqlDialect()).from_('table', {'id': 'id_table', 'name':None}).assemble()
# output: SELECT "id" AS "id_table","name" FROM "table"
print(qry)

```

The query builder also fully supports [Record](object_mapper.md) classes or objects as table and schema identifiers:

```python
from rick_db import fieldmapper
from rick_db.sql import Select, PgSqlDialect


@fieldmapper(tablename="publisher", pk="id_publisher")
class Publisher:
    id = "id_publisher"
    name = "name"


@fieldmapper(tablename="book", pk="id_book")
class Book:
    id = "id_book"
    title = "title"
    total_pages = "total_pages"
    rating = "rating"
    isbn = "isbn"
    published = "published_date"
    fk_publisher = "fk_publisher"


# simple SELECT
qry, values = Select(PgSqlDialect()).from_(Publisher).assemble()
# output: SELECT "publisher".* FROM "publisher"
print(qry)

# SELECT... WHERE
qry, values = (
    Select(PgSqlDialect())
    .from_(Book, [Book.title, Book.rating])
    .where(Book.id, "=", 5)
    .assemble()
)
# output: SELECT "title","rating" FROM "book" WHERE ("id_book" = %s)
print(qry)

# SELECT... JOIN
qry, values = (
    Select(PgSqlDialect())
    .from_(Book)
    .join(
        Publisher,
        Publisher.id,
        Book,
        Book.fk_publisher,
        cols={Publisher.name: "publisher_name"},
    )
    .assemble()
)
# output: SELECT "book".*,"publisher"."name" AS "publisher_name" FROM "book" INNER JOIN "publisher" ON "book"."fk_publisher"="publisher"."id_publisher"
print(qry)
```

The [Select](classes/select.md) Object also supports both **AND** and **OR** **WHERE** clauses, as well as nested parenthesis:

```python
from rick_db.sql import Select, PgSqlDialect

# SELECT... WHERE <cond> OR <cond>
qry, values = (
    Select(PgSqlDialect())
    .from_(Book)
    .where(Book.title, "ILIKE", "%SQL%")
    .orwhere(Book.rating, ">", 4)
    .assemble()
)
# output: SELECT "book".* FROM "book" WHERE ("title" ILIKE %s) OR ("rating" > %s)
print(qry)


# SELECT... WHERE <cond> OR (<cond> AND <cond>)
qry, values = (
    Select(PgSqlDialect())
    .from_(Book)
    .where(Book.title, "ILIKE", "%SQL%")
    .where_or()
    .where(Book.rating, ">", 4)
    .where(Book.total_pages, ">", 150)
    .where_end()
    .assemble()
)
# output: SELECT "book".* FROM "book" WHERE ("title" ILIKE %s) OR ( ("rating" > %s) AND ("total_pages" > %s) )
print(qry)
```

[Select](classes/select.md) Object supports **LEFT JOIN**, **RIGHT JOIN**, **FULL JOIN**, **CROSS JOIN** and **NATURAL JOIN**:

```python
from rick_db.sql import Select, PgSqlDialect

# INNER JOIN
qry, values = (
    Select(PgSqlDialect())
    .from_("table1")
    .join("table2", "id", "table1", "fk_table2")
    .assemble()
)
# output: SELECT "table1".* FROM "table1" INNER JOIN "table2" ON "table1"."fk_table2"="table2"."id"
print(qry)

# RIGHT JOIN
qry, values = (
    Select(PgSqlDialect())
    .from_("table1")
    .join_right("table2", "id", "table1", "fk_table2")
    .assemble()
)
# output: SELECT "table1".* FROM "table1" RIGHT JOIN "table2" ON "table1"."fk_table2"="table2"."id"
print(qry)

# FULL JOIN
qry, values = (
    Select(PgSqlDialect())
    .from_("table1")
    .join_full("table2", "id", "table1", "fk_table2")
    .assemble()
)
# output: SELECT "table1".* FROM "table1" FULL JOIN "table2" ON "table1"."fk_table2"="table2"."id"
print(qry)

# CROSS JOIN
qry, values = Select(PgSqlDialect()).from_("table1").join_cross("table2").assemble()
# output: SELECT "table1".* FROM "table1" CROSS JOIN "table2"
print(qry)

# NATURAL JOIN
qry, values = Select(PgSqlDialect()).from_("table1").join_natural("table2").assemble()
# output: SELECT "table1".* FROM "table1" NATURAL JOIN "table2"
print(qry)

# mixed example
qry, values = (
    Select(PgSqlDialect())
    .from_("table1")
    .join_right("table2", "id", "table1", "fk_table2")
    .join("table3", "id", "table2", "fk_table3")
    .join("table4", "id", "table3", "fk_table4")
    .assemble()
)
# output: SELECT "table1".* FROM "table1" RIGHT JOIN "table2" ON "table1"."fk_table2"="table2"."id" INNER JOIN "table3" ON "table2"."fk_table3"="table3"."id" INNER JOIN "table4" ON "table3"."fk_table4"="table4"."id"
print(qry)
```

**WHERE IN / NOT IN** with a list of values generates properly parameterized queries:

```python
from rick_db.sql import Select, PgSqlDialect

# WHERE IN with a list
qry, values = Select(PgSqlDialect()).from_("table").where("id", "IN", [1, 2, 3]).assemble()
# output: SELECT "table".* FROM "table" WHERE ("id" IN (%s, %s, %s))
# values: [1, 2, 3]
print(qry)

# WHERE NOT IN with a list
qry, values = Select(PgSqlDialect()).from_("table").where("status", "NOT IN", ["inactive", "deleted"]).assemble()
# output: SELECT "table".* FROM "table" WHERE ("status" NOT IN (%s, %s))
# values: ['inactive', 'deleted']
print(qry)
```

Tuples are also accepted as value lists. An empty list will raise `SqlError`.

It is also possible to use subselects:

```python
from rick_db.sql import Select, PgSqlDialect

subselect = Select(PgSqlDialect()).from_("some_table", ["id"]).where("field", ">", 32)

qry, _ = (
    Select(PgSqlDialect()).from_("table").where("field", "IN", subselect).assemble()
)
# output: SELECT "table".* FROM "table" WHERE ("field" IN (SELECT "id" FROM "some_table" WHERE ("field" > %s)))
print(qry)
```

Also, custom SQL expressions are supported:
```python
from rick_db.sql import Select, PgSqlDialect, Literal

# using a simple expression
qry, _ = Select(PgSqlDialect()).expr([1]).assemble()
# output: SELECT 1
print(qry)

# using a simple expression
qry, _ = Select(PgSqlDialect()).expr([1, 2, 3]).assemble()
# output: SELECT 1,2,3
print(qry)

# using LITERAL
qry, _ = Select(PgSqlDialect()).from_('table', {Literal('COUNT(*)'):'total'}).assemble()
# output: SELECT COUNT(*) AS "total" FROM "table"
print(qry)
```

## SQL Functions

The [Fn](classes/fn.md) class provides helpers for common SQL functions. Each method returns a
[Literal](classes/literal.md), so they work anywhere a Literal is accepted. Use dict-style column definitions
to alias the results:

```python
from rick_db.sql import Select, Fn, PgSqlDialect

# Single aggregate with alias
qry, _ = Select(PgSqlDialect()).from_("orders", {Fn.count(): "total"}).assemble()
# output: SELECT COUNT(*) AS "total" FROM "orders"
print(qry)

# Multiple columns: regular fields and aggregates together
qry, _ = (
    Select(PgSqlDialect())
    .from_("orders", {
        "category": None,
        Fn.count(): "order_count",
        Fn.sum("amount"): "total_amount",
        Fn.avg("amount"): "avg_amount",
    })
    .group("category")
    .assemble()
)
# output: SELECT "category",COUNT(*) AS "order_count",SUM(amount) AS "total_amount",AVG(amount) AS "avg_amount" FROM "orders" GROUP BY "category"
print(qry)

# Nested functions
qry, _ = (
    Select(PgSqlDialect())
    .from_("orders", {
        "category": None,
        Fn.round(Fn.avg("amount"), 2): "avg_rounded",
    })
    .group("category")
    .assemble()
)
# output: SELECT "category",ROUND(AVG(amount), 2) AS "avg_rounded" FROM "orders" GROUP BY "category"
print(qry)

# Multiple aggregates with HAVING
qry, _ = (
    Select(PgSqlDialect())
    .from_("orders", {
        "category": None,
        Fn.count(): "cnt",
        Fn.min("price"): "cheapest",
        Fn.max("price"): "priciest",
        Fn.sum("amount"): "total",
    })
    .group("category")
    .having(Fn.count(), ">", 5)
    .assemble()
)
# output: SELECT "category",COUNT(*) AS "cnt",MIN(price) AS "cheapest",MAX(price) AS "priciest",SUM(amount) AS "total" FROM "orders" GROUP BY "category" HAVING (COUNT(*) > %s)
print(qry)
```

Available functions:

- **Aggregate**: `count`, `sum`, `avg`, `min`, `max`
- **Math**: `abs`, `ceil`, `floor`, `round`, `power`, `sqrt`, `mod`, `sign`, `trunc`
- **General**: `coalesce`, `cast`

See [Fn class documentation](classes/fn.md) for full reference.

## Insert

[Insert](classes/insert.md) objects can be used to generate SQL **INSERT** statements, with optional **RETURNING** clause,
and with full support for [Record](object_mapper.md) objects:

```python
from rick_db.sql import Insert, PgSqlDialect
from rick_db import fieldmapper

@fieldmapper(tablename='publisher', pk='id_publisher')
class Publisher:
    id = 'id_publisher'
    name = 'name'

# simple INSERT example
qry = Insert(PgSqlDialect()).into('table').fields(['field']).values(['value'])
# output: ('INSERT INTO "table" ("field") VALUES (%s)', ['value'])
print(qry.assemble())

# INSERT w/ Record object
record = Publisher(name='some publisher name')
qry = Insert(PgSqlDialect()).into(record)
# output: ('INSERT INTO "publisher" ("name") VALUES (%s)', ['some publisher name'])
print(qry.assemble())
```

It is possible to build an **INSERT** query to perform multiple inserts:

```python
from rick_db.sql import Insert, PgSqlDialect

data = [
    ['john', 'connor'],
    ['sarah', 'connor']
]
sql = []
qry = Insert(PgSqlDialect()).into('table').fields(['name', 'surname'])
for v in data:
    qry.values(v)
    sql.append(qry.assemble())

# output: 
# [('INSERT INTO "table" ("name", "surname") VALUES (%s, %s)', ['john', 'connor']), 
# ('INSERT INTO "table" ("name", "surname") VALUES (%s, %s)', ['sarah', 'connor'])]
print(sql)
```

## Update

[Update](classes/update.md) objects can be used to generate SQL **UPDATE WHERE** statements, with [Record](object_mapper.md)
object support:

```python
from rick_db.sql import Update, PgSqlDialect

@fieldmapper(tablename='publisher', pk='id_publisher')
class Publisher:
    id = 'id_publisher'
    name = 'name'

# simple UPDATE example
qry = Update(PgSqlDialect()).table('table').fields(['field']).values(['value'])
# output: ('UPDATE "table" SET "field"=%s', ['value'])
print(qry.assemble())

# INSERT w/ Record object
record = Publisher(name='some publisher name')
qry = Update(PgSqlDialect()).table('tablename').values(record)
# output: ('UPDATE "tablename" SET "name"=%s', ['some publisher name'])
print(qry.assemble())
```

**WHERE** clause support:
```python
from rick_db.sql import Update, PgSqlDialect

# UPDATE WHERE... common usage
qry = (
    Update(PgSqlDialect()).table("table").values({"field": "value"}).where("id", "=", 7)
)
# output: ('UPDATE "table" SET "field"=%s WHERE "id" = %s', ['value', 7])
print(qry.assemble())

# UPDATE WHERE... no value
qry = (
    Update(PgSqlDialect())
    .table("table")
    .values({"field": "value"})
    .where("id", "IS NOT NULL")
)
# output: ('UPDATE "table" SET "field"=%s WHERE "id" IS NOT NULL', ['value'])
print(qry.assemble())

# UPDATE WHERE... with multiple clauses
qry = (
    Update(PgSqlDialect())
    .table("table")
    .values({"field": "value"})
    .where("id", "=", 7)
    .where("name", "ILIKE", "john%")
)
# output: ('UPDATE "table" SET "field"=%s WHERE "id" = %s AND "name" ILIKE %s', ['value', 7, 'john%'])
print(qry.assemble())

# UPDATE WHERE... IN with a list
qry = (
    Update(PgSqlDialect())
    .table("table")
    .values({"field": "value"})
    .where("id", "IN", [1, 2, 3])
)
# output: ('UPDATE "table" SET "field"=%s WHERE "id" IN (%s, %s, %s)', ['value', 1, 2, 3])
print(qry.assemble())
```

## Delete

[Delete](classes/delete.md) objects can be used to generate SQL **DELETE** statements:


```python
from rick_db.sql import Delete, PgSqlDialect

# DELETE WHERE... common usage
qry = Delete(PgSqlDialect()).from_("table").where("id", "=", 7)
# output: ('DELETE FROM "table" WHERE "id" = %s', [7])
print(qry.assemble())

# DELETE WHERE... no value
qry = Delete(PgSqlDialect()).from_("table").where("id", "IS NOT NULL")
# output: ('DELETE FROM "table" WHERE "id" IS NOT NULL', [])
print(qry.assemble())

# DELETE WHERE... with multiple clauses
qry = (
    Delete(PgSqlDialect())
    .from_("table")
    .where("id", "=", 7)
    .where("name", "ILIKE", "john%")
)
# output: ('DELETE FROM "table" WHERE "id" = %s AND "name" ILIKE %s', [7, 'john%'])
print(qry.assemble())

# DELETE WHERE... IN with a list
qry = Delete(PgSqlDialect()).from_("table").where("id", "IN", [1, 2, 3])
# output: ('DELETE FROM "table" WHERE "id" IN (%s, %s, %s)', [1, 2, 3])
print(qry.assemble())
```


## JSON Operations

The Query Builder provides comprehensive support for working with JSON data through the `JsonField` and `PgJsonField` classes and specialized helper methods on the `Select` class. For detailed information, see the [JSON Operations](json_operations.md) documentation.

Basic JSON query example:

```python
from rick_db.sql import Select, PgJsonField
from rick_db.sql.dialect import PgSqlDialect

# Create a PostgreSQL dialect
pg_dialect = PgSqlDialect()

# Using JsonField directly
json_field = PgJsonField("user_data", pg_dialect)

# Extract values from JSON
query = (
    Select(pg_dialect)
    .from_("users")
    .where(json_field.extract("$.name"), "=", "John")
    .where(json_field.extract("$.active"), "=", True)
)

# Using helper methods
query = (
    Select(pg_dialect)
    .from_("users")
    .json_extract("user_data", "$.name", "user_name")
    .json_where("user_data", "$.active", "=", True)
)

# Using bracket notation (PostgreSQL)
query = (
    Select(pg_dialect)
    .from_("users")
    .where(json_field["address"]["city"], "=", "New York")
)
```

## With

[With](classes/with.md) objects can be used to generate CTE statements:


```python
from rick_db import fieldmapper
from rick_db.sql import Select, PgSqlDialect, With, Sql

@fieldmapper(tablename="folder", pk="id_folder")
class FolderRecord:
    id = "id_folder"
    parent = "fk_parent"


dialect = PgSqlDialect()

union = Select(dialect).union(
    [
        Select(dialect).from_({FolderRecord: "f1"}).where(FolderRecord.id, "=", 19),
        Select(dialect)
        .from_({FolderRecord: "f2"})
        .join("folder_tree", FolderRecord.parent, "f2", FolderRecord.id),
    ],
    Sql.SQL_UNION_ALL,
)

qry = (
    With()
    .clause("folder_tree", union)
    .query(Select(dialect).from_("folder_tree"))
    .recursive()
)

# output:
# ('WITH RECURSIVE "folder_tree" AS (
#   SELECT "f1".* FROM "folder" AS "f1" WHERE ("id_folder" = %s)
#   UNION ALL
#   SELECT "f2".* FROM "folder" AS "f2" INNER JOIN "folder_tree" ON "f2"."id_folder"="folder_tree"."fk_parent"
#   ) SELECT "folder_tree".* FROM "folder_tree"', [19])
print(qry.assemble())
```
