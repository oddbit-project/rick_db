rick_db - Simple SQL database layer
--
[![Tests](https://github.com/oddbit-project/rick_db/workflows/Tests/badge.svg?branch=master)](https://github.com/oddbit-project/rick_db/actions)
[![pypi](https://img.shields.io/pypi/v/rick-db.svg)](https://pypi.org/project/rick-db/)
[![license](https://img.shields.io/pypi/l/rick-db.svg)](https://github.com/oddbit-project/rick_db/blob/master/LICENSE)


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


## Installation
```
$ pip3 install rick-db
```

## Connection

### PostgreSQL

There are several PostgreSQL connectors available. However, it is recommended to use PgConnection with pgpool, instead of
the available connection pool classes.

Using PgConnection:

```python
from rick_db.conn.pg import PgConnection

config = {
    'dbname': 'my_database',
    'user': '<some_user>',
    'password': '<some_password>',
    'host': 'localhost',
    'port': 5432,
}

# create connection
conn = PgConnection(**config)
```

Using PgConnectionPool:

```python
from rick_db.conn.pg import PgConnectionPool

config = {
    'dbname': 'my_database',
    'user': '<some_user>',
    'password': '<some_password>',
    'host': 'localhost',
    'port': 5432,
    'min_conn': 4,
}

# create connection
conn = PgConnectionPool(**config)
```

Using PgThreadedConnectionPool:

```python
from rick_db.conn.pg import PgThreadedConnectionPool

config = {
    'dbname': 'my_database',
    'user': '<some_user>',
    'password': '<some_password>',
    'host': 'localhost',
    'port': 5432,
    'min_conn': 4,
}

# create connection
conn = PgThreadedConnectionPool(**config)
```


### SqlLite

```python
from rick_db.conn.sqlite import Sqlite3Connection

# create or open a sqlite database
conn = Sqlite3Connection('my_database.db')
```

## Object Mapper

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
## Query Builder 

Features:
- support for Select, Insert, Delete, Update queries;
- join support;
- schema support, including cross-schema operations;
- integration with fieldmapper; 

The query builder provides SQL generation using a fluent interface, suitable for most cases. Different database support
is handled via dialect objects (extending from SqlDialect). The query builder itself will only generate a SQL string
and a parameter list; its up to the developer to use the generated SQL in the appropriate database context.

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

Insert Query Builder examples:
```python
from rick_db.sql import Insert

record = {
    'field1': 'value1',
    'field2': 12,
}
qry, values = Insert().into('mytable').values(record).assemble()
# INSERT INTO "mytable" ("field1", "field2") VALUES (?, ?)
print(qry)
# ['value1', 12]
print(values)

qry, values = Insert().into('mytable').values(record).returning(['id']).assemble()
# INSERT INTO "mytable" ("field1", "field2") VALUES (?, ?) RETURNING "id"
print(qry)
# ['value1', 12]
print(values)
``` 

Delete Query Builder examples:

```python
from rick_db.sql import Delete

qry, values = Delete().from_('mytable').assemble()
# output: DELETE FROM "mytable"
print(qry)
# output: []
print(values)

qry, values = Delete().from_('mytable').where('id', '=', 16).assemble()
# output: DELETE FROM "mytable" WHERE "id" = ?
print(qry)
# output: [16]
print(values)

qry, values = Delete().from_('mytable') \
    .where('id', '=', 16) \
    .orwhere('name', 'LIKE', '%John%') \
    .assemble()
# output: DELETE FROM "mytable" WHERE "id" = ? OR "name" LIKE ?
print(qry)
# [16, '%John%']
print(values)
```

Select using Object Mapper:

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

Insert using Object Mapper:

```python
from rick_db import fieldmapper
from rick_db.sql import Insert


@fieldmapper(tablename='customers', pk='id_customer')
class Customer:
    id = 'id_customer'
    name = 'name'
    address = 'address'
    city = 'city'
    id_country = 'fk_country'


record = Customer(id=1, name='John', city='Dallas')

qry, values = Insert().into(Customer).values(record).assemble()
# output: INSERT INTO "customers" ("id_customer", "name", "city") VALUES (?, ?, ?)
print(qry)
# output: [1, 'John', 'Dallas']
print(values)

# Insert() - compact form with Records
# into() will detect its a valid record, and parse everything from there
qry, values = Insert().into(record).assemble()
# output: INSERT INTO "customers" ("id_customer", "name", "city") VALUES (?, ?, ?)
print(qry)
# output: [1, 'John', 'Dallas']
print(values)

qry, values = Insert().into(record).returning([Customer.id]).assemble()
# output: INSERT INTO "customers" ("id_customer", "name", "city") VALUES (?, ?, ?) RETURNING "id_customer"
print(qry)
# output: [1, 'John', 'Dallas']
print(values)
```
Delete using Object Mapper:

```python
from rick_db import fieldmapper
from rick_db.sql import Delete


@fieldmapper(tablename='customers', pk='id_customer')
class Customer:
    id = 'id_customer'
    name = 'name'
    address = 'address'
    city = 'city'
    id_country = 'fk_country'


record = Customer(id=1, name='John', city='Dallas')

qry, values = Delete().from_(Customer).assemble()
# output: DELETE FROM "customers"
print(qry)
# output: []
print(values)

qry, values = Delete().from_(Customer).where(Customer.id, '=', record.id).assemble()
# output: DELETE FROM "customers" WHERE "id_customer" = ?
print(qry)
# output: [1]
print(values)

qry, values = Delete().from_(Customer) \
    .where(Customer.id, '=', record.id) \
    .orwhere(Customer.name, 'LIKE', '%John%') \
    .assemble()
# output: DELETE FROM "customers" WHERE "id_customer" = ? OR "name" LIKE ?
print(qry)
# [1, '%John%']
print(values)
```

## Repository

The **Repository** class provides a simple wrapper for **Record** read, insert, update and delete operations. Most operations
require that the **Record** has both tablename and primary key information available.
 
A repository object requires a database connection and a **Record** class:

 ```python
from rick_db import fieldmapper, Repository
from rick_db.conn.pg import PgConnection


@fieldmapper(tablename='users', pk='id_user')
class User:
    id = 'id_user'
    name = 'name'
    age = 'age'


conn = PgConnection(dbname='tests', user='postgres', password='some_password')

# create a repository for User class
user_repository = Repository(conn, User)

# iterate all records
for user in user_repository.fetch_all():
    print("Name: ", user.name)

```

**Repository** available methods:

|Method|Description|
|---|---|
|backend()| Retrieve Connection instance|
|dialect()| Retrieve SqlDialect instance|
|select() | New Select() instance for the current table|
|fetch_pk(pk_value)| Get one record by primary key value|
|fetch_one(qry)| Get one record using the specified query|
|fetch(qry)| Get list of records using the specified query|
|fetch_raw(qry) | Get result using the specified query; no record serialization is done|
|fetch_by_field(field, value, cols)| Get a list of records where field==value|
|fetch_where(where_clauses, cols)| Get a list of records using a where clause list (AND only)|
|fetch_all() | Get all records|
|insert(record, cols)| Insert a record, optionally returning values|
|insert_pk(record)| Insert a record and return the primary key value|
|delete_pk(pk_value)| Delete a record by primary key value|
|delete_where(where_clauses)| Delete records by where clause list (AND only)|
|map_result_id(result) | Return a dict from a result list, where the key is the primary key|
|valid_pk(pk_value)| Check if a given pk exists|
|exec(sql, values, cls, useCls) | Execute a raw query and return the result|
|exists(field, value, pk_to_skip)| Check if a field has a given value other than in the record specified by primary key|
|update(record, pk_value) | Updates a record|
|update_where(record, where_list)|Updates one or more records using a where clause list|
|count()| Get number of rows|
|count_where(where_list)| Count rows using a where clause list|


## Running tests

To run the tests, you should have both tox and tox-docker, as well as a local docker daemon. Make sure the current user has
access to the docker daemon.
```python
$ pip3 install tox tox-docker
$ tox 
```
