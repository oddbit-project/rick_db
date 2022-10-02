# Class rick_db.conn.**Connection**

Base connection class for all database connections.

### @property Connection.**profiler**

Get or set the current profiler. By default, a connection is initialized with
a [NullProfiler](profiler.md#class-rick_dbprofilernullprofiler). Check
[Profiler](profiler.md#rick_dbprofiler) for details on the return type.

### Connection.**dialect()**

Retrieve connection dialect. Check [SqlDialect](sqldialect.md) for more details on the return type.

### Connection.**begin()**

Starts a database transaction. Raises **ConnectionError** exception if autocommit is enabled or a transaction is already
opened.

### Connection.**commit()**

Finishes (commit) a database transaction.

### Connection.**rollback()**

Cancels (rollback) a database transaction.

### Connection.**transaction_status()**

Returns true if there is a started database transaction.

### Connection.**cursor()**

Initializes and returns a new [Cursor](cursor.md) object.

### Connection.**backend()**

Retrieve the underlying database connection object.

### Connection.**migration_manager()**

Retrieve the appropriate MigrationManager object instance for the current connection. The MigrationManager
object can be used to manage database migrations.

### Connection.**metadata()**

Retrieve the appropriate Metadata object instance for the current connection. The Metadata object can be used
to list internal database structures, such as tables, views, schemas and users.

### Connection.**close()**

Close database connection. If there is a started database transaction, the transaction will be cancelled.


