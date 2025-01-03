# Connection

The connection object provides high-level methods to interact with the database, including cursor and transaction support,
as well as a profiler. For more information on available methods, see [Connection](classes/connection.md).

## Connecting to PostgreSQL

There are two PostgreSQL connectors available - a simple connector and a thread-safe connection pool; the recommended 
usage is to use **PgConnectionPool**.

Available connection parameters:

|Field| Connector | Description                                                           |
|---|---|-----------------------------------------------------------------------|
|dbname| All | Database Name                                                         |
|user| All | User name used to authenticate                                        |
|password| All | Password used to authenticate                                         |
|host| All| Database host (defaults to UNIX socket if not provided                |
|port| All | Connection port (defaults to 5432 if not provided                     |
|sslmode|All | *SSL negotiation type: disable, allow, prefer, require                |
|minconn|PgConnectionPool| Minimum number of connections to keep, defaults to 5 if not provided  |
|maxconn|PgConnectionPool| Maximum number of connections to keep, defaults to 25 if not provided |

*More details on sslmode operation are available in the [libpq documentation](https://www.postgresql.org/docs/current/libpq-ssl.html). 


Using PgConnection:

```python
from rick_db.backend.pg import PgConnection

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
with conn.cursor() as c:
    # to stuff
```

Using PgConnectionPool:

```python
from rick_db.backend.pg import PgConnectionPool

config = {
    'dbname': 'my_database',
    'user': '<some_user>',
    'password': '<some_password>',
    'host': 'localhost',
    'port': 5432,
    'minconn': 4,
}

# create connection
pool = PgConnectionPool(**config)
with pool.connection() as conn:     # fetch a connection from the pool
    with conn.cursor() as c:        # create a cursor
        # to stuff
        pass
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
from rick_db.backend.sqlite import Sqlite3Connection

# create or open a sqlite database
conn = Sqlite3Connection('my_database.db')

with conn.cursor() as c:
    # do stuff
    pass
```

## Using a profiler

RickDb provides a simple profiler interface that allows logging of queries, parameters and execution times, as well
as a simple in-memory profiler implementation, [DefaultProfiler](classes/profiler.md#class-rick_dbprofilerdefaultprofiler).

To use a [DefaultProfiler](classes/profiler.md#class-rick_dbprofilerdefaultprofiler) instance on a connection,
just assign the desired instance to the **profiler** property:

```python
from rick_db.backend.pg import PgConnection
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

Example using PgConnectionPool:
```python
from rick_db.backend.pg import PgConnectionPool
from rick_db.profiler import DefaultProfiler

db_cfg = {
    'dbname': "rick_test",
    'user': "rickdb_user",
    'password': "rickdb_password",
    'sslmode': 'require'
}

pool = PgConnectionPool(**db_cfg)
# instantiate profiler, and use it on conn object
pool.profiler = DefaultProfiler()

# perform some queries we can profile
with pool.connection() as conn:
    with conn.cursor() as c:
        c.exec("SELECT 1")

# output: SELECT 1 0.00012579001486301422
for evt in conn.profiler.get_events():
    print(evt.query, evt.elapsed)
```
