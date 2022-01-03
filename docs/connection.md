# Connection

The connection object provides high-level methods to interact with the database, including cursor and transaction support,
as well as a profiler. For more information on available methods, see [Connection](classes/connection.md).

## Connecting to PostgreSQL

There are three PostgreSQL connectors available; however, it is advisable to use the regular **PgConnection** with an external
connection pool, such as [pgpool](https://www.pgpool.net/) or equivalent.

Available connection parameters:

|Field| Connector | Description  |
|---|---|---|
|dbname| All | Database Name|
|user| All | User name used to authenticate|
|password| All | Password used to authenticate|
|host| All| Database host (defaults to UNIX socket if not provided|
|port| All | Connection port (defaults to 5432 if not provided |
|sslmode|All | *SSL negotiation type: disable, allow, prefer, require|
|minconn|PgConnectionPool, PgThreadedConnectionPool| Minimum number of connections to keep, defaults to 5 if not provided|
|maxconn|PgConnectionPool, PgThreadedConnectionPool| Maximum number of connections to keep, defaults to 5 if not provided|

*More details on sslmode operation are available in the [libpq documentation](https://www.postgresql.org/docs/current/libpq-ssl.html). 


Using PgConnection:

```python
from rick_db.conn.pg import PgConnection

config = {
    'dbname': 'my_database',
    'user': '<some_user>',
    'password': '<some_password>',
    'host': 'localhost',
    'port': 5432,
    'sslmode': 'require'    
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
    'minconn': 4,
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
    'minconn': 4,
}

# create connection
conn = PgThreadedConnectionPool(**config)
```

## Connecting to SQLite

Available connection parameters:

|Field|  Description  |
|---|---|
|db_file| Database file|
|isolation_level| Optional isolation level; defaults to empty if not provided|
|timeout| Timeout in seconds; defaults to 5.0 if not provided|

Example:
```python
from rick_db.conn.sqlite import Sqlite3Connection

# create or open a sqlite database
conn = Sqlite3Connection('my_database.db')
```

## Using a profiler

RickDb provides a simple profiler interface that allows logging of queries, parameters and execution times, as well
as a simple in-memory profiler implementation, [DefaultProfiler](classes/profiler.md#class-rick_dbprofilerdefaultprofiler).

To use a [DefaultProfiler](classes/profiler.md#class-rick_dbprofilerdefaultprofiler) instance on a connection,
just assign the desired instance to the **profiler** property:

```python
from rick_db.conn.pg import PgConnection
from rick_db.profiler import DefaultProfiler

db_cfg = {
    'dbname': "rick_test",
    'user': "rickdb_user",
    'password': "rickdb_password",
    'sslmode': 'require'
}

conn = PgConnection(**db_cfg)
# instantiate profiler, and use it on conn object
conn.profiler = DefaultProfiler()

# perform some queries we can profile
with conn.cursor() as c:
    c.exec("SELECT 1")

# output: SELECT 1 0.00012579001486301422
for evt in conn.profiler.get_events():
    print(evt.query, evt.elapsed)
```
