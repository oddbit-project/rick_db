# Class rick_db.sql.**Literal**

Class used to encapsulate literal values

### Literal.**\_\_init\_\_(literal)**

Create a Literal object with *literal* as content
```python
qry, _ = Select(PgSqlDialect()).from_('table', {Literal('COUNT(*)'): 'total'}).assemble()
# output: SELECT COUNT(*) AS "total" FROM "table"
print(qry)
```

# Class rick_db.sql.**L**

This class is an alias of [Literal](#class-rick_dbsqlliteral); to be used as a shortcut and to avoid naming collisions