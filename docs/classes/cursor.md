# Class rick_db.**Cursor**

Provides cursor logic in a database-independent fashion.

### @property Cursor.**conn**

Exposes the underlying connection used to create the Cursor object.

### @property Cursor.**cursor**

Exposes the internal cursor object, from the connection adapter.

### @property Cursor.**profiler**

Exposes the current [Profiler](profiler.md#rick_dbprofiler)  object in use by the Cursor.

### Cursor.**exec(qry: str, params=None, cls=None)**

Executes a SQL query specified in *qry*, with optional parameter list *params*. If *cls*, the specified class will be used
to return objects via Object Mapper. The query may or may not return a result.

### Cursor.**fetchone(qry: str, params=None, cls=None)**

Executes a SQL query specified in *qry*, with optional parameter list *params* and optional Object Mapper class defined via 
*cls*. It will return a single result or None

### Cursor.**fetchall(qry: str, params=None, cls=None)**

Executes a SQL query specified in *qry*, with optional parameter list *params* and optional Object Mapper class defined via 
*cls*. It will always return a list. If no records are to be returned, the list will be empty.

### Cursor.**lastrowid()**

Returns the last inserted id; if not supported, returns None

### Cursor.**close()**

Closes current cursor.
