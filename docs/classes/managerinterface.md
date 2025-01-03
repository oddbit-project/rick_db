# Class rick_db.**ManagerInterface**

The ManagerInterface provides a common interface to [PgManager](pgmanager.md) and [Sqlite3Manager](sqlite3manager.md) 
classes, exposing common management methods.

### ManagerInterface.**conn()**

Returns a [Connection](connection.md) using a context manager; the connection is automatically disposed (if required)
when context exits.

### ManagerInterface.**backend()**

Returns the current active backend, either a [Connection](connection.md) object, or a [PoolInterface](poolinterface.md)
object.

### ManagerInterface.**tables(schema=None)**

Returns a list of existing table names, optionally on a specific *schema*. 

### ManagerInterface.**views(schema=None)**

Returns a list of existing view names, optionally on a specific *schema*. 

### ManagerInterface.**schemas()**

Returns a list of existing schema names. 

### ManagerInterface.**database()**

Returns a list of existing database names. 

### ManagerInterface.**table_indexes(table_name:str, schema=None)**

Returns a list of [FieldRecord](fieldrecord.md) with fields that are indexed on the specified table.

### ManagerInterface.**table_pk(table_name:str, schema=None)**

Returns a [FieldRecord](fieldrecord.md) with details of the primary key, or None if no primary key exists.

### ManagerInterface.**table_fields(table_name:str, schema=None)**

Returns a list of [FieldRecord](fieldrecord.md) with details of all the fields of the specified table.

### ManagerInterface.**view_fields(view_name:str, schema=None)**

Returns a list of [FieldRecord](fieldrecord.md) with details of all the fields of the specified view.

### ManagerInterface.**users()**

Returns a list of [UserRecord](userrecord.md) with details of all the users of the database;

### ManagerInterface.**user_groups(user_name:str)**

Returns a string list  of all groups associated with a given user.

### ManagerInterface.**table_exists(table_name:str, schema=None)**

Returns True if the specified table exists.

### ManagerInterface.**view_exists(view_name:str, schema=None)**

Returns True if the specified view exists.

### ManagerInterface.**create_database(database_name:str, **kwargs)**

Creates a new database with the specified name and optional arguments.

### ManagerInterface.**database_exists(database_name:str)**

Returns True if the specified database exists.

### ManagerInterface.**drop_database(database_name:str)**

Removes the specified database.

### ManagerInterface.**create_schema(schema:str, **kwargs)**

Creates a new schema with the specified name and options in the current database.

### ManagerInterface.**schema_exists(schema:str)**

Returns True if the specified schema exists.

### ManagerInterface.**drop_schema(schema:str, cascade=False)**

Removes the specified schema, optionally cascading.

### ManagerInterface.**kill_clients(database_name:str)**

Kill all clients for the specified database.

### ManagerInterface.**drop_table(table_name: str, cascade=False, schema=None)**

Attempts to remove the specified table, optionally cascading.


### ManagerInterface.**drop_view(view_name: str, cascade=False, schema=None)**

Attempts to remove the specified view, optionally cascading.