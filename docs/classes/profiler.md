# rick_db.profiler

Classes related to the SQL Profiler implementation.

## Class rick_db.profiler.**Event**

Dataclass for a single event entry. Available properties:

```python
@dataclass
class Event:
    timestamp: float
    query: str
    parameters: dict
    elapsed: float
```

## Class rick_db.profiler.**EventCollection**

A list-based class to hold a collection of [Event](#class-rick_dbprofilerevent) objects.

### EventCollection.**filter_duration(duration: float)**

Retrieve a list of [Event](#class-rick_dbprofilerevent) objects whose duration is bigger than or equal to *duration*.

## Class rick_db.profiler.**Profiler**

Base profiler class. Implements an interface for the Profiler classes.

### Profiler.**add_event(query: str, parameters: dict, duration: float)**

Create a new profiling event based on the passed *query*, *parameters* and *duration*, and add it to the internal
event collection.

### Profiler.**clear()**

Purge (clear) all stored events.

### Profiler.**get_events()**

Return internal profiling event collection.


## Class rick_db.profiler.**NullProfiler**

A [Profiler](#rick_dbprofiler)-based class with dummy behaviour, to be used when no profiler is desired.


## Class rick_db.profiler.**DefaultProfiler**

A [Profiler](#rick_dbprofiler)-based class. Events are kept in-memory.
