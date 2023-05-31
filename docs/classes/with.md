# Class rick_db.sql.**With**

A wrapper for ordinary or recursive Common Table Expressions (CTE).

### With.**\_\_init\_\_(dialect: SqlDialect = None)**

Initialize the CTE wrapper object, using a database *dialect*. If no *dialect* is provided, a default dialect will be
used.
Check [SqlDialect](sqldialect.md) for more details.

### With.**recursive(status=True)**

Creates a recursive CTE if status is True, or an ordinary CTE if status is False

Example:

```python
union = Select().union([
    Literal("VALUES(1)"),
    Select().from_("t", cols=[Literal("n+1")]).where("n", "<", 100)
], Sql.UNION_ALL)

# assemble a recursive CTE
with_qry = With()
    .clause("t", union)
    .query(Select().from_("t", cols={Literal("SUM(n)"): "total"}))
    .recursive()

sql, values = with_qry.assemble()
# sql: WITH RECURSIVE "t"("n") AS (VALUES(1) UNION SELECT n+1 FROM "t" WHERE ("n" < %s)) SELECT SUM(n) AS "total" FROM "t"
# values: [100]
```

### With.**clause(name: str, with_query: Union[SqlStatement, Literal], columns: list = None, materialized: bool =
True)**

Adds a CTE expression with the format WITH *name*(*columns*) AS (*with_query*); The *columns* parameter is optional.
If *materialized* is False, WITH...NOT MATERIALIZED AS () is generated instead.

### With.**query(query: SqlStatement)**

Specifies the final CTE query to be applied on the expressions.

### With.**assemble()**

Generates a tuple with the generated SQL string and list of values.
