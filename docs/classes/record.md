# Class rick_db.**Record**

The base Record class definition for all Object Mapper classes. Instead of inheritance, the Record class method attributes
are copied to the final class, via attribute patching performed by the **@fieldmapper** decorator.

Classes patched from Record inherit several useful methods, not only in the Object Mapper context, but also for general
usage such as serialization/deserialization or type conversion.

### Record.**load(\*\*kwargs)**

Loads attribute values from the provided named parameters. 
Note: loading can also be done via constructor

Example:
```python
from rick_db import fieldmapper

@fieldmapper
class MyRecord:
    id = 'id_record'
    name = 'name'

# load values via constructor
r1 = MyRecord(id=1, name='Sarah Connor')

# load values via load()
r2 = MyRecord().load(id=2, name='John Connor')
```

### Record.**fromrecord(record: dict)**

Load attribute values from a source dict. This method is used to load database row results into Record objects, and it
is performance-sensitive - the attribute names aren't checked, and the values aren't actually copied, but referenced 
instead. Don't use this with mutable sources, as it will also change the Record object values.

### Record.**has_pk()**

Returns True if a primary key definition (*pk* field in the decorator) exists. 

### Record.**pk()**

Return the primary key value, if primary key is defined and a value is set. If a primary key is defined, but no value
is present, raises **AttributeError** instead.

### Record.**dbfields()**

Returns a list of the database field names, defined in the class declaration.

Example:
```python
from rick_db import fieldmapper

@fieldmapper
class MyRecord:
    id = 'id_record'
    name = 'name'

r1 = MyRecord(id=1, name='Sarah Connor')

# output: ['id_record', 'name']
print(r1.dbfields())
```

### Record.**asdict()**

Converts the Record object to a dictionary and returns it. Attribute names are used as keys for existing values.

Example:
```python
from rick_db import fieldmapper

@fieldmapper
class MyRecord:
    id = 'id_record'
    name = 'name'

r1 = MyRecord(id=1, name='Sarah Connor')

# output: {'id': 1, 'name': 'Sarah Connor'}
print(r1.asdict())
```

### Record.**asrecord()**

Converts the Record object to a database-compatible dictionary and returns it. Field names are used as keys for
existing values.

Example:
```python
from rick_db import fieldmapper

@fieldmapper
class MyRecord:
    id = 'id_record'
    name = 'name'

r1 = MyRecord(id=1, name='Sarah Connor')

# output: {'id_record': 1, 'name': 'Sarah Connor'}
print(r1.asrecord())
```

### Record.**fields()**

Alias function to Record.asdict().items()

Example:
```python
from rick_db import fieldmapper

@fieldmapper
class MyRecord:
    id = 'id_record'
    name = 'name'

r1 = MyRecord(id=1, name='Sarah Connor')

# output: ['id', 'name']
print(r1.fields())
```

### Record.**values()**

Returns a list with stored values.

Example:
```python
from rick_db import fieldmapper

@fieldmapper
class MyRecord:
    id = 'id_record'
    name = 'name'

r1 = MyRecord(id=1, name='Sarah Connor')

# output: [1, 'Sarah Connor']
print(r1.values())
```
