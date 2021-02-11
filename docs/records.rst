.. _records:

How it works
============

Records
-------

**TL; DR;** A Record is a decorated class that provides the following functionality:

- attribute-based access to row data;
- mapping between internal database field names and attribute names;
- DAOs that are independent from the specific database implementation;
- Fast data import by using referencing for internal dict;


A **Record** is a class that encapsulates a row dict, usually read from the database, and exposes its usage via attributes,
for clean OO usage and facilitating code completion. By leveraging different class and instance scopes, it is possible
to use the defined attributes as the field name for database operation and as the actual value accessor when reading or
writing values.

To achieve this behaviour, a class must be decorated with :function:`fieldmapper<rick_db.record.fieldmapper>`.
The decorator will parse the class definition and build the appropriate internal field mapping, wire the required internal
methods (as well as the initializer, __init__) and set some additional optional parameters, such as tablename, schema and
primary key definition.

Additionally, the class can extend from Record, to provide code completion hints for the Record-related functions.
Regardless if extends or not, :function:`fieldmapper<rick_db.record.fieldmapper>` will patch the appropriate methods.

Example:

.. code-block:: python

    @fieldmapper(pk='id_user')
    class User:
      id = 'id_user'
      name = 'name'
      surname = 'surname'

    print(User.id)      # class scope: outputs 'id_user', the actual internal field name

    user = User(id=9,name="john", surname="connor")

    print(user.id)      # instance scope: outputs 9, the actual stored value


