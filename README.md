rick_db - Simple SQL database layer
--

rick_db is a simple SQL database layer for Python3. It includes connection management, Object Mapper, Query Builder,
and a Repository pattern implementation. It is **not** an ORM, and it's not meant to replace one. 

## Features
- Object Mapper;
- Fluent Sql Query builder;
- High level connectors for PostgreSQL, SqlLite3;
- Pluggable SQL query profiler; 

## Usage scenarios

rick_db was built to cater to a schema-first approach: Database schema is built and managed directly with SQL DDL commands,
and the application layer has no responsibility on the structure of the database.


### Installation

### Connection
TBD

### Object Mapper

The object mapper converts query results into object attributes. These data objects are generically known as **Records**.
A Record contains a set of attributes for the desired fields, as well as optional table, schema and primary key information.

Usually, Record objects should only contain attributes, as their primary goal is to act like DAO (data access objects). As
such, Records don't need to map an underlying table or view; They are just a set of fields that may map to a query result.
It is possible to create Record objects that map only specific fields from a query result; the additional fields are just
ignored.

The attribute names of the Record objects don't need to match the field in the database result object; instead, the target
column name is specified as their value. The field mapper mechanism will patch the defined class and build the appropriate
internal mapping structures. This internal mapping is done at load time, and not at run time. The resulting class will
have distinct behaviour when accessing attributes, depending on the current scope; class-scope access returns the
atribute-column definitions, object scope returns the underlying row value for the given attribute, or None if value is
not present.

To create a Record class, just use the @fieldmapper decorator:

```python
from rick_db import fieldmapper

@fieldmapper
class Customer:
    id = 'id_customer'
    name = 'name'
    address = 'address'
    city = 'city'
    id_country = 'fk_country'

# access class-level attributes
print(Customer.name) # outputs  'name'

# access object-level attributes
# customer data is loaded via __init__; The key names must match the defined attributes
customer = Customer(id=3, name="John Doe", address="Obere Str.", city="Berlin")

print(customer.name)  # outputs 'John Doe'
print(customer.id_country) # outputs 'None' 
```

It is possible to also provide optional table/view, primary key and schema information; this is particularly useful
when using **Repositories** or the bundled **Query Builder**

Extending on the previous examples:
```python
from rick_db import fieldmapper

@fieldmapper(tablename='customers', pk='id_customer', schema='public')
class Customer:
    id = 'id_customer'
    name = 'name'
    address = 'address'
    city = 'city'
    id_country = 'fk_country'

# access class-level attributes
print(Customer.name) # outputs  'name'

# access object-level attributes
# customer data is loaded via __init__; The key names must match the defined attributes
customer = Customer(id=3, name="John Doe", address="Obere Str.", city="Berlin")

print(customer.name)  # outputs 'John Doe'
print(customer.id_country) # outputs 'None' 
```
### Query Builder 

The query builder provides SQL generation using a fluent interface, suitable for most cases. Different database support
is handled via dialect objects (extending from SqlDialect). The query builder itself will only generate a SQL string
and a parameter list; its up to the developer to use the generated SQL in the appropriate database context.

The query builder supports Object Mapper classes as table and schema identifiers in most cases; however it can also be
used without any Object Mapper reference. See examples below:

Query Builder examples:
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
Using Object Mapper:

```python
from rick_db import fieldmapper
from rick_db.sql import Select


@fieldmapper(tablename='customers', pk='id_customer')
class Customer:
    id = 'id_customer'
    name = 'name'
    address = 'address'
    city = 'city'
    id_country = 'fk_country'


@fieldmapper(tablename='orders', pk='id_order')
class Order:
    id = 'id_order'
    id_customer = 'fk_customer'
    order_date = 'order_date'
    total = 'order_total'


@fieldmapper(tablename='sales', pk='id_sale')
class Sale:
    id = 'id_sale'
    id_order = 'fk_order'
    total = 'sale_total'


qry = Select().from_(Customer, [Customer.name, Customer.city]) \
    .join({Order: "o"}, Order.id_customer, Customer, Customer.id) \
    .join({Sale: "s"}, Sale.id_order, {Order: "o"}, Order.id, cols=Sale.total) \
    .where(Sale.total, '>', 100)

# output: ('SELECT "name","city","s"."sale_total" FROM "customers" INNER JOIN "orders" AS "o" ON "customers"."id_customer"="o"."fk_customer" INNER JOIN "sales" AS "s" ON "o"."id_order"="s"."fk_order" WHERE ("sale_total" > ?)', [100])
print(qry.assemble())
```

### Repository
TBD

