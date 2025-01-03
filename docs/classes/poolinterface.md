# Class rick_db.**PoolInterface**

Thread-safe pool interface, implemented by connection pool objects.

### PoolInterface.**getconn()**

Returns a [Connection](connection.md) object from the pool; the object needs to be disposed via *PoolInterface.putconn()*.

### PoolInterface.**putconn()**

Returns a [Connection](connection.md) object to the pool.

### PoolInterface.**connection()**

Returns a [Connection](connection.md) using a context manager; the connection is automatically returned
to the pool when the context exits.
