import inspect

from rick_db.conn import Connection
from rick_db.mapper import ATTR_RECORD_MAGIC, ATTR_TABLE, ATTR_SCHEMA, ATTR_PRIMARY_KEY


class RepositoryError(Exception):
    pass


class SimpleRepository:

    def __init__(self, db: Connection, tablename: str, schema=None, pk=None):
        self._db = db
        self._tablename = tablename
        self._schema = schema
        self._pk = pk

    def backend(self) -> Connection:
        return self._db

class Repository(SimpleRepository):

    def __init__(self, db, record_type):
        if not inspect.isclass(record_type) or getattr(record_type, ATTR_RECORD_MAGIC, None) is not True:
            raise RepositoryError("__init__(): record_type must be a valid Record class")
        self._record_type = record_type

        super().__init__(db,
                         getattr(record_type, ATTR_TABLE),
                         getattr(record_type, ATTR_SCHEMA),
                         getattr(record_type, ATTR_PRIMARY_KEY)
                         )
