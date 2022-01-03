# Class rick_db.sql.**Insert**

### Insert.**\_\_init\_\_(dialect: SqlDialect = None)**

Initialize a Insert() object, using a database *dialect*. If no *dialect* is provided, a default dialect will be used.
Check [SqlDialect](sqldialect.md) for more details.

### Insert.**into(table, schema=None)**

Defines the target *table* name and *schema*. If *table* is a [Record](record.md) object, it will also load fields and
values from this object.

Example:
```python
# simple INSERT example
qry = Insert(PgSqlDialect()).into('table').fields(['field']).values(['value'])
# output: ('INSERT INTO "table" ("field") VALUES (%s)', ['value'])
print(qry.assemble())

# INSERT w/ Record object
record = Publisher(name='some publisher name')
qry = Insert(PgSqlDialect()).into(record)
# output: ('INSERT INTO "publisher" ("name") VALUES (%s)', ['some publisher name'])
print(qry.assemble())
```

### Insert.**fields(fields: list)**

Defines the field names for insertion. The length of *fields* list must match the list of provided values.

Example:
```python
data = [
    ['john', 'connor'],
    ['sarah', 'connor']
]
sql = []
qry = Insert(PgSqlDialect()).into('table').fields(['name', 'surname'])
for v in data:
    qry.values(v)
    sql.append(qry.assemble())

# output: 
# [('INSERT INTO "table" ("name", "surname") VALUES (%s, %s)', ['john', 'connor']), 
# ('INSERT INTO "table" ("name", "surname") VALUES (%s, %s)', ['sarah', 'connor'])]
print(sql)
```

### Insert.**values(values: Union[list, dict, object])**

Define values to be inserted. This method can be called multiple times (see [fields()](#insertfieldsfields-list) for an
example). If *values* is a dict, both fields and values are read from the provided dict. If *values* is a [Record](record.md)
object, fields and values are read from the object.

Example:
```python
# simple INSERT example
qry = Insert(PgSqlDialect()).into('table').fields(['field']).values(['value'])
# output: ('INSERT INTO "table" ("field") VALUES (%s)', ['value'])
print(qry.assemble())

# INSERT w/ Record object
record = Publisher(name='some publisher name')
qry = Insert(PgSqlDialect()).into('tablename').values(record)
# output: ('INSERT INTO "tablename" ("name") VALUES (%s)', ['some publisher name'])
print(qry.assemble())
```

### Insert.**returning(fields)**

Adds a **RETURNING** clause to the **INSERT**. *fields* is a string or list of field names to be returned.

Example:

```python
# simple INSERT example
qry = Insert(PgSqlDialect()).into('tablename').fields(['field']).values(['value']).returning(['id', 'field'])
# output: ('INSERT INTO "tablename" ("field") VALUES (%s) RETURNING "id", "field"', ['value'])
print(qry.assemble())

# INSERT w/ Record object
record = Publisher(name='some publisher name')
qry = Insert(PgSqlDialect()).into('tablename').values(record).returning('id')
# output: ('INSERT INTO "tablename" ("name") VALUES (%s) RETURNING "id"', ['some publisher name'])
print(qry.assemble())
```

### Insert.**get_values()**

Returns list of current values.

Example:

```python
qry = Insert(PgSqlDialect()).into('tablename').fields(['field']).values(['value'])
# output: ['value']
print(qry.get_values())
```

### Insert.**assemble()**

Assembles **INSERT** SQL string and returns a tuple with (sql_string, list_of_values). If an error occurs, *SqlError* is raised.

Example:

```python
# simple INSERT example
qry = Insert(PgSqlDialect()).into('table').fields(['field']).values(['value'])
# output: ('INSERT INTO "table" ("field") VALUES (%s)', ['value'])
print(qry.assemble())
```
