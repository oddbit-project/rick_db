# rick_db.Repository

## Class BaseRepository

Internal top-level repository type.

### BaseRepository.**backend()**

Return the internal [Connection](connection.md) object.

### BaseRepository.**dialect()**

Return the internal [SqlDialect](sqldialect.md) object used by the current connection.

## Class Repository(BaseRepository)

The parent Repository class implementation, to be extended to implement specific Record repositories.

### **Repository(db, record_type)**

Repository constructor. Receives a [Connection](connection.md) object, *db*, and a [Record](record.md) class, *record_type*.
The *record_type* class will provide the schema, table name and primary key information, and be used as a data type for
methods that return records or collections.


### Repository.**select(cols=None)**

Return a [Select](select.md) query builder instance for the current table, with an optional column list, *cols*.


### Repository.**fetch_pk(pk_value)**

Attempt to read a record  from the database by primary key value. It will return a record of the defined record_type on 
success, None if no record exists. Will raise **RepositoryError** if the record_type doesn't have a primary key definition.

Example:
```python
(...)
# try to fetch record with pk=32
record = repo.fetch_pk(32)
if record is not None:
    print("record 32 exists")
```

### Repository.**fetch_one(qry: Select)**

Execute the *qry* [Select](select.md) statement and return a single record. If there is no record to return, will return None.

Example:
```python
(...)
# fetch record if exists, else returns None
user = repo.fetch_one(repo.select().where('login', '=', 'gandalf@lotr'))
```

### Repository.**fetch(qry: Select, cls=None)**

Execute the *qry* [Select](select.md) statement and return a list of records. If there is nothing to return, will return
and empty list. If a record class is specified in *cls*, this class will be used as record_type instead of the repository
definition. This is useful to e.g. return join results that may return a different record type. 

Example:
```python
(...)
# fetch a list of records from a query
for r in repo.fetch(repo.select().where('name', 'like', 'gandalf%')):
    print(r.name)
```

### Repository.**fetch_raw(qry: Select)**

Execute the *qry* [Select](select.md) statement, but no record conversion is performed on the result - it will return 
the raw result dataset, a collection of dict-like structures, from the database connection. If there is nothing to return, will return
and empty list. 

Example:
```python
(...)
# fetch a list of records from a query
for r in repo.fetch_raw(repo.select().where('name', 'like', 'gandalf%')):
    print(r['name'])
```

### Repository.**fetch_by_field(field, value, cols=None)**

Fetch a list of rows where field matches a value. An optional list of fields to be returned can be defined with *cols*.
It returns a record list, or an empty list if no match is found.

Example:
```python
(...)
# fetch records where login='gandalf@lotr'
user = repo.fetch_by_field('login', 'gandalf@lotr')
```

### Repository.**fetch_where(where_clauses: list, cols=None)**

Fetch a list of rows that match a list of **WHERE** clauses. If more than one clause is present, they are concatenated
with **AND**.  An optional list of fields to be returned can be defined with *cols*.  It returns a record list, or an 
empty list if no match is found.

A where clause is a list of tuples in the form of *(field, operator, value)*. See the example below for more details.

Example:
```python
(...)
# fetch 'name' field from records matching a where clause 
for r in repo.fetch_where([('name', 'like', 'gandalf%'), ], cols=['name']):
    print(r.name)
```

### Repository.**fetch_all()**

Fetch all rows; equivalent to a **SELECT * FROM <record_type_table>**. It returns a record list, or an empty list if 
the table is empty.

Example:
```python
(...)
# fetch all records 
for r in repo.fetch_all():
    print(r.name)
```

### Repository.**insert(record, cols=None)**

Insert a new record, optionally returning values. If the database does not support INSERT...RETURNING, *cols* can only
have one entry, and the primary key will be returned regardless of the actual field name.

Example:
```python
# insert a new record, returns None
repo.insert(Character(name="John Connor"))

# insert a new record, returns a record with id filled
record = repo.insert(Character(name="Sarah Connor"), cols=['id'])
if record is not None:
    print(record.id)
```

### Repository.**insert_pk(record)**

