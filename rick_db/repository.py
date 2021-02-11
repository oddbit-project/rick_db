import inspect

from rick_db.record import ATTR_RECORD_MAGIC, ATTR_TABLE, ATTR_SCHEMA, ATTR_PRIMARY_KEY


class RepositoryError(Exception):
    pass


class Repository:

    def __init__(self, db, record_type):
        if not inspect.isclass(record_type) or getattr(record_type, ATTR_RECORD_MAGIC, None) is not True:
            raise RepositoryError("__init__(): record_type must be a valid Record class")

        self._db = db
        self._record_type = record_type
        self._tablename = getattr(record_type, ATTR_TABLE)
        self._schema = getattr(record_type, ATTR_SCHEMA)
        self._pk = getattr(record_type, ATTR_PRIMARY_KEY)

