# Class rick_db.sql.**Select**

### Select.**\_\_init\_\_(dialect: SqlDialect = None)**

Initialize a Select() object, using a database *dialect*. If no *dialect* is provided, a default dialect will be used.
Check [SqlDialect](sqldialect.md) for more details.

### Select.**distinct(flag=True)**

Enables or disables the usage of **DISTINCT** clause, based on the state of *flag*. The provided **DISTINCT** functionality
is limited - it doesn't support wildcard or specific columns.

Example:
```python
sql, _ = Select(PgSqlDialect()).from_('test_table', 'field').distinct().assemble()
# output: SELECT DISTINCT "field" FROM "test_table"
print(sql)
```

### Select.**expr(cols=None)**

Adds an anonymous expression to the **SELECT** statement. It can only be used once in a query. Possible *cols* values can
be:
- string with contents
- a list of strings with contents
- a [Literal](literal.md) object
- a list of [Literal](literal.md) objects

Example:
```python
qry, _ = Select(PgSqlDialect()).expr('1').assemble()
# output: SELECT 1
print(qry)

qry, _ = Select(PgSqlDialect()).expr(['1','2','3']).assemble()
# output: SELECT 1,2,3
print(qry)

qry, _ = Select(PgSqlDialect()).expr({Literal("NEXTVAL('some_sequence_name')"): "seq_next"}) .assemble()
# output: SELECT NEXTVAL('some_sequence_name') AS "seq_next"
print(qry)
```


### Select.**from_(table, cols=None, schema=None)**

