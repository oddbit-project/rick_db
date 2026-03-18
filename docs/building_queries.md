# Building Queries

RickDb's Query Builder can generate SELECT, INSERT, DELETE and UPDATE queries. It also provides schema support (including
cross-schema operations), JOIN support, JSON operations, and recognizes [Record](object_mapper.md) objects for table and schema
identification.

The query builder provides SQL generation using a fluent interface, suitable for most cases. Different database support
is handled via dialect objects (extending from SqlDialect): `PgSqlDialect` for PostgreSQL, `Sqlite3SqlDialect` for
SQLite, `ClickHouseSqlDialect` for ClickHouse, and `MySqlSqlDialect` for MySQL. The query builder itself will only
generate a SQL string and a parameter value list; it is up to the developer to use the generated SQL in the appropriate
database context.

All scalar values passed to `where()`, `values()`, etc. become parameterized placeholders in the generated SQL — they
are never interpolated into the query string directly. The `.assemble()` method returns a `(sql, values)` tuple that
can be passed directly to a database cursor.

## Table of Contents

- [Select](#select)
  - [Basic queries and column selection](#basic-queries-and-column-selection)
  - [Table aliases and schemas](#table-aliases-and-schemas)
  - [Column aliases](#column-aliases)
  - [Column type casting](#column-type-casting)
  - [Using Record objects](#using-record-objects)
  - [WHERE conditions](#where-conditions)
  - [AND / OR WHERE](#and-or-where)
  - [Grouped WHERE with parentheses](#grouped-where-with-parentheses)
  - [WHERE IN / NOT IN](#where-in-not-in)
  - [WHERE with subqueries](#where-with-subqueries)
  - [WHERE with cross-table field comparison](#where-with-cross-table-field-comparison)
  - [Literal expressions](#literal-expressions)
  - [Anonymous expressions (no FROM)](#anonymous-expressions-no-from)
  - [DISTINCT](#distinct)
  - [ORDER BY, LIMIT, and pagination](#order-by-limit-and-pagination)
  - [FOR UPDATE](#for-update)
  - [UNION](#union)
  - [JOINs](#joins)
  - [GROUP BY and HAVING](#group-by-and-having)
- [SQL Functions (Fn)](#sql-functions)
- [Insert](#insert)
- [Update](#update)
- [Delete](#delete)
- [JSON Operations](#json-operations)
- [WITH (Common Table Expressions)](#with)


## Select

Selects are by far the most common statements, and can be easily built using a [Select](classes/select.md) query builder
object. Check the class documentation for more details on all available methods.

### Basic queries and column selection

The `from_(table, cols=None, schema=None)` method sets the source table and optionally selects specific columns.

The `table` argument accepts:
- A **string** table name
- A **dict** `{table: alias}` for table aliasing
- A **fieldmapper class or instance** (extracts the table name automatically)
- A **Select** object (subquery)
- A **Literal** for raw SQL expressions

The `cols` argument controls which columns are selected:
- **None** (default) — selects all columns (`*`)
- A **list** — selects the specified columns
- A **dict** — selects columns with aliases (see [Column aliases](#column-aliases))

You can call `from_()` multiple times to select from multiple tables.

```python
from rick_db.sql import Select, PgSqlDialect

# SELECT ALL
qry, _ = Select(PgSqlDialect()).from_("table").assemble()
# output: SELECT "table".* FROM "table"
print(qry)

# SELECT specific columns
qry, _ = Select(PgSqlDialect()).from_("table", ["id", "name", "email"]).assemble()
# output: SELECT "id","name","email" FROM "table"
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
```

### Table aliases and schemas

Pass a dict as the `table` argument to alias the table. The `schema` parameter qualifies the table with a schema name.

```python
from rick_db.sql import Select, PgSqlDialect

# SELECT w/ table alias and schema
qry, _ = Select(PgSqlDialect()).from_({'table': 't1'}, schema='data').assemble()
# output: SELECT "t1".* FROM "data"."table" AS "t1"
print(qry)

# Table alias without schema
qry, _ = Select(PgSqlDialect()).from_({'users': 'u'}, ['name', 'email']).assemble()
# output: SELECT "name","email" FROM "users" AS "u"
print(qry)
```

### Column aliases

Pass a **dict** as the `cols` argument to alias columns. Dict keys are field names (or `Fn`/`Literal` expressions),
and values control the alias:

- **`None`** — no alias, include the column as-is
- **`"alias_name"`** — adds `AS "alias_name"` to the column

```python
from rick_db.sql import Select, PgSqlDialect

# SELECT w/ column alias
qry, _ = Select(PgSqlDialect()).from_('table', {'id': 'id_table'}).assemble()
# output: SELECT "id" AS "id_table" FROM "table"
print(qry)

# SELECT w/ column alias, and non-aliased field
qry, _ = Select(PgSqlDialect()).from_('table', {'id': 'id_table', 'name': None}).assemble()
# output: SELECT "id" AS "id_table","name" FROM "table"
print(qry)

# Aliasing with Literal expressions
from rick_db.sql import Literal

qry, _ = Select(PgSqlDialect()).from_('table', {Literal('COUNT(*)'): 'total', 'name': None}).assemble()
# output: SELECT COUNT(*) AS "total","name" FROM "table"
print(qry)
```

### Column type casting

Column alias values can also be a **list** to apply type casting:

- **`["cast_type"]`** — casts the column (PostgreSQL uses `::`, other dialects use `CAST()`)
- **`["cast_type", "alias_name"]`** — cast + alias

```python
from rick_db.sql import Select, PgSqlDialect

# Cast only (no alias)
qry, _ = Select(PgSqlDialect()).from_('table', {'id': ['int']}).assemble()
# output (PG): SELECT "id"::int FROM "table"
print(qry)

# Cast with alias
qry, _ = Select(PgSqlDialect()).from_('table', {'id': ['int'], 'name': ['varchar', 'user_name']}).assemble()
# output (PG): SELECT "id"::int,"name"::varchar AS "user_name" FROM "table"
print(qry)
```

### Using Record objects

The query builder fully supports [Record](object_mapper.md) classes or objects as table and schema identifiers.
When a fieldmapper class or instance is passed as the `table` argument, the builder automatically extracts the
table name and schema. Field attributes from the class can be used directly in column lists, `where()` calls,
`join()` calls, etc. — the builder resolves them to the actual database column names.

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


# simple SELECT — table name extracted from the class
qry, values = Select(PgSqlDialect()).from_(Publisher).assemble()
# output: SELECT "publisher".* FROM "publisher"
print(qry)

# SELECT with specific columns — using class attributes as column references
qry, values = (
    Select(PgSqlDialect())
    .from_(Book, [Book.title, Book.rating])
    .where(Book.id, "=", 5)
    .assemble()
)
# output: SELECT "title","rating" FROM "book" WHERE ("id_book" = %s)
print(qry)

# SELECT with JOIN — Record classes used for both tables and field references
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

### WHERE conditions

The `where(field, operator=None, value=None)` method adds a condition to the WHERE clause.

**Parameters:**

- **`field`** — the column to filter on. Accepts a string, a fieldmapper attribute, a dict `{table: field}` for
  table-qualified references, or a `Literal` for raw SQL expressions.
- **`operator`** — any SQL comparison operator as a string: `=`, `!=`, `<>`, `>`, `<`, `>=`, `<=`, `LIKE`, `ILIKE`
  (PostgreSQL only), `IS NULL`, `IS NOT NULL`, `IN`, `NOT IN`, etc.
- **`value`** — the value to compare against. Accepts a scalar (parameterized), a list (for `IN`/`NOT IN`),
  a `Select` subquery, a dict `{table: field}` for cross-table comparison, or a `Literal`. For unary operators
  like `IS NULL` / `IS NOT NULL`, omit the value.

Each scalar value becomes a parameterized placeholder in the generated SQL. Multiple `where()` calls are joined
with `AND` (see [AND / OR WHERE](#and--or-where) for alternatives).

```python
from rick_db.sql import Select, PgSqlDialect

# Equality
qry, values = Select(PgSqlDialect()).from_("table").where("id", "=", 7).assemble()
# output: SELECT "table".* FROM "table" WHERE ("id" = %s)
# values: [7]
print(qry)

# Comparison operators
qry, values = Select(PgSqlDialect()).from_("table").where("price", ">=", 100).assemble()
# output: SELECT "table".* FROM "table" WHERE ("price" >= %s)
print(qry)

# IS NULL / IS NOT NULL — no value argument needed
qry, values = Select(PgSqlDialect()).from_("table").where("email", "IS NULL").assemble()
# output: SELECT "table".* FROM "table" WHERE ("email" IS NULL)
print(qry)

qry, values = Select(PgSqlDialect()).from_("table").where("email", "IS NOT NULL").assemble()
# output: SELECT "table".* FROM "table" WHERE ("email" IS NOT NULL)
print(qry)

# LIKE / ILIKE (ILIKE is PostgreSQL only; SQLite does not support it)
qry, values = Select(PgSqlDialect()).from_("table").where("name", "LIKE", "%alice%").assemble()
# output: SELECT "table".* FROM "table" WHERE ("name" LIKE %s)
print(qry)

qry, values = Select(PgSqlDialect()).from_("table").where("name", "ILIKE", "%alice%").assemble()
# output: SELECT "table".* FROM "table" WHERE ("name" ILIKE %s)
print(qry)
```

### AND / OR WHERE

Multiple `where()` calls on the same query are concatenated with `AND`. Use `orwhere()` to join with `OR` instead.
Both methods accept the same parameters. The first condition in a chain has no conjunction prefix — the conjunction
only appears between conditions.

```python
from rick_db.sql import Select, PgSqlDialect

# Multiple where() calls produce AND
qry, values = (
    Select(PgSqlDialect())
    .from_("users")
    .where("active", "=", True)
    .where("name", "LIKE", "A%")
    .assemble()
)
# output: SELECT "users".* FROM "users" WHERE ("active" = %s) AND ("name" LIKE %s)
print(qry)

# orwhere() produces OR
qry, values = (
    Select(PgSqlDialect())
    .from_(Book)
    .where(Book.title, "ILIKE", "%SQL%")
    .orwhere(Book.rating, ">", 4)
    .assemble()
)
# output: SELECT "book".* FROM "book" WHERE ("title" ILIKE %s) OR ("rating" > %s)
print(qry)
```

### Grouped WHERE with parentheses

For complex boolean logic, use `where_and()` or `where_or()` to open a parenthesized group, and `where_end()`
to close it:

- **`where_and()`** — opens a group where inner conditions are joined by `AND`
- **`where_or()`** — opens a group where inner conditions are joined by `OR`
- **`where_end()`** — closes the most recent group

Groups can be nested. The builder tracks open/close balance and raises an error if you call `.assemble()`
on a query with unclosed groups.

```python
from rick_db.sql import Select, PgSqlDialect

# WHERE <cond> OR (<cond> AND <cond>)
# "find books about SQL, or books that are both highly rated AND long"
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

# WHERE (<cond> AND <cond>) OR <cond>
# "find active admins, or anyone with a specific email"
qry, values = (
    Select(PgSqlDialect())
    .from_("users")
    .where_and()
    .where("role", "=", "admin")
    .where("active", "=", True)
    .where_end()
    .orwhere("email", "=", "superuser@example.com")
    .assemble()
)
# output: SELECT "users".* FROM "users" WHERE ( ("role" = %s) AND ("active" = %s) ) OR ("email" = %s)
print(qry)

# Nested groups: WHERE <cond> AND (<cond> OR <cond>)
qry, values = (
    Select(PgSqlDialect())
    .from_("users")
    .where("active", "=", True)
    .where_or()
    .where("role", "=", "admin")
    .where("role", "=", "moderator")
    .where_end()
    .assemble()
)
# output: SELECT "users".* FROM "users" WHERE ("active" = %s) AND ( ("role" = %s) OR ("role" = %s) )
print(qry)
```

### WHERE IN / NOT IN

When the `value` argument to `where()` is a **list** or **tuple**, the builder generates `IN` or `NOT IN` with
properly parameterized placeholders — one placeholder per element. An empty list will raise `SqlError`.

The operator is case-insensitive (`"IN"`, `"in"`, `"In"` all work).

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

Tuples are also accepted as value lists.

### WHERE with subqueries

A `Select` object can be passed as the `value` argument to `where()`, generating a subquery. The subquery's
parameters are automatically merged into the outer query's parameter list. This is commonly used with `IN` / `NOT IN`.

```python
from rick_db.sql import Select, PgSqlDialect

# Subquery in WHERE IN
subselect = Select(PgSqlDialect()).from_("some_table", ["id"]).where("field", ">", 32)

qry, _ = (
    Select(PgSqlDialect()).from_("table").where("field", "IN", subselect).assemble()
)
# output: SELECT "table".* FROM "table" WHERE ("field" IN (SELECT "id" FROM "some_table" WHERE ("field" > %s)))
print(qry)
```

### WHERE with cross-table field comparison

Pass a **dict** `{table_name: field_name}` as the `value` argument to compare a field against a column from another
table. The dict value is emitted as a table-qualified field reference rather than a parameterized placeholder.

```python
from rick_db.sql import Select, PgSqlDialect

# Compare fields across tables
qry, _ = (
    Select(PgSqlDialect())
    .from_("orders")
    .join("users", "id", "orders", "user_id")
    .where("orders_total", ">", {"users": "credit_limit"})
    .assemble()
)
# WHERE "orders_total" > "users"."credit_limit"
print(qry)
```

### Literal expressions

The `Literal` class (also importable as `L`) wraps a raw SQL string that is emitted as-is into the generated
query — no quoting, no parameterization. Use it for SQL expressions, function calls, or any fragment the builder
can't construct natively.

`Literal` can be used anywhere a field name, table name, column, or value is accepted.

```python
from rick_db.sql import Select, PgSqlDialect, Literal

# Literal as a column expression
qry, _ = Select(PgSqlDialect()).from_('table', {Literal('COUNT(*)'): 'total'}).assemble()
# output: SELECT COUNT(*) AS "total" FROM "table"
print(qry)

# Literal in a WHERE clause (as the field)
qry, _ = Select(PgSqlDialect()).from_("users").where(Literal("LENGTH(name)"), ">", 5).assemble()
# output: SELECT "users".* FROM "users" WHERE (LENGTH(name) > %s)
print(qry)

# Literal as a table source
qry, _ = Select(PgSqlDialect()).from_(Literal("generate_series(1, 10) AS n")).assemble()
# output: SELECT * FROM generate_series(1, 10) AS n
print(qry)
```

### Anonymous expressions (no FROM)

The `expr(cols)` method generates a SELECT without a FROM clause — useful for computed values, database functions,
or existence checks.

```python
from rick_db.sql import Select, PgSqlDialect, Literal

# Simple expression
qry, _ = Select(PgSqlDialect()).expr([1]).assemble()
# output: SELECT 1
print(qry)

# Multiple values
qry, _ = Select(PgSqlDialect()).expr([1, 2, 3]).assemble()
# output: SELECT 1,2,3
print(qry)

# With Literal
qry, _ = Select(PgSqlDialect()).expr(Literal("NOW()")).assemble()
# output: SELECT NOW()
print(qry)
```

### DISTINCT

The `distinct()` method adds the `DISTINCT` keyword to eliminate duplicate rows from the result set.

```python
from rick_db.sql import Select, PgSqlDialect

qry, _ = Select(PgSqlDialect()).from_("users", ["name"]).distinct().assemble()
# output: SELECT DISTINCT "name" FROM "users"
print(qry)
```

### ORDER BY, LIMIT, and pagination

**`order(fields, order=ASC)`** adds an ORDER BY clause. It accepts:
- A **string** — single field, direction set by the `order` parameter
- A **list** — multiple fields, all with the same direction
- A **dict** `{field: "ASC"|"DESC"}` — multiple fields with individual directions
- A **Literal** — raw SQL expression

**`limit(limit, offset=None)`** sets LIMIT and optionally OFFSET directly.

**`page(page_number, rows_per_page)`** is a convenience method that calculates the offset from a 0-indexed
page number: `offset = page_number * rows_per_page`.

```python
from rick_db.sql import Select, PgSqlDialect

# ORDER BY single field (default ASC)
qry, _ = Select(PgSqlDialect()).from_("users").order("name").assemble()
# output: SELECT "users".* FROM "users" ORDER BY "name" ASC
print(qry)

# ORDER BY DESC
qry, _ = Select(PgSqlDialect()).from_("users").order("name", Select.ORDER_DESC).assemble()
# output: SELECT "users".* FROM "users" ORDER BY "name" DESC
print(qry)

# ORDER BY multiple fields with mixed directions
qry, _ = Select(PgSqlDialect()).from_("users").order({"name": "ASC", "id": "DESC"}).assemble()
# output: SELECT "users".* FROM "users" ORDER BY "name" ASC,"id" DESC
print(qry)

# LIMIT and OFFSET
qry, _ = Select(PgSqlDialect()).from_("users").order("id").limit(10, offset=20).assemble()
# output: SELECT "users".* FROM "users" ORDER BY "id" ASC LIMIT 10 OFFSET 20
print(qry)

# Page helper (page 3 with 10 rows per page = offset 20, limit 10)
# Pages are 0-indexed, so page(0, 10) is the first page
qry, _ = Select(PgSqlDialect()).from_("users").order("id").page(2, 10).assemble()
# output: SELECT "users".* FROM "users" ORDER BY "id" ASC LIMIT 10 OFFSET 20
print(qry)
```

### FOR UPDATE

The `for_update()` method appends `FOR UPDATE` to the query, enabling row-level locking within a transaction.
This is useful for pessimistic concurrency control.

```python
from rick_db.sql import Select, PgSqlDialect

qry, _ = Select(PgSqlDialect()).from_("users").where("id", "=", 1).for_update().assemble()
# output: SELECT "users".* FROM "users" WHERE ("id" = %s) FOR UPDATE
print(qry)
```

### UNION

The `union(queries, union_type=UNION)` method combines the result sets of multiple SELECT queries.

- **`queries`** — a list of `Select` objects or raw SQL strings
- **`union_type`** — `Select.UNION` (default, deduplicates rows) or `Select.UNION_ALL` (keeps all rows including duplicates)

```python
from rick_db.sql import Select, PgSqlDialect

dialect = PgSqlDialect()

q1 = Select(dialect).from_("users", ["name"]).where("active", "=", True)
q2 = Select(dialect).from_("users", ["name"]).where("role", "=", "admin")

# UNION (deduplicated)
qry, values = Select(dialect).union([q1, q2]).assemble()
print(qry)

# UNION ALL (keep duplicates)
qry, values = Select(dialect).union([q1, q2], Select.UNION_ALL).assemble()
print(qry)
```

### JOINs

The [Select](classes/select.md) builder supports all standard SQL join types. All join methods (except cross and
natural) follow the same signature:

```
join_*(table, field, expr_table, expr_field, operator=None, cols=None, schema=None, expr_schema=None)
```

**Parameters:**

- **`table`** — the table to join (string, fieldmapper class, or object)
- **`field`** — the join column on the joined table
- **`expr_table`** — the table being joined against (typically the table already in the query)
- **`expr_field`** — the join column on the existing table
- **`operator`** — the join comparison operator (defaults to `=`)
- **`cols`** — columns to select from the joined table (list or dict for aliases; `None` selects nothing from
  the joined table beyond what `from_()` already selected)
- **`schema`** / **`expr_schema`** — schema qualifiers for each side of the join

**Available join methods:**

| Method | SQL |
|--------|-----|
| `join()` / `join_inner()` | `INNER JOIN` |
| `join_left()` | `LEFT JOIN` |
| `join_right()` | `RIGHT JOIN` |
| `join_full()` | `FULL JOIN` |
| `join_cross(table, cols, schema)` | `CROSS JOIN` (no ON clause) |
| `join_natural(table, cols, schema)` | `NATURAL JOIN` (no ON clause) |
| `join_inner_lateral(subquery, alias, join_expr)` | `INNER JOIN LATERAL` (PostgreSQL) |
| `join_left_lateral(subquery, alias, join_expr)` | `LEFT JOIN LATERAL` (PostgreSQL) |

```python
from rick_db.sql import Select, PgSqlDialect

# INNER JOIN — join() is an alias for join_inner()
qry, values = (
    Select(PgSqlDialect())
    .from_("table1")
    .join("table2", "id", "table1", "fk_table2")
    .assemble()
)
# output: SELECT "table1".* FROM "table1" INNER JOIN "table2" ON "table1"."fk_table2"="table2"."id"
print(qry)

# JOIN with columns from the joined table
qry, values = (
    Select(PgSqlDialect())
    .from_(Book, [Book.title])
    .join(
        Publisher,
        Publisher.id,
        Book,
        Book.fk_publisher,
        cols={Publisher.name: "publisher_name"},
    )
    .assemble()
)
# output: SELECT "title","publisher"."name" AS "publisher_name" FROM "book" INNER JOIN "publisher" ON "book"."fk_publisher"="publisher"."id_publisher"
print(qry)

# LEFT JOIN
qry, values = (
    Select(PgSqlDialect())
    .from_("table1")
    .join_left("table2", "id", "table1", "fk_table2")
    .assemble()
)
# output: SELECT "table1".* FROM "table1" LEFT JOIN "table2" ON "table1"."fk_table2"="table2"."id"
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

# CROSS JOIN — no ON clause needed
qry, values = Select(PgSqlDialect()).from_("table1").join_cross("table2").assemble()
# output: SELECT "table1".* FROM "table1" CROSS JOIN "table2"
print(qry)

# NATURAL JOIN — no ON clause needed
qry, values = Select(PgSqlDialect()).from_("table1").join_natural("table2").assemble()
# output: SELECT "table1".* FROM "table1" NATURAL JOIN "table2"
print(qry)

# Chaining multiple joins
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

**LATERAL JOINs** (PostgreSQL only) take a subquery, an alias, and a `Literal` for the ON condition:

```python
from rick_db.sql import Select, PgSqlDialect, Literal

dialect = PgSqlDialect()
subquery = Select(dialect).from_("orders", ["total"]).where("user_id", "=", Literal('"users"."id"'))

qry, _ = (
    Select(dialect)
    .from_("users")
    .join_inner_lateral(subquery, "recent_orders", Literal("true"))
    .assemble()
)
print(qry)
```

### GROUP BY and HAVING

**`group(fields)`** adds a GROUP BY clause. Accepts a single field name, a `Literal`, or a list of fields/Literals.
The builder detects duplicate group fields and raises an error.

**`having(field, operator, value)`** filters grouped results. It has the same signature as `where()`. Multiple
`having()` calls are joined with AND.

```python
from rick_db.sql import Select, Fn, PgSqlDialect

# Basic GROUP BY with aggregate
qry, _ = (
    Select(PgSqlDialect())
    .from_("orders", {"category": None, Fn.count(): "total"})
    .group("category")
    .assemble()
)
# output: SELECT "category",COUNT(*) AS "total" FROM "orders" GROUP BY "category"
print(qry)

# GROUP BY with HAVING
qry, _ = (
    Select(PgSqlDialect())
    .from_("orders", {"category": None, Fn.count(): "cnt"})
    .group("category")
    .having(Fn.count(), ">", 5)
    .assemble()
)
# output: SELECT "category",COUNT(*) AS "cnt" FROM "orders" GROUP BY "category" HAVING (COUNT(*) > %s)
print(qry)

# Multiple group fields
qry, _ = (
    Select(PgSqlDialect())
    .from_("orders", {"category": None, "status": None, Fn.sum("amount"): "total"})
    .group(["category", "status"])
    .assemble()
)
print(qry)
```


## SQL Functions

The [Fn](classes/fn.md) class provides helpers for common SQL functions. Each static method returns a
[Literal](classes/literal.md), so they work anywhere a `Literal` is accepted — as column expressions, in `where()`,
in `having()`, in dict-style column aliases, etc.

Since `Fn` methods return `Literal` instances, they can be **nested**: pass one `Fn` call as the argument to another
to compose complex expressions like `ROUND(AVG(price), 2)`.

**Available functions:**

| Category | Functions |
|----------|-----------|
| **Aggregate** | `count(field="*")`, `sum(field)`, `avg(field)`, `min(field)`, `max(field)` |
| **Math** | `abs(field)`, `ceil(field)`, `floor(field)`, `round(field, decimals=None)`, `power(field, exponent)`, `sqrt(field)`, `mod(field, divisor)`, `sign(field)`, `trunc(field, decimals=None)` |
| **General** | `coalesce(*fields)`, `cast(field, type_name)` |

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

# Nested functions: ROUND(AVG(amount), 2)
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

See [Fn class documentation](classes/fn.md) for full reference.

## Insert

[Insert](classes/insert.md) objects generate SQL **INSERT** statements. There are several ways to specify what to insert:

1. **From a fieldmapper instance** — pass an instance to `into()` and it extracts fields and values automatically
2. **Explicit fields and values** — call `into(table)` with a class/string, then `fields()` and `values()` separately
3. **From a dict** — call `values()` with a dict where keys become field names

The optional `returning(fields)` method adds a RETURNING clause (supported by PostgreSQL and SQLite 3.35+).

```python
from rick_db.sql import Insert, PgSqlDialect
from rick_db import fieldmapper

@fieldmapper(tablename='publisher', pk='id_publisher')
class Publisher:
    id = 'id_publisher'
    name = 'name'

# 1. INSERT from a fieldmapper instance
record = Publisher(name='some publisher name')
qry = Insert(PgSqlDialect()).into(record)
# output: ('INSERT INTO "publisher" ("name") VALUES (%s)', ['some publisher name'])
print(qry.assemble())

# 2. INSERT with explicit fields and values
qry = Insert(PgSqlDialect()).into('table').fields(['name', 'email']).values(['Alice', 'alice@test.com'])
# output: ('INSERT INTO "table" ("name", "email") VALUES (%s, %s)', ['Alice', 'alice@test.com'])
print(qry.assemble())

# 3. INSERT from a dict
qry = Insert(PgSqlDialect()).into('table').values({'name': 'Alice', 'email': 'alice@test.com'})
# output: ('INSERT INTO "table" ("name", "email") VALUES (%s, %s)', ['Alice', 'alice@test.com'])
print(qry.assemble())

# INSERT with RETURNING
qry = Insert(PgSqlDialect()).into(record).returning([Publisher.id])
# output: ('INSERT INTO "publisher" ("name") VALUES (%s) RETURNING "id_publisher"', ['some publisher name'])
print(qry.assemble())
```

To build multiple INSERT statements, reuse the builder and call `values()` with new data for each row:

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

[Update](classes/update.md) objects generate SQL **UPDATE** statements. The `table()` method sets the target:

- If passed a **fieldmapper instance**, it extracts fields, values, and automatically adds a WHERE clause on the
  primary key.
- If passed a **fieldmapper class** or **string**, you must provide values and WHERE conditions manually.

The `values()` method accepts a dict of `{field: value}` pairs where values can be:
- **Scalars** — parameterized as placeholders
- **`Literal` expressions** — emitted as raw SQL (e.g. for incrementing: `Literal('"counter" + 1')`)
- **`Select` subqueries** — embedded as subselects

`where()` and `orwhere()` work identically to Select's WHERE methods, including IN/NOT IN with lists and subqueries.
The optional `returning(fields)` method adds a RETURNING clause (PostgreSQL).

```python
from rick_db.sql import Update, PgSqlDialect
from rick_db import fieldmapper

@fieldmapper(tablename='publisher', pk='id_publisher')
class Publisher:
    id = 'id_publisher'
    name = 'name'

# UPDATE from a fieldmapper instance — WHERE on pk is automatic
record = Publisher(name='some publisher name')
record.id_publisher = 5
qry = Update(PgSqlDialect()).table(record)
# output: ('UPDATE "publisher" SET "name"=%s WHERE "id_publisher" = %s', ['some publisher name', 5])
print(qry.assemble())

# UPDATE with explicit values and WHERE
qry = Update(PgSqlDialect()).table('table').fields(['field']).values(['value'])
# output: ('UPDATE "table" SET "field"=%s', ['value'])
print(qry.assemble())

# UPDATE with dict values
qry = (
    Update(PgSqlDialect()).table("table").values({"field": "value"}).where("id", "=", 7)
)
# output: ('UPDATE "table" SET "field"=%s WHERE "id" = %s', ['value', 7])
print(qry.assemble())

# UPDATE WHERE IS NOT NULL — unary operator, no value needed
qry = (
    Update(PgSqlDialect())
    .table("table")
    .values({"field": "value"})
    .where("id", "IS NOT NULL")
)
# output: ('UPDATE "table" SET "field"=%s WHERE "id" IS NOT NULL', ['value'])
print(qry.assemble())

# UPDATE with multiple WHERE clauses (AND)
qry = (
    Update(PgSqlDialect())
    .table("table")
    .values({"field": "value"})
    .where("id", "=", 7)
    .where("name", "ILIKE", "john%")
)
# output: ('UPDATE "table" SET "field"=%s WHERE "id" = %s AND "name" ILIKE %s', ['value', 7, 'john%'])
print(qry.assemble())

# UPDATE WHERE IN with a list
qry = (
    Update(PgSqlDialect())
    .table("table")
    .values({"field": "value"})
    .where("id", "IN", [1, 2, 3])
)
# output: ('UPDATE "table" SET "field"=%s WHERE "id" IN (%s, %s, %s)', ['value', 1, 2, 3])
print(qry.assemble())

# UPDATE with Literal value (e.g. increment a counter)
from rick_db.sql import Literal

qry = (
    Update(PgSqlDialect())
    .table("table")
    .values({"counter": Literal('"counter" + 1')})
    .where("id", "=", 1)
)
print(qry.assemble())

# UPDATE with RETURNING
qry = (
    Update(PgSqlDialect())
    .table("table")
    .values({"name": "Bob"})
    .where("id", "=", 1)
    .returning(["id", "name"])
)
print(qry.assemble())
```

## Delete

[Delete](classes/delete.md) objects generate SQL **DELETE** statements. The `from_()` method sets the target
table (string or fieldmapper class). `where()` and `orwhere()` filter which rows to delete — they accept the
same arguments as Select's WHERE methods, including IN/NOT IN with lists and subqueries.

```python
from rick_db.sql import Delete, PgSqlDialect

# DELETE WHERE — common usage
qry = Delete(PgSqlDialect()).from_("table").where("id", "=", 7)
# output: ('DELETE FROM "table" WHERE "id" = %s', [7])
print(qry.assemble())

# DELETE WHERE IS NOT NULL
qry = Delete(PgSqlDialect()).from_("table").where("id", "IS NOT NULL")
# output: ('DELETE FROM "table" WHERE "id" IS NOT NULL', [])
print(qry.assemble())

# DELETE with multiple WHERE clauses (AND)
qry = (
    Delete(PgSqlDialect())
    .from_("table")
    .where("id", "=", 7)
    .where("name", "ILIKE", "john%")
)
# output: ('DELETE FROM "table" WHERE "id" = %s AND "name" ILIKE %s', [7, 'john%'])
print(qry.assemble())

# DELETE WHERE IN with a list
qry = Delete(PgSqlDialect()).from_("table").where("id", "IN", [1, 2, 3])
# output: ('DELETE FROM "table" WHERE "id" IN (%s, %s, %s)', [1, 2, 3])
print(qry.assemble())

# DELETE WHERE NOT IN with a list
qry = Delete(PgSqlDialect()).from_("table").where("status", "NOT IN", ["active", "pending"])
# output: ('DELETE FROM "table" WHERE "status" NOT IN (%s, %s)', ['active', 'pending'])
print(qry.assemble())

# DELETE with OR WHERE
qry = (
    Delete(PgSqlDialect())
    .from_("table")
    .where("active", "=", False)
    .orwhere("email", "IS NULL")
)
print(qry.assemble())

# DELETE with subquery
from rick_db.sql import Select

inactive = Select(PgSqlDialect()).from_("logs", ["user_id"]).where("last_seen", "<", "2020-01-01")
qry = Delete(PgSqlDialect()).from_("users").where("id", "IN", inactive)
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

[With](classes/with.md) objects generate Common Table Expression (CTE) statements. CTEs define named temporary
result sets that exist for the scope of a single query.

**Methods:**

- **`clause(name, with_query, columns=None, materialized=True)`** — adds a named CTE. `with_query` is a `Select`
  or `Literal`, `columns` optionally defines explicit column names, and `materialized=False` adds `NOT MATERIALIZED`.
- **`query(query)`** — sets the main SELECT that references the CTEs.
- **`recursive()`** — enables `WITH RECURSIVE` for self-referencing CTEs.

Multiple `clause()` calls add multiple CTEs.

```python
from rick_db import fieldmapper
from rick_db.sql import Select, PgSqlDialect, With, Sql

@fieldmapper(tablename="folder", pk="id_folder")
class FolderRecord:
    id = "id_folder"
    parent = "fk_parent"


dialect = PgSqlDialect()

# Recursive CTE — walk a folder tree starting from folder 19
union = Select(dialect).union(
    [
        # Base case: start at folder 19
        Select(dialect).from_({FolderRecord: "f1"}).where(FolderRecord.id, "=", 19),
        # Recursive case: join children via parent FK
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
