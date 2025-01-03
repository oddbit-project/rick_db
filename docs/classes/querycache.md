# Class rick_db.**QueryCache**

Internal thread-safe query cache object

### QueryCache.**get(key:str, default=None)**

Attempts to fetch a stored value by key, and if it does not exist, returns *default* value.

### QueryCache.**set(key:str, value:str)**

Stores a value associated with the specified *key*. If *key* already exists, its contents are replaced.

### QueryCache.**has(key:str)**

Returns *True* if the specified key exists.

### QueryCache.**remove(key:str)**

Attempts to remove the entry identified by *key*. Non-existing keys are ignored.

### QueryCache.**purge()**

Removes all stored data.

### QueryCache.**copy()**

Returns a new *QueryCache* object with a copy of the stored data, and a new *threading.Lock()* instance.
