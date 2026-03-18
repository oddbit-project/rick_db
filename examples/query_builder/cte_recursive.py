"""
Recursive CTE (Common Table Expression) for walking a tree structure.

Demonstrates:
 - With() builder for CTEs
 - Recursive CTEs with UNION ALL
 - Non-recursive CTEs
 - Multiple CTE clauses
"""
from rick_db import fieldmapper
from rick_db.sql import Select, With, Literal, Fn, Sql, PgSqlDialect

dialect = PgSqlDialect()


# -- Example 1: Recursive tree walk (e.g. folder hierarchy) --

@fieldmapper(tablename="folder", pk="id_folder")
class Folder:
    id = "id_folder"
    name = "name"
    parent = "fk_parent"


# Walk all descendants of folder id=1
# Base case: the root folder
base = Select(dialect).from_({Folder: "f1"}).where(Folder.id, "=", 1)

# Recursive case: join children via parent FK
recursive = (
    Select(dialect)
    .from_({Folder: "f2"})
    .join("folder_tree", Folder.parent, "f2", Folder.id)
)

# Combine with UNION ALL
union = Select(dialect).union([base, recursive], Sql.SQL_UNION_ALL)

# Build the CTE
qry, values = (
    With(dialect)
    .recursive()
    .clause("folder_tree", union)
    .query(Select(dialect).from_("folder_tree"))
    .assemble()
)
# WITH RECURSIVE "folder_tree" AS (
#   SELECT "f1".* FROM "folder" AS "f1" WHERE ("id_folder" = %s)
#   UNION ALL
#   SELECT "f2".* FROM "folder" AS "f2" INNER JOIN "folder_tree" ON "f2"."id_folder"="folder_tree"."fk_parent"
# ) SELECT "folder_tree".* FROM "folder_tree"
print("=== Recursive tree walk ===")
print(qry)
print("values:", values)


# -- Example 2: Recursive number series with column specification --

# Generate numbers 1 to 10 using a recursive CTE
base_num = Select(dialect).expr([Literal("1 AS n")])
recursive_num = Select(dialect).from_("nums", {Literal("n + 1"): "n"}).where("n", "<", 10)
union_num = Select(dialect).union([base_num, recursive_num], Sql.SQL_UNION_ALL)

qry, values = (
    With(dialect)
    .recursive()
    .clause("nums", union_num, columns=["n"])
    .query(Select(dialect).from_("nums"))
    .assemble()
)
# WITH RECURSIVE "nums"("n") AS (
#   SELECT 1 AS n UNION ALL SELECT n + 1 AS "n" FROM "nums" WHERE ("n" < %s)
# ) SELECT "nums".* FROM "nums"
print("\n=== Recursive number series ===")
print(qry)
print("values:", values)


# -- Example 3: Non-recursive CTE for readability --

# Use a CTE to pre-filter, then query the result
cte_query = (
    Select(dialect)
    .from_("orders", ["customer_id", "amount"])
    .where("amount", ">", 100)
)

main_query = (
    Select(dialect)
    .from_("big_orders", {"customer_id": None, Fn.sum("amount"): "total"})
    .group("customer_id")
)

qry, values = (
    With(dialect)
    .clause("big_orders", cte_query)
    .query(main_query)
    .assemble()
)
print("\n=== Non-recursive CTE ===")
print(qry)
print("values:", values)


# -- Example 4: Multiple CTE clauses --

active_users = (
    Select(dialect)
    .from_("users", ["id", "name"])
    .where("active", "=", True)
)

user_totals = (
    Select(dialect)
    .from_("orders", {"user_id": None, Fn.sum("amount"): "total"})
    .group("user_id")
)

main = (
    Select(dialect)
    .from_("au", ["name"])
    .join("ut", "user_id", "au", "id", cols=["total"])
)

qry, values = (
    With(dialect)
    .clause("au", active_users)
    .clause("ut", user_totals)
    .query(main)
    .assemble()
)
print("\n=== Multiple CTEs ===")
print(qry)
print("values:", values)
