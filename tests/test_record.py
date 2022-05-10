import pytest

from rick_db.mapper import Record, fieldmapper, ATTR_FIELDS, ATTR_TABLE, ATTR_SCHEMA, ATTR_PRIMARY_KEY, \
    ATTR_RECORD_MAGIC, ATTR_ROW

FIELD_USER_ID = 'id_user'
FIELD_USER_NAME = 'username'

FIELD_ADDRESS_ID = 'id_address'
FIELD_ADDRESS_USER_ID = 'fk_user'
FIELD_ADDRESS_STREET = 'street'
FIELD_ADDRESS_CITY = 'city'


@fieldmapper(pk='id_user')
class User(Record):
    id = FIELD_USER_ID
    name = FIELD_USER_NAME


@fieldmapper(tablename='addresses')
class Address(Record):
    id = FIELD_ADDRESS_ID
    user = FIELD_ADDRESS_USER_ID
    street = FIELD_ADDRESS_STREET
    city = FIELD_ADDRESS_CITY


@fieldmapper(tablename="view_user")
class UserAddress(User, Address):
    pass


def test_fieldmapper_user():
    # check user class
    assert getattr(User, ATTR_RECORD_MAGIC, None) is True
    for attr in [ATTR_TABLE, ATTR_SCHEMA]:
        assert getattr(User, attr, True) is None
    assert getattr(User, ATTR_PRIMARY_KEY, None) == FIELD_USER_ID
    row = getattr(User, ATTR_ROW, None)
    assert type(row) is dict
    assert len(row) == 0
    fm = getattr(User, ATTR_FIELDS, None)
    assert type(fm) is dict
    assert len(fm) == 2
    for k in fm.keys():
        assert k in ['id', 'name']
    for v in fm.values():
        assert v in [FIELD_USER_ID, FIELD_USER_NAME]
    assert User.id == FIELD_USER_ID
    assert User.name == FIELD_USER_NAME


def test_fieldmapper_address():
    # check address class
    assert getattr(Address, ATTR_RECORD_MAGIC, None) is True
    for attr in [ATTR_SCHEMA, ATTR_PRIMARY_KEY]:
        assert getattr(Address, attr, True) is None
    assert getattr(Address, ATTR_TABLE, None) == 'addresses'
    row = getattr(Address, ATTR_ROW, None)
    assert type(row) is dict
    assert len(row) == 0
    fm = getattr(Address, ATTR_FIELDS, None)
    assert type(fm) is dict
    assert len(fm) == 4
    for k in fm.keys():
        assert k in ['id', 'user', 'street', 'city']
    for v in fm.values():
        assert v in [FIELD_ADDRESS_ID, FIELD_ADDRESS_USER_ID, FIELD_ADDRESS_STREET, FIELD_ADDRESS_CITY]
    assert Address.id == FIELD_ADDRESS_ID
    assert Address.user == FIELD_ADDRESS_USER_ID
    assert Address.street == FIELD_ADDRESS_STREET
    assert Address.city == FIELD_ADDRESS_CITY


def check_user(u: User, id, name):
    # pk
    assert u.has_pk() is True
    # read attributes
    if id is None:
        assert u.id is None
        d = {
            'name': name,
        }
        r = {
            'username': name,
        }
    else:
        assert u.id == id
        assert u.pk() == id
        d = {
            'id': id,
            'name': name,
        }
        r = {
            'id_user': id,
            'username': name,
        }
    assert u.name == name

    assert u.fields() == list(d.keys())
    assert u.values() == list(d.values())
    for field, value in u.items():
        assert field in d.keys()
        assert value in d.values()

    u_dict = u.asdict()
    assert u_dict == d
    u_record = u.asrecord()
    assert u_record == r


def test_record_simple():
    # simple/incomplete record creation
    user = User(name="john doe")
    check_user(user, None, "john doe")

    # complete record creation
    user = User(id=3, name="john doe")
    check_user(user, 3, "john doe")
    user.name = "uncle bob"
    check_user(user, 3, "uncle bob")

    # programmatic record
    user = User()
    user.id = "abc"
    user.name = "def"
    check_user(user, "abc", "def")

    # record manipulation
    user = User(id=9, name="john doe")
    new_user = User().load(**user.asdict())
    check_user(new_user, 9, "john doe")

    record = user.asrecord()
    new_user = User().fromrecord(record)
    check_user(new_user, 9, "john doe")

    record = record.copy()  # duplicate record, because fromrecord() uses referencing, not a separate copy
    record["unmapped_field"] = "something"
    new_user = User().fromrecord(record)
    check_user(new_user, 9, "john doe")

    # ensure dicts are not shared
    user = User().load(name="john connor")
    user2 = User()
    assert user2.name != user.name
    assert user2.name is None
    assert user2.id is None


def test_record_multi():
    ua = UserAddress(name="john connor", city="california")
    assert ua._tablename == "view_user"
    assert ua._pk is None
    assert ua.name == "john connor"
    assert ua.street is None
    assert ua.city == "california"
    for field in ua.fields():
        assert field in ['id', 'name', 'user', 'street', 'city']
    assert len(ua.asdict()) == 2
