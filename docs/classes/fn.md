# Class rick_db.sql.**Fn**

SQL function helpers that return [Literal](literal.md) instances. Designed to be used with dict-style column
definitions for aliasing.

All methods are static and return a `Literal`, so they can be used anywhere a `Literal` is accepted: column lists,
`having()` clauses, nested inside other `Fn` calls, etc.

## Aggregate Functions

### Fn.**count(field="*")**

Returns `Literal("COUNT(field)")`.

```python
Fn.count()          # COUNT(*)
Fn.count("id")      # COUNT(id)
```

### Fn.**sum(field)**

Returns `Literal("SUM(field)")`.

### Fn.**avg(field)**

Returns `Literal("AVG(field)")`.

### Fn.**min(field)**

Returns `Literal("MIN(field)")`.

### Fn.**max(field)**

Returns `Literal("MAX(field)")`.

## Math Functions

### Fn.**abs(field)**

Returns `Literal("ABS(field)")`.

### Fn.**ceil(field)**

Returns `Literal("CEIL(field)")`.

### Fn.**floor(field)**

Returns `Literal("FLOOR(field)")`.

### Fn.**round(field, decimals=None)**

Returns `Literal("ROUND(field)")` or `Literal("ROUND(field, decimals)")` if *decimals* is specified.

```python
Fn.round("price")       # ROUND(price)
Fn.round("price", 2)    # ROUND(price, 2)
```

### Fn.**power(field, exponent)**

Returns `Literal("POWER(field, exponent)")`.

### Fn.**sqrt(field)**

Returns `Literal("SQRT(field)")`.

### Fn.**mod(field, divisor)**

Returns `Literal("MOD(field, divisor)")`.

### Fn.**sign(field)**

Returns `Literal("SIGN(field)")`.

### Fn.**trunc(field, decimals=None)**

Returns `Literal("TRUNC(field)")` or `Literal("TRUNC(field, decimals)")` if *decimals* is specified.

```python
Fn.trunc("price")       # TRUNC(price)
Fn.trunc("price", 1)    # TRUNC(price, 1)
```

## General Functions

### Fn.**coalesce(*fields)**

Returns `Literal("COALESCE(field1, field2, ...)")`.

```python
Fn.coalesce("nickname", "name", "'unknown'")   # COALESCE(nickname, name, 'unknown')
```

### Fn.**cast(field, type_name)**

Returns `Literal("CAST(field AS type_name)")`.

```python
Fn.cast("price", "integer")   # CAST(price AS integer)
```

## Usage

`Fn` helpers return `Literal` objects, so they are used with dict-style column definitions where the key is the
expression and the value is the alias (or `None` for no alias):

```python
from rick_db.sql import Select, Fn, PgSqlDialect

dialect = PgSqlDialect()

# Single aggregate
qry, _ = Select(dialect).from_("orders", {Fn.count(): "total"}).assemble()
# output: SELECT COUNT(*) AS "total" FROM "orders"

# Multiple columns with aggregates
qry, _ = (
    Select(dialect)
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

# Nested functions
qry, _ = (
    Select(dialect)
    .from_("orders", {
        "category": None,
        Fn.round(Fn.avg("amount"), 2): "avg_rounded",
    })
    .group("category")
    .assemble()
)
# output: SELECT "category",ROUND(AVG(amount), 2) AS "avg_rounded" FROM "orders" GROUP BY "category"

# With HAVING
qry, _ = (
    Select(dialect)
    .from_("orders", {
        "category": None,
        Fn.sum("amount"): "total",
    })
    .group("category")
    .having(Fn.sum("amount"), ">", 1000)
    .assemble()
)
# output: SELECT "category",SUM(amount) AS "total" FROM "orders" GROUP BY "category" HAVING (SUM(amount) > %s)

# With fieldmapper Record classes
qry, _ = (
    Select(dialect)
    .from_(Order, {
        Order.category: None,
        Fn.count(): "cnt",
        Fn.min(Order.price): "cheapest",
        Fn.max(Order.price): "priciest",
        Fn.round(Fn.avg(Order.price), 2): "avg_price",
    })
    .group(Order.category)
    .order(Order.category)
    .assemble()
)
```
