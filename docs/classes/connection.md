# Class rick_db.**Connection**

Base connection class for all database connections.

### @property Connection.**profiler**

Get or set the current profiler. By default, a connection is initialized with
a [NullProfiler](profiler.md#class-rick_dbprofilernullprofiler). Check [Profiler](profiler.md#rick_dbprofiler) for details on the return type.

### Connection.**dialect()**

Retrieve connection dialect. Check [SqlDialect](sqldialect.md) for more details on the return type.

## Connection.**get_cursor()**

Initializes and returns a new [Cursor](cursor.md) object.

## Connection.**cursor()**

Creates a new [Cursor](cursor.md)  and returns it as a contextmanager

### Connection.**begin()**

Starts a database transaction. Raises **ConnectionError** exception if autocommit is enabled or a transaction is already
opened.

### Connection.**commit()**

Finishes (commit) a database transaction.

### Connection.**rollback()**

Cancels (rollback) a database transaction.

### Connection.**in_transaction()**

Returns true if there is a started database transaction.

### Connection.**close()**

Close database connection. If there is a started database transaction, the transaction will be cancelled.
