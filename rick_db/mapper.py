from functools import lru_cache
import inspect

# Record class attribute names
ATTR_RECORD_MAGIC = "__PatchedRecordClass__"
ATTR_FIELDS = "_fieldmap"
ATTR_TABLE = "_tablename"
ATTR_SCHEMA = "_schema"
ATTR_PRIMARY_KEY = "_pk"
ATTR_JSON_EXCLUDE = "_json_exclude"
ATTR_ROW = "_row"


class RecordError(Exception):
    pass


class Record:
    def load(self, **kwargs):
        pass

    def fromrecord(self, record):
        pass

    def has_pk(self):
        pass

    def pk(self):
        pass

    def asdict(self, exclude=None):
        pass

    def asrecord(self):
        pass

    def fields(self):
        pass

    def items(self):
        pass

    def values(self):
        pass

    def fieldmap(self):
        pass


class BaseRecord(Record):
    _fieldmap = {}
    _tablename = None
    _schema = None
    _pk = None
    _json_exclude = set()

    def __init__(self, **kwargs):
        self._row = {}  # row must be a local scoped var
        if len(kwargs) > 0:
            self.load(**kwargs)

    def load(self, **kwargs):
        """
        Load record data from named parameter
        Names are field values, ex:
            user.load(name="john connor", age=11)
        :param kwargs:
        :return: self
        """
        fm = object.__getattribute__(self, ATTR_FIELDS)
        row = object.__getattribute__(self, ATTR_ROW)
        for field, value in kwargs.items():
            if field in fm:
                row[fm[field]] = value
            else:
                raise RecordError(f"unknown attribute {field}")
        return self

    def fromrecord(self, record: dict):
        """
        Loads a record from a db result record

        Field names are not checked. This allows for fast loading of data for read operations
        record parameter is not copied, but instead referenced; ensure there are no operations that may alter record
        structure outside the scope of the Record class
        :param record:
        :return: Record
        """
        object.__setattr__(self, ATTR_ROW, record)
        return self

    def has_pk(self):
        """
        Returns true if a pk is defined
        :return:
        """
        return self._pk is not None

    def dbfields(self):
        """
        Return the db field list from the fieldmap
        :return: list
        """
        return list(self._fieldmap.values())

    def pk(self):
        """
        Return the current pk value, if defined
        If not defined, RecordError is raised
        If defined but value is not set, raises AttributeError
        :return:
        """
        pk = self._pk
        if pk is None:
            raise RecordError("primary key is not defined")
        row = self._row
        if pk in row:
            return row[pk]
        raise AttributeError("primary key value is not set")

    def asdict(self, exclude=None):
        if exclude is None:
            skip = self._json_exclude
        else:
            skip = set(exclude) | self._json_exclude
        result = {}
        data = self._row
        for key, dbfield in self._fieldmap.items():
            if key not in skip and dbfield in data:
                result[key] = data[dbfield]
        return result

    def asrecord(self):
        fieldmap = object.__getattribute__(self, ATTR_FIELDS)
        data = object.__getattribute__(self, ATTR_ROW)
        dbfieldnames = fieldmap.values()
        return {key: val for key, val in data.items() if key in dbfieldnames}

    def fields(self):
        result = []
        data = self._row
        for key, dbfield in self._fieldmap.items():
            if dbfield in data:
                result.append(key)
        return result

    def items(self):
        return self.asdict().items()

    def values(self):
        result = []
        data = self._row
        for key, dbfield in self._fieldmap.items():
            if dbfield in data:
                result.append(data[dbfield])
        return result

    def fieldmap(self):
        """
        Return the field mapping dict {attribute_name: db_column_name}
        :return: dict
        """
        return self._fieldmap

    def add(self, name, value, field_name: str = None):
        # copy-on-write: avoid mutating the class-level _fieldmap
        if self._fieldmap is self.__class__._fieldmap:
            object.__setattr__(self, ATTR_FIELDS, dict(self._fieldmap))
        fm = object.__getattribute__(self, ATTR_FIELDS)
        if not field_name:
            fm[name] = name
            field_name = name
        else:
            fm[name] = field_name
        self.__setattr__(name, value)

    def __getattribute__(self, attr):
        fieldmap = object.__getattribute__(self, ATTR_FIELDS)
        if attr in fieldmap:
            field = fieldmap[attr]
            data = object.__getattribute__(self, ATTR_ROW)
            return data.get(field)

        return object.__getattribute__(self, attr)

    def __setattr__(self, key, value):
        fm = object.__getattribute__(self, ATTR_FIELDS)
        if key in fm:
            data = object.__getattribute__(self, ATTR_ROW)
            if not isinstance(data, dict):
                # unwrap dict from dict-like record objects, such as psycopg2 results
                # this is only necessary when setting values, as original object is often read-only
                data = dict(data)
                object.__setattr__(self, ATTR_ROW, data)
            field = fm[key]
            data[field] = value
        else:
            self.__dict__[key] = value


@lru_cache(maxsize=None)
def _base_record_method_map() -> dict:
    methods = {}
    for item in dir(BaseRecord):
        attr = getattr(BaseRecord, item)
        if inspect.isfunction(attr):
            methods[item] = attr
    return methods


def fieldmapper(
    cls=None, pk=None, tablename=None, schema=None, clsonly=False, json_exclude=None
):
    def wrap(cls):
        fieldmap = {}
        if clsonly:
            # build fieldmap for current class attributes only
            fieldmap = dict(
                (field, value)
                for field, value in cls.__dict__.items()
                if field[0] != "_" and not callable(value)
            )
        else:
            # build fieldmap for all available class attributes
            for item in dir(cls):
                if item[0] != "_":
                    value = getattr(cls, item)
                    if not callable(value):
                        fieldmap[item] = value

        # replace class variables
        setattr(cls, ATTR_RECORD_MAGIC, True)
        setattr(cls, ATTR_FIELDS, fieldmap)
        setattr(cls, ATTR_TABLE, tablename)
        setattr(cls, ATTR_SCHEMA, schema)
        setattr(cls, ATTR_PRIMARY_KEY, pk)
        setattr(cls, ATTR_JSON_EXCLUDE, set(json_exclude) if json_exclude else set())
        # row attr is set, but will be shadowed by internal attribute on __init__
        setattr(cls, ATTR_ROW, {})

        # patch methods
        for name, method in _base_record_method_map().items():
            setattr(cls, name, method)
        return cls

    if cls is None:
        return wrap
    return wrap(cls)


def patch_record(obj=None, tablename=None, pk=None, schema=None):
    """
    Set/update internal attributes for Record obj
    :param obj: Record object to update
    :param tablename: table name
    :param pk: primary key name
    :param schema: schema name
    :return:
    """
    setattr(obj, ATTR_TABLE, tablename)
    setattr(obj, ATTR_PRIMARY_KEY, pk)
    setattr(obj, ATTR_SCHEMA, schema)
