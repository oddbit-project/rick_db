# Building Queries

RickDb's Query Builder can generate SELECT, INSERT, DELETE and UPDATE queries. It also provides schema support (including
cross-schema operations), JOIN support and recognizes [Object Mapper](object_mapper.md) objects for table and schema 
identification.

The query builder provides SQL generation using a fluent interface, suitable for most cases. Different database support
is handled via dialect objects (extending from SqlDialect). The query builder itself will only generate a SQL string
and a parameter value list; it is up to the developer to use the generated SQL in the appropriate database context.

## Select

Select are by far the most common statements. 



The query builder supports Object Mapper classes as table and schema identifiers in most cases; however it can also be
used without any Object Mapper reference. See examples below:

Select Query Builder examples:
```python
from rick_db.sql import Select, PgSqlDialect, Literal

qry, values = Select(PgSqlDialect()).from_('table').assemble()
# output: SELECT "table".* FROM "table"
print(qry)

qry, values = Select(PgSqlDialect()).from_('table1', ['table1_field']) \
    .from_('table2', ['table2_field']) \
    .assemble()
# output: SELECT "table1_field","table2_field" FROM "table1", "table2"
print(qry)

qry, values = Select(PgSqlDialect()).from_('table1', ['table1_field']) \
    .from_('table2', ['table2_field']) \
    .order('table1_field', 'DESC') \
    .order('table2_field') \
    .assemble()
# output: SELECT "table1_field","table2_field" FROM "table1", "table2" ORDER BY "table1_field" DESC,"table2_field" ASC
print(qry)

qry, values = Select(PgSqlDialect()).expr("1").assemble()
# output: SELECT 1
print(qry)

qry, values = Select(PgSqlDialect()).from_('table', {Literal('COUNT(*)'): 'total'}).assemble()
# output: SELECT COUNT(*) AS "total" FROM "table"
print(qry)

qry, values = Select(PgSqlDialect()).from_('table', ['field1', 'field2']).assemble()
# output: SELECT "field1","field2" FROM "table"
print(qry)

qry, values = Select(PgSqlDialect()).from_({'table': 'alias'}, ['field1', 'field2']).assemble()
# output: SELECT "alias"."field1","alias"."field2" FROM "table" AS "alias"
print(qry)

qry, values = Select(PgSqlDialect()).from_({'table': 'alias'}, [{'field1': 'field_alias'}, 'field2']).assemble()
# output: SELECT "alias"."field1" AS "field_alias","alias"."field2" FROM "table" AS "alias"
print(qry)

qry, values = Select(PgSqlDialect()).from_('table') \
    .join('other_table', 'fk_table', 'table', 'id_table') \
    .assemble()
# output: SELECT "table".* FROM "table" INNER JOIN "other_table" ON "table"."id_table"="other_table"."fk_table"
print(qry)

qry, values = Select(PgSqlDialect()).from_('table') \
    .join('other_table', 'fk_table', 'table', 'id_table', cols=['some_field', {'other_table_field': 'other_field'}]) \
    .assemble()
# output: SELECT "table".*,"other_table"."some_field","other_table"."other_table_field" AS "other_field" FROM "table" INNER JOIN "other_table" ON "table"."id_table"="other_table"."fk_table"
print(qry)

qry, values = Select(PgSqlDialect()).from_('customers') \
    .join('orders', 'fk_customer', 'customers', 'id') \
    .join('sales', 'fk_order', 'orders', 'id', cols=[{'document_total': 'total'}]) \
    .assemble()
# output: SELECT "customers".*,"sales"."document_total" AS "total" FROM "customers" INNER JOIN "orders" ON "customers"."id"="orders"."fk_customer" INNER JOIN "sales" ON "orders"."id"="sales"."fk_order"
print(qry)
```


### JOIN