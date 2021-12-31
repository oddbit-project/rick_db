# Object Mapper

## DTO Records

The RickDb object mapper allows the declaration of DTO (data transfer objects) classes, generically known as Records. A
record contains a set of attributes and their corresponding field names in the database scope, and some optional additional
details such as table name, schema and primary key information. The object mapper purpose is to manage the translation 
of database fields to object attributes, and vice-versa.

RickDb Records are pure data objects, as they don't depend or reference any database-specific resource; they only hold
attributes and values representing a result row from a given database operation. Attribute names are also independent from
their database representation - the mapping between an attribute and the underlying field name is explicit, and performed
in the declaration of the class.

It is possible to declare Record objects that map only a subset of fields from a given query result; the additional fields
will be ignored.

These properties make Records a suitable format to carry data between architectural boundaries, not only due to their 
decoupling from the underlying table structure, but also because they can be easily serialized and deserialized.

To achieve better performance, the internal mapping of attributes to database field names is performed at load time within
the class declaration context; a decorator patches the class definition with the required internal structures when the
file is loaded, instead of handling it in runtime. 

## Declaring Records

Record classes are declared using the **@fieldmapper** decorator:

```python
from rick_db import fieldmapper

@fieldmapper
class Customer:
    id = 'id_customer'  # attribute 'id' maps to field 'id_customer'
    name = 'name'       # attribute 'name' maps to field 'name'
    address = 'address' # attribute 'address' maps to field 'address'
    city = 'city'       # attribute 'city' maps to field 'city'
    id_country = 'fk_country' # attribute 'id_country' maps to field 'fk_country'

# access class-level attributes
print(Customer.name) # outputs  'name'

# access object-level attributes
# customer data is loaded via __init__; The key names must match the defined attributes
customer = Customer(id=3, name="John Doe", address="Obere Str.", city="Berlin")

# output: John Doe
print(customer.name)  

# output: 'None'
print(customer.id_country)  

# output: {'address': 'Obere Str.', 'city': 'Berlin', 'id': 3, 'name': 'John Doe'}
print(customer.asdict())

# output: {'id_customer': 3, 'name': 'John Doe', 'address': 'Obere Str.', 'city': 'Berlin'}
print(customer.asrecord())
```

As mentioned previously, it is possible to also provide optional details, such as table or view name, schema and primary
key name; these details are quite useful when using RickDb's [Repository](repository.md) or [Query Builder](sql/index.md) to
provide context for operations. This is probably the most common usage scenario, when designing a multi-tier application:

```python
from rick_db import fieldmapper

@fieldmapper(tablename='customers', pk='id_customer', schema='public')
class Customer:
    id = 'id_customer'  # attribute 'id' maps to field 'id_customer'
    name = 'name'       # attribute 'name' maps to field 'name'
    address = 'address' # attribute 'address' maps to field 'address'
    city = 'city'       # attribute 'city' maps to field 'city'
    id_country = 'fk_country' # attribute 'id_country' maps to field 'fk_country'

# access class-level attributes
print(Customer.name) # outputs  'name'

# access object-level attributes
# customer data is loaded via __init__; The key names must match the defined attributes
customer = Customer(id=3, name="John Doe", address="Obere Str.", city="Berlin")

# output: John Doe
print(customer.name)  

# output: 'None'
print(customer.id_country)  

# output: {'address': 'Obere Str.', 'city': 'Berlin', 'id': 3, 'name': 'John Doe'}
print(customer.asdict())

# output: {'id_customer': 3, 'name': 'John Doe', 'address': 'Obere Str.', 'city': 'Berlin'}
print(customer.asrecord())
```

## Available methods

The patching process performed by **@fieldmapper** copies all the available methods in the base [Record](classes/record.md)
class to the defined class. As a result, all [Record](classes/record.md) methods can be used on a **@fieldmapper** patched 
class.






