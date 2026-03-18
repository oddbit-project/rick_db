"""
Fn helper class for SQL aggregate and math functions.

Demonstrates:
 - Fn.count, Fn.sum, Fn.avg, Fn.min, Fn.max
 - Fn.round with nesting (Fn.round(Fn.avg(...)))
 - Fn.coalesce, Fn.cast
 - GROUP BY with HAVING
 - Dict-style column aliases with Fn expressions
"""
from rick_db.sql import Select, Fn, PgSqlDialect

dialect = PgSqlDialect()

# -- Basic aggregates with aliases --

# COUNT(*) with alias
qry, _ = Select(dialect).from_("orders", {Fn.count(): "total_orders"}).assemble()
# SELECT COUNT(*) AS "total_orders" FROM "orders"
print(qry)

# COUNT on a specific field
qry, _ = Select(dialect).from_("orders", {Fn.count("discount"): "discounted_orders"}).assemble()
# SELECT COUNT(discount) AS "discounted_orders" FROM "orders"
print(qry)


# -- Multiple aggregates with GROUP BY --

qry, _ = (
    Select(dialect)
    .from_(
        "orders",
        {
            "category": None,
            Fn.count(): "order_count",
            Fn.sum("amount"): "total_amount",
            Fn.avg("amount"): "avg_amount",
            Fn.min("amount"): "min_amount",
            Fn.max("amount"): "max_amount",
        },
    )
    .group("category")
    .assemble()
)
# SELECT "category",COUNT(*) AS "order_count",SUM(amount) AS "total_amount",...
print(qry)


# -- Nested functions: ROUND(AVG(...), 2) --

qry, _ = (
    Select(dialect)
    .from_(
        "orders",
        {
            "category": None,
            Fn.round(Fn.avg("amount"), 2): "avg_rounded",
        },
    )
    .group("category")
    .assemble()
)
# SELECT "category",ROUND(AVG(amount), 2) AS "avg_rounded" FROM "orders" GROUP BY "category"
print(qry)


# -- GROUP BY with HAVING --

qry, values = (
    Select(dialect)
    .from_(
        "orders",
        {
            "category": None,
            Fn.count(): "cnt",
            Fn.sum("amount"): "total",
        },
    )
    .group("category")
    .having(Fn.count(), ">", 10)
    .assemble()
)
# SELECT ... FROM "orders" GROUP BY "category" HAVING (COUNT(*) > %s)
print(qry)
print("values:", values)


# -- Math functions --

qry, _ = (
    Select(dialect)
    .from_(
        "measurements",
        {
            "sensor_id": None,
            Fn.abs("reading"): "abs_reading",
            Fn.ceil("reading"): "ceil_reading",
            Fn.floor("reading"): "floor_reading",
            Fn.round("reading", 3): "rounded",
            Fn.sqrt(Fn.abs("reading")): "sqrt_abs",
        },
    )
    .assemble()
)
print(qry)


# -- COALESCE and CAST --

qry, _ = (
    Select(dialect)
    .from_(
        "users",
        {
            "name": None,
            Fn.coalesce("nickname", "name"): "display_name",
            Fn.cast("created_at", "date"): "created_date",
        },
    )
    .assemble()
)
# SELECT "name",COALESCE(nickname, name) AS "display_name",CAST(created_at AS date) AS "created_date" FROM "users"
print(qry)
