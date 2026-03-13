from typing import Optional

from rick_db.mapper import (
    Record,
    fieldmapper,
    ATTR_FIELDS,
    ATTR_TABLE,
    ATTR_SCHEMA,
    ATTR_PRIMARY_KEY,
    ATTR_JSON_EXCLUDE,
    ATTR_RECORD_MAGIC,
    ATTR_ROW,
)

# field names - User
FIELD_USER_ID = "id_user"
FIELD_USER_NAME = "username"

# field names - Address
FIELD_ADDRESS_ID = "id_address"
FIELD_ADDRESS_USER_ID = "fk_user"
FIELD_ADDRESS_STREET = "street"
FIELD_ADDRESS_CITY = "city"


@fieldmapper(pk="id_user")
class User(Record):
    id = FIELD_USER_ID
    name = FIELD_USER_NAME


@fieldmapper(tablename="address")
class Address(Record):
    id = FIELD_ADDRESS_ID
    user = FIELD_ADDRESS_USER_ID
    street = FIELD_ADDRESS_STREET
    city = FIELD_ADDRESS_CITY


@fieldmapper(tablename="view_user")
class UserAddress(User, Address):
    pass


class TestMapper:

    def test_user_class(self):
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
            assert k in ["id", "name"]
        for v in fm.values():
            assert v in [FIELD_USER_ID, FIELD_USER_NAME]
        assert User.id == FIELD_USER_ID
        assert User.name == FIELD_USER_NAME

    def test_address_class(self):
        # check address class
        assert getattr(Address, ATTR_RECORD_MAGIC, None) is True
        for attr in [ATTR_SCHEMA, ATTR_PRIMARY_KEY]:
            assert getattr(Address, attr, True) is None
        assert getattr(Address, ATTR_TABLE, None) == "address"
        row = getattr(Address, ATTR_ROW, None)
        assert type(row) is dict
        assert len(row) == 0
        fm = getattr(Address, ATTR_FIELDS, None)
        assert type(fm) is dict
        assert len(fm) == 4
        for k in fm.keys():
            assert k in ["id", "user", "street", "city"]
        for v in fm.values():
            assert v in [
                FIELD_ADDRESS_ID,
                FIELD_ADDRESS_USER_ID,
                FIELD_ADDRESS_STREET,
                FIELD_ADDRESS_CITY,
            ]
        assert Address.id == FIELD_ADDRESS_ID
        assert Address.user == FIELD_ADDRESS_USER_ID
        assert Address.street == FIELD_ADDRESS_STREET
        assert Address.city == FIELD_ADDRESS_CITY

    def validate_user(self, u: User, id: Optional[int], name: str):
        # check pk
        assert u.has_pk() is True

        # read attributes
        if id is None:
            assert u.id is None
            d = {
                "name": name,
            }
            r = {
                "username": name,
            }
        else:
            assert u.id == id
            assert u.pk() == id
            d = {
                "id": id,
                "name": name,
            }
            r = {
                "id_user": id,
                "username": name,
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

    def test_record_user(self):
        # simple/incomplete record creation
        user = User(name="john doe")
        self.validate_user(user, None, "john doe")

        # complete record creation
        user = User(id=3, name="john doe")
        self.validate_user(user, 3, "john doe")
        user.name = "uncle bob"
        self.validate_user(user, 3, "uncle bob")

        # programmatic record
        user = User()
        user.id = "abc"
        user.name = "def"
        self.validate_user(user, "abc", "def")

        # record manipulation
        user = User(id=9, name="john doe")
        new_user = User().load(**user.asdict())
        self.validate_user(new_user, 9, "john doe")

        record = user.asrecord()
        new_user = User().fromrecord(record)
        self.validate_user(new_user, 9, "john doe")

        record = (
            record.copy()
        )  # duplicate record, because fromrecord() uses referencing, not a separate copy

        record["unmapped_field"] = "something"
        new_user = User().fromrecord(record)
        self.validate_user(new_user, 9, "john doe")

        # ensure dicts are not shared
        user = User().load(name="john connor")
        user2 = User()
        assert user2.name != user.name
        assert user2.name is None
        assert user2.id is None

    def test_record_view(self):
        ua = UserAddress(name="john connor", city="california")
        assert ua._tablename == "view_user"
        assert ua._pk is None
        assert ua.name == "john connor"
        assert ua.street is None
        assert ua.city == "california"
        for field in ua.fields():
            assert field in ["id", "name", "user", "street", "city"]
        assert len(ua.asdict()) == 2


# field names - SecureUser
FIELD_SECURE_USER_ID = "id_user"
FIELD_SECURE_USER_NAME = "username"
FIELD_SECURE_USER_PASSWORD = "password_hash"
FIELD_SECURE_USER_SECRET = "secret_key"


@fieldmapper(pk="id_user", tablename="users", json_exclude={"password", "secret"})
class SecureUser(Record):
    id = FIELD_SECURE_USER_ID
    name = FIELD_SECURE_USER_NAME
    password = FIELD_SECURE_USER_PASSWORD
    secret = FIELD_SECURE_USER_SECRET


class TestJsonExclude:

    def test_class_level_exclusion(self):
        """Fields listed in json_exclude are omitted from asdict()"""
        user = SecureUser(id=1, name="alice", password="hashed", secret="s3cret")
        result = user.asdict()
        assert result == {"id": 1, "name": "alice"}
        assert "password" not in result
        assert "secret" not in result

    def test_per_call_exclusion(self):
        """asdict(exclude=...) omits additional fields per call"""
        user = User(id=1, name="john")
        result = user.asdict(exclude=["name"])
        assert result == {"id": 1}
        assert "name" not in result

    def test_combined_exclusion(self):
        """Per-call exclude merges with class-level json_exclude"""
        user = SecureUser(id=1, name="alice", password="hashed", secret="s3cret")
        result = user.asdict(exclude=["name"])
        assert result == {"id": 1}
        assert "name" not in result
        assert "password" not in result
        assert "secret" not in result

    def test_backward_compat_no_exclusion(self):
        """Existing asdict() without arguments still works identically"""
        user = User(id=3, name="john doe")
        result = user.asdict()
        assert result == {"id": 3, "name": "john doe"}

    def test_excluded_fields_still_accessible(self):
        """Excluded fields are still accessible as attributes and via other methods"""
        user = SecureUser(id=1, name="alice", password="hashed", secret="s3cret")

        # attribute access still works
        assert user.password == "hashed"
        assert user.secret == "s3cret"

        # asrecord() still includes excluded fields
        record = user.asrecord()
        assert record == {
            "id_user": 1,
            "username": "alice",
            "password_hash": "hashed",
            "secret_key": "s3cret",
        }

        # fields() still includes excluded fields
        assert "password" in user.fields()
        assert "secret" in user.fields()

        # values() still includes excluded fields
        assert "hashed" in user.values()
        assert "s3cret" in user.values()

    def test_json_exclude_attribute_set_on_class(self):
        """The _json_exclude attribute is properly set on decorated classes"""
        assert getattr(SecureUser, ATTR_JSON_EXCLUDE) == {"password", "secret"}
        assert getattr(User, ATTR_JSON_EXCLUDE) == set()

    def test_empty_exclude_returns_all(self):
        """Passing an empty list to exclude returns all fields (no class-level exclude)"""
        user = User(id=1, name="john")
        result = user.asdict(exclude=[])
        assert result == {"id": 1, "name": "john"}