Insert a new record and return the primary key value, or None if database doesn't return any value. If no primary key 
is defined, will raise **RepositoryError**. 

Example:
```python
# insert a new record, returns a record with id filled
id = repo.insert_pk(Character(name="John Connor"))
if id is not None:
    print(id)
```

### Repository.**delete_pk(pk_value)**

Remove a record identified by primary key value.  If no primary key is defined, will raise **RepositoryError**. 

Example:
```python
# remove record #32
repo.delete_pk(32)
```


### Repository.**delete_where(where_clauses: list)**

Remove records matching a list of **WHERE** clauses. If more than one clause is present, they are concatenated
with **AND**.

A where clause is a list of tuples in the form of *(field, operator, value)*. See the example below for more details.

Example:
```python
# remove records WHERE name='gandalf' AND name='frodo'
repo.delete_where([('name', '=', 'gandalf'), ('name', '=', 'frodo')])
```

### Repository.**map_result_id(result: list)**

Transform a list of records into a dict indexed by primary key. If no primary key is defined, raises **RepositoryError**.

Example:
```python
records = [
    Character(id=1, name="John Connor"),
    Character(id=2, name="Sarah Connor"),
]

# idx_records = { 1: Character(id=1, name="John Connor"), 2: Character(id=2, name="Sarah Connor") } 
idx_records = repo.map_result_id(records)

```

### Repository.**valid_pk(pk_value)**

Returns True if a row exists with a primary key value matching *pk_value*, or False otherwise. If no primary key is
defined, raises **RepositoryError**.

Example:
```python
if repo.valid_pk(32):
    # record with pk=32 exists
    (...)
```

### Repository.**exec(sql, values=None, cls=None, useCls=True)**

Execute a raw SQL query. Query values must be passed via *values*. If *useCls* is True (default), returned database rows
are converted to a list of records. If a Record class is specified via *cls*, it will be used instead of the internal
record_type for record serialization.

Example:
```python
for r in repo.exec('SELECT * FROM characters WHERE id=%s', [32,]):
    print(r.name)
```

### Repository.**exists(field, value, pk_to_skip)**

Returns True if a record exists **WHERE field=value AND primary_key <> pk_to_skip**. If no primary key is
defined, raises **RepositoryError**. This is useful to check for uniqueness.

Example:
```python
can_update = repo.exists('login', 'gandalf@lotr', 32)
if not can_update:
    print("A record already exists with the same login value")
```

### Repository.**update(record, pk_value=None)**

Updates a record on the database by primary key. If *record* contains a primary key value, it will be used instead 
of *pk_value*. If *record* doesn't contain a primary key value, *pk_value* is required.

Example:
```python
record = Character(name='T-1000')
repo.update(record, 2)
```

### Repository.**update_where(record, where_list: list)**

Updates a record matching a list of **WHERE** clauses defined by *where_list*.  If more than one clause is present, 
they are concatenated with **AND**.

A where clause is a list of tuples in the form of *(field, value)* or *(field, operator, value)*.  See the example 
below for more details. 

Example:
```python
record = Character(name='T-1000')
repo.update(record, [('name', 'John Connor')])
```

### Repository.**count()**

Returns the number of records in the table. Equivalent of **SELECT COUNT(1) FROM <table_name>**. 

Example:
```python
record = Character(name='T-1000')
total = repo.count()
```

### Repository.**count_where(where_list: list)**

Returns the number of records matching a list of **WHERE** clauses. If more than one clause is present, 
they are concatenated with **AND**.

A where clause is a list of tuples in the form of *(field, value)* or *(field, operator, value)*.  See the example 
below for more details. 

Example:
```python
total_johns = repo.count_where([('name', 'like', 'John %'), ])
```

### Repository.**list(qry: Select, limit=None, offset=None, cls=None)**

Performs a query *qry*, with an optional *offset* and *limit*, and returns a tuple with the total row count for the query
(without offset and limit applied), and a list of rows returned from the execution of the query with offset and limit.

If a Record class *cls* is specified, it will be used instead of the predefined *record_type*.

Note: The original *qry* object is left intact.

Example:
```python
total_records, recordset = repo.list(repo.Select(), 10)
```