Adds a **FROM** clause to the query. The *table* is a [table identifier](#table-identifier) expression, *cols* is a 
[column identifier](#column-identifier) and *schema* specifies an optional schema for *table*.

Example:
```python
qry, _ = Select(PgSqlDialect()).from_("foo").assemble()
# output: SELECT "foo".* FROM "foo"
print(qry)

qry, _ = Select(PgSqlDialect()).from_("foo", None, "public").assemble()
# output: SELECT "foo".* FROM "public"."foo"
print(qry)

qry, _ = Select(PgSqlDialect()).from_({"foo":"bar"}).assemble()
# output: SELECT "bar".* FROM "foo" AS "bar"
print(qry)

qry, _ = Select(PgSqlDialect()).from_("foo", {"field1":None, "field2":"alias"}).assemble()
# output: SELECT "field1","field2" AS "alias" FROM "foo"
print(qry)

qry, _ = Select(PgSqlDialect()).from_("foo", "field").assemble()
# output: SELECT "field" FROM "foo"
print(qry)

qry, _ = Select(PgSqlDialect()).from_("foo", ["field1", "field2"]).assemble()
# output: SELECT "field1", "field2" FROM "foo"
print(qry)

qry, _ = Select(PgSqlDialect()).from_({"foo": "bar"}, ["field1"]).assemble()
# output: SELECT "bar.field1" FROM "foo" AS "bar"
print(qry)

qry, _ = Select(PgSqlDialect()).from_(record_class_or_object, ["field1"]).assemble()
# output: SELECT "field1" FROM "<object_table_name>"
print(qry)

qry, _ = Select(PgSqlDialect()).from_({record_class_or_object: "bar"}, ["field1"]).assemble()
# output: SELECT "bar"."field1" FROM "<object_table_name>" AS "bar"
print(qry)
```

#### Table identifier

A table identifier can be a string, [Record](record.md) class or object, a {'table':'alias'} dict, or a 
{[Record](record.md) class or object:'alias'} dict.

#### Column identifier

A column identifier can be None ('*' will be used), a string with a field name, a list of field names, a
{'field': 'alias'} dict, a {'field': None, 'other_field':'alias} dict, or a [{'field': 'alias'}, 'field', ] list 
of mixed string and dict values. 

### Select.**limit(limit: int, offset: int = None)**

Adds an **LIMIT**/**OFFSET** clause.

Example:
```python
qry, _ = Select(PgSqlDialect()).from_("foo").limit(10).assemble()
# output: SELECT "foo".* FROM "foo" LIMIT 10
print(qry)

qry, _ = Select(PgSqlDialect()).from_("foo").limit(10, 5).assemble()
# output: SELECT "foo".* FROM "foo" LIMIT 10 OFFSET 5
print(qry)
```

### Select.**page(page: int, page_rows: int)**

Helper to add **LIMIT**/**OFFSET** clause for pagination purposes. *page* specifies which page to fetch, starting from 1,
and *page rows* specifies the number of rows per page

Example:
```python
qry, _ = Select(PgSqlDialect()).from_("foo").page(1, 10).assemble()
# output: SELECT "foo".* FROM "foo" LIMIT 10 OFFSET 0
print(qry)

qry, _ = Select(PgSqlDialect()).from_("foo").page(10, 10).assemble()
# output: SELECT "foo".* FROM "foo" LIMIT 10 OFFSET 10
print(qry)
```

### Select.**for_update(flag: bool = True)**

Adds a **FOR UPDATE** clause if *flag* is True.

### Select.**order(fields, order=Sql.SQL_ASC)**

Adds an **ORDER BY** clause with the specified *fields*. *order* is **ASC** by default.

Example:
```python
qry, _ = Select(PgSqlDialect()).from_("foo").order('id').assemble()
# output: SELECT "foo".* FROM "foo" ORDER BY id ASC
print(qry)

qry, _ = Select(PgSqlDialect()).from_("foo").order(['id', 'name'], Select.ORDER_DESC).assemble()
# output: SELECT "foo".* FROM "foo" ORDER BY id DESC, a DESC
print(qry)
```

### Select.**where(field, operator=None, value=None)**

Adds a **WHERE** clause. Multiple calls to this method are concatenated with **AND**. *field* must contain a valid  
[Field identifier](#field-identifier), *operator* can contain either a string with an operator or a [Literal](literal.md)
object, and finally *value*, if specified, is the operand.

Example:
```python
# showcase multiple WHERE... AND clauses
qry = Select(PgSqlDialect()).from_("foo").\
    where('id', '>', 5).\
    where('name', 'IS NOT NULL').\
    where('cp', 'IN', [100,200,300,400])

# output: ('SELECT "foo".* FROM "foo" WHERE ("id" > %s) AND ("name" IS NOT NULL) AND ("cp" IN %s)', [5, [100, 200, 300, 400]])
print(qry.assemble())
```

#### Field identifier

A field identifier can be a string with a field name, a [Literal](literal.md) object, a {'table':'field'} dict or 
{<record_class_or_object>:'field'} dict.


### Select.**where_and()**

Starts a parenthesis **AND** block within the **WHERE** clause, allowing the build of complex **WHERE** clauses. This method
is nestable, allowing the composition of multi-level parenthesis blocks. All declared blocks need to be explicitly closed
with [where_end()](#selectwhere_end).

Example:
```python
# showcase WHERE clause AND ( clause OR clause)
qry = Select(PgSqlDialect()).from_("foo").\
    where('id', '>', 5).\
    where_and().\
    where('name', 'IS NOT NULL').\
    orwhere('cp', 'IN', [100,200,300,400]).\
    where_end()

# output: ('SELECT "foo".* FROM "foo" WHERE ("id" > %s) AND ( ("name" IS NOT NULL) OR ("cp" IN %s) )', [5, [100, 200, 300, 400]])
print(qry.assemble())

```

### Select.**where_or()**

Starts a parenthesis **OR** block within the **WHERE** clause, allowing the build of complex **WHERE** clauses. This method
is nestable, allowing the composition of multi-level parenthesis blocks. All declared blocks need to be explicitly closed
with [where_end()](#selectwhere_end).

Example:
```python
# showcase WHERE clause OR ( clause AND clause)
qry = Select(PgSqlDialect()).from_("foo").\
    where('id', '>', 5).\
    where_or().\
    where('name', 'IS NOT NULL').\
    where('cp', 'IN', [100,200,300,400]).\
    where_end()

# output: ('SELECT "foo".* FROM "foo" WHERE ("id" > %s) OR ( ("name" IS NOT NULL) AND ("cp" IN %s) )', [5, [100, 200, 300, 400]])
print(qry.assemble())

```

### Select.**where_end()**

Closes a parenthesis **AND** or **OR** block. Please note, to allow the most freedom when building queries,
Validation of open/closed blocks is only performed on *assemble()*. If the internal open block counter is not 0 on *assemble()*,
a *RuntimeError* is raised. 

See [where_and()](#selectwhere_and) and [where_or()](#selectwhere_or) for usage examples.


### Select.**orwhere(field, operator=None, value=None)**

Adds a **WHERE** clause to be concatenated with **OR**.*field* must contain a valid  
[Field identifier](#field-identifier), *operator* can contain either a string with an operator or a [Literal](literal.md)
object, and finally *value*, if specified, is the operand.

Example:
```python
# showcase multiple WHERE... AND clauses
qry = Select(PgSqlDialect()).from_("foo").\
    where('id', '>', 5).\
    orwhere('name', 'IS NOT NULL').\
    where('cp', 'IN', [100,200,300,400])

# output: ('SELECT "foo".* FROM "foo" WHERE ("id" > %s) OR ("name" IS NOT NULL) AND ("cp" IN %s)', [5, [100, 200, 300, 400]])
print(qry.assemble())
```

### Select.**group(fields)**

Adds a **GROUP BY** clause. **fields** can be either a field name, a list of field names, a [Literal](literal.md) or a 
list of [Literal](literal.md) objects.

Example:
```python
qry, _ = Select(PgSqlDialect()).from_("foo").group(['age', 'name']).assemble()

# output: SELECT "foo".* FROM "foo" GROUP BY "age", "name"
print(qry)
```

### Select.**having(field, operator=None, value=None, schema=None)**

Adds a **HAVING** clause. **field** can be a field name, a [Literal](literal.md), a {'table':'field'} dict or a
{[Record](record.md) class or object:'field'} dict.

Example:
```python
# HAVING Literal condition
qry, _ = Select(PgSqlDialect()).from_("foo").having(Literal('COUNT(field) > 5')).assemble()
# output: SELECT "foo".* FROM "foo" HAVING (COUNT(field) > 5)
print(qry)

# HAVING condition
qry, _ = Select(PgSqlDialect()).from_("foo").having('field', '>', 5, 'public').assemble()
# output: SELECT "foo".* FROM "foo" HAVING ("field" > %s)
print(qry)

# HAVING with schema
qry, _ = Select(PgSqlDialect()).from_("foo").having({'some_table':'field'}, '>', 5, 'public').assemble()
# output: SELECT "foo".* FROM "foo" HAVING ("public"."some_table"."field" > %s)
print(qry)
```

### Select.**union(queries: list, union_type: str = Sql.SQL_UNION)**

Performs an **UNION** of two or more Select() or string queries. *union_type* can be either *Sql.SQL_UNION* or *Sql.SQL_UNION_ALL*.

Example:

```python
qry, _ = Select(PgSqlDialect()).union([
    Select().from_('table'),
    Select().from_('other_table')]). \
    assemble()

# output: SELECT "table".* FROM "table" UNION SELECT "other_table".* FROM "other_table"
print(qry)
```

### Select.**join(table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None, expr_schema=None)**
  
Adds a **INNER JOIN** clause. The parameters must conform with [join() parameters](#join-parameters).

Example:

```python
# simple example
qry, _ = Select(PgSqlDialect()).from_('some_table').\
    join('other_table', 'fk_some_table', 'some_table', 'id').\
    assemble()

# output: SELECT "some_table".* FROM "some_table" INNER JOIN "other_table" ON "some_table"."id"="other_table"."fk_some_table"
print(qry)

# example w/ destination table aliasing
qry, _ = Select(PgSqlDialect()).from_('some_table').\
    join({'other_table': 't2'}, 'fk_some_table', 'some_table', 'id').\
    assemble()

# output: SELECT "some_table".* FROM "some_table" INNER JOIN "other_table" AS "t2" ON "some_table"."id"="t2"."fk_some_table"
print(qry)

# example w/ source table aliasing
qry, _ = Select(PgSqlDialect()).from_({'some_table': 't1'}).\
    join({'other_table': 't2'}, 'fk_some_table', {'some_table':'t1'}, 'id').\
    assemble()
# output: SELECT "t1".* FROM "some_table" AS "t1" INNER JOIN "other_table" AS "t2" ON "t1"."id"="t2"."fk_some_table"
print(qry)

# example w/ Record objects and extra SELECT column w/alias
qry, _ = Select(PgSqlDialect()).from_(Book).\
    join(Publisher, Publisher.id, Book, Book.fk_publisher, '=', [{Publisher.name: 'publisher_name'}]).assemble()
# output: SELECT "book".*,"publisher"."name" AS "publisher_name" FROM "book" INNER JOIN "publisher" ON "book"."fk_publisher"="publisher"."id_publisher"
print(qry)
```

#### join() parameters

*table* identifies the table to **JOIN** to, and must be a valid [Table identifier](#table-identifier)
expression. 

*field* is the field name or expression to join on *table*. 

*expr_table* identifies the existing table to **JOIN** from, and must be a valid [Table identifier](#table-identifier). 

*expr_field* is the field name or expression to **JOIN** on the existing table. 

*operator* is an optional join operator - if omitted, *'='* is used. 

*cols* is an optional list of column names to add to the **SELECT** statement. 

*schema* and *expr_schema* can provide optional schema naming for both table to JOIN to and table to JOIN from.

### Select.**join_inner(table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None, expr_schema=None)**
  
Alias to [join()](#selectjointable-field-expr_tablenone-expr_fieldnone-operatornone-colsnone-schemanone-expr_schemanone).


### Select.**join_left(table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None, expr_schema=None)**

Adds a **LEFT JOIN** clause. The parameters must conform with [join() parameters](#join-parameters).

Example:

```python
# simple example
qry, _ = Select(PgSqlDialect()).from_('some_table').\
    join_left('other_table', 'fk_some_table', 'some_table', 'id').\
    assemble()

# output: SELECT "some_table".* FROM "some_table" LEFT JOIN "other_table" ON "some_table"."id"="other_table"."fk_some_table"
print(qry)

# example w/ destination table aliasing
qry, _ = Select(PgSqlDialect()).from_('some_table').\
    join_left({'other_table': 't2'}, 'fk_some_table', 'some_table', 'id').\
    assemble()

# output: SELECT "some_table".* FROM "some_table" LEFT JOIN "other_table" AS "t2" ON "some_table"."id"="t2"."fk_some_table"
print(qry)

# example w/ source table aliasing
qry, _ = Select(PgSqlDialect()).from_({'some_table': 't1'}).\
    join_left({'other_table': 't2'}, 'fk_some_table', {'some_table':'t1'}, 'id').\
    assemble()

# output: SELECT "t1".* FROM "some_table" AS "t1" LEFT JOIN "other_table" AS "t2" ON "t1"."id"="t2"."fk_some_table"
print(qry)

# example w/ Record objects and extra SELECT column w/alias
qry, _ = Select(PgSqlDialect()).from_(Book).\
    join_left(Publisher, Publisher.id, Book, Book.fk_publisher, '=', [{Publisher.name: 'publisher_name'}]).assemble()

# output: SELECT "book".*,"publisher"."name" AS "publisher_name" FROM "book" LEFT JOIN "publisher" ON "book"."fk_publisher"="publisher"."id_publisher"
print(qry)
```

### Select.**join_right(table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None, expr_schema=None)**

Adds a **RIGHT JOIN** clause. The parameters must conform with [join() parameters](#join-parameters).

Example:

```python
# simple example
qry, _ = Select(PgSqlDialect()).from_('some_table').\
    join_right('other_table', 'fk_some_table', 'some_table', 'id').\
    assemble()

# output: SELECT "some_table".* FROM "some_table" RIGHT JOIN "other_table" ON "some_table"."id"="other_table"."fk_some_table"
print(qry)

# example w/ destination table aliasing
qry, _ = Select(PgSqlDialect()).from_('some_table').\
    join_right({'other_table': 't2'}, 'fk_some_table', 'some_table', 'id').\
    assemble()

# output: SELECT "some_table".* FROM "some_table" RIGHT JOIN "other_table" AS "t2" ON "some_table"."id"="t2"."fk_some_table"
print(qry)

# example w/ source table aliasing
qry, _ = Select(PgSqlDialect()).from_({'some_table': 't1'}).\
    join_right({'other_table': 't2'}, 'fk_some_table', {'some_table':'t1'}, 'id').\
    assemble()

# output: SELECT "t1".* FROM "some_table" AS "t1" RIGHT JOIN "other_table" AS "t2" ON "t1"."id"="t2"."fk_some_table"
print(qry)

# example w/ Record objects and extra SELECT column w/alias
qry, _ = Select(PgSqlDialect()).from_(Book).\
    join_right(Publisher, Publisher.id, Book, Book.fk_publisher, '=', [{Publisher.name: 'publisher_name'}]).assemble()

# output: SELECT "book".*,"publisher"."name" AS "publisher_name" FROM "book" RIGHT JOIN "publisher" ON "book"."fk_publisher"="publisher"."id_publisher"
print(qry)
```

### Select.**join_full(table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None, expr_schema=None)**

Adds a **FULL OUTER JOIN** clause. The parameters must conform with [join() parameters](#join-parameters).

Example:

```python
# simple example
qry, _ = Select(PgSqlDialect()).from_('some_table').\
    join_full('other_table', 'fk_some_table', 'some_table', 'id').\
    assemble()

# output: SELECT "some_table".* FROM "some_table" FULL JOIN "other_table" ON "some_table"."id"="other_table"."fk_some_table"
print(qry)

# example w/ destination table aliasing
qry, _ = Select(PgSqlDialect()).from_('some_table').\
    join_full({'other_table': 't2'}, 'fk_some_table', 'some_table', 'id').\
    assemble()

# output: SELECT "some_table".* FROM "some_table" FULL JOIN "other_table" AS "t2" ON "some_table"."id"="t2"."fk_some_table"
print(qry)

# example w/ source table aliasing
qry, _ = Select(PgSqlDialect()).from_({'some_table': 't1'}).\
    join_full({'other_table': 't2'}, 'fk_some_table', {'some_table':'t1'}, 'id').\
    assemble()

# output: SELECT "t1".* FROM "some_table" AS "t1" FULL JOIN "other_table" AS "t2" ON "t1"."id"="t2"."fk_some_table"
print(qry)

# example w/ Record objects and extra SELECT column w/alias
qry, _ = Select(PgSqlDialect()).from_(Book).\
    join_full(Publisher, Publisher.id, Book, Book.fk_publisher, '=', [{Publisher.name: 'publisher_name'}]).assemble()

# output: SELECT "book".*,"publisher"."name" AS "publisher_name" FROM "book" FULL JOIN "publisher" ON "book"."fk_publisher"="publisher"."id_publisher"
print(qry)
```

### Select.**join_cross(table, cols=None, schema=None)**

Adds a **CROSS JOIN** clause. *table* identifies the table to **CROSS JOIN** with, and must be a valid [Table identifier](#table-identifier)
expression. *cols* a list of field names to be *SELECT*ed from the joined table. *schema* is the optional schema name
for the joined table.

Example:

```python
# simple example
qry, _ = Select(PgSqlDialect()).from_('table1').\
    join_cross('table2').\
    assemble()

# output: SELECT "table1".* FROM "table1" CROSS JOIN "table2"
print(qry)

# example w/ destination table aliasing
qry, _ = Select(PgSqlDialect()).from_('table1').\
    join_cross({'table2': 't2'}).\
    assemble()

# output: SELECT "table1".* FROM "table1" CROSS JOIN "table2" AS "t2"
print(qry)

# example w/ destination table aliasing and extra SELECT columns
qry, _ = Select(PgSqlDialect()).from_('table1').\
    join_cross({'table2': 't2'}, [{'id':'t2_id'}, 'name']).\
    assemble()

# output: SELECT "table1".*,"t2"."id" AS "t2_id","t2"."name" FROM "table1" CROSS JOIN "table2" AS "t2"
print(qry)

# example w/ Record objects and extra SELECT columns
qry, _ = Select(PgSqlDialect()).from_(Book).\
    join_cross(Publisher, [Publisher.id, Publisher.name]).\
    assemble()

# output: SELECT "book".*,"publisher"."id_publisher","publisher"."name" FROM "book" CROSS JOIN "publisher"
print(qry)
```

### Select.**join_natural(table, cols=None, schema=None)**

Adds a **CROSS JOIN** clause. *table* identifies the table to **CROSS JOIN** with, and must be a valid [Table identifier](#table-identifier)
expression. *cols* a list of field names to be *SELECT*ed from the joined table. *schema* is the optional schema name
for the joined table.

Example:

```python
# simple example
qry, _ = Select(PgSqlDialect()).from_('table1').\
    join_natural('table2').\
    assemble()

# output: SELECT "table1".* FROM "table1" NATURAL JOIN "table2"
print(qry)

# example w/ destination table aliasing
qry, _ = Select(PgSqlDialect()).from_('table1').\
    join_natural({'table2': 't2'}).\
    assemble()

# output: SELECT "table1".* FROM "table1" NATURAL JOIN "table2" AS "t2"
print(qry)

# example w/ destination table aliasing and extra SELECT columns
qry, _ = Select(PgSqlDialect()).from_('table1').\
    join_natural({'table2': 't2'}, [{'id':'t2_id'}, 'name']).\
    assemble()

# output: SELECT "table1".*,"t2"."id" AS "t2_id","t2"."name" FROM "table1" NATURAL JOIN "table2" AS "t2"
print(qry)

# example w/ Record objects and extra SELECT columns
qry, _ = Select(PgSqlDialect()).from_(Book).\
    join_natural(Publisher, [Publisher.id, Publisher.name]).\
    assemble()

# output: SELECT "book".*,"publisher"."id_publisher","publisher"."name" FROM "book" NATURAL JOIN "publisher"
print(qry)
```

### Select.**assemble()**

Assembles and returns the SQL query string and list of values. Returns a tuple with (sql_query, list_of_values) . If no
values are present, an empty list is returned instead. It will raise *RuntimeError* on existing errors.

Example:

```python
qry, _ = Select(PgSqlDialect()).expr([1]).assemble()

# output: SELECT 1
print(qry)
```

### Select.**dialect()**

Return the current [SqlDialect](sqldialect.md) object in use.
