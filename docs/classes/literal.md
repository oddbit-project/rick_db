# Class rick_db.sql.**Literal**

Class used to encapsulate literal values

### Literal.**\_\_init\_\_(literal)**

Create a Literal object with *literal* as content
```python
qry, _ = Select(PgSqlDialect()).from_('table', {Literal('COUNT(*)'): 'total'}).assemble()
# output: SELECT COUNT(*) AS "total" FROM "table"
print(qry)
```