import collections
import inspect
from typing import Union, Any

from rick_db import Record
from rick_db.cache import StrCache
from rick_db.conn import Connection
from rick_db.mapper import ATTR_RECORD_MAGIC, ATTR_TABLE, ATTR_SCHEMA, ATTR_PRIMARY_KEY
from rick_db.sql import SqlDialect, Select, Insert


class RepositoryError(Exception):
    pass


class BaseRepository:

    def __init__(self, db: Connection, tablename: str, schema=None, pk=None):
        self._db = db
        self._tablename = tablename
        self._schema = schema
        self._pk = pk
        self._dialect = db.dialect()

    def backend(self) -> Connection:
        return self._db

    def dialect(self) -> SqlDialect:
        return self._dialect


class Repository(BaseRepository):

    def __init__(self, db, record_type):
        if not inspect.isclass(record_type) or getattr(record_type, ATTR_RECORD_MAGIC, None) is not True:
            raise RepositoryError("__init__(): record_type must be a valid Record class")
        self._record = record_type  # type: Record
        self._query_cache = query_cache  # use global query cache
        self._key_prefix = "{0}.{1}:".format(self.__class__.__module__, self.__class__.__name__)

        super().__init__(db,
                         getattr(record_type, ATTR_TABLE),
                         getattr(record_type, ATTR_SCHEMA),
                         getattr(record_type, ATTR_PRIMARY_KEY)
                         )

    def select(self, cols=None) -> Select:
        """
        Return a Select() builder instance for the current table
        :param cols: optional columns
        :return: Select
        """
        return Select(self._dialect).from_(self._tablename, cols=cols, schema=self._schema)

    def find_pk(self, pk_value) -> Union[object, None]:
        """
        Retrieve a single row by primary key
        :param pk_value: primary key value
        :return: record object of self._record type or None
        """
        if self._pk is None:
            raise RepositoryError("find_pk(): missing primary key in Record %s" % str(type(self._record)))
        qry = self._cache_get('find_pk')
        if qry is None:
            qry, values = self.select().where(self._pk, '=', pk_value).limit(1).assemble()
            self._cache_set('find_pk', qry)
        else:
            values = [pk_value]
        with self._db.cursor() as c:
            return c.fetchone(qry, values, self._record)

    def fetch_one(self, qry: Select) -> Union[object, None]:
        """
        Retrieve a single row
        :param qry: query to execute
        :return: record object of self._record or None
        """
        with self._db.cursor() as c:
            return c.fetchone(qry.limit(1).assemble(), self._record)

    def fetch(self, qry: Select) -> Union[list, None]:
        """
        Fetch a list of rows
        :param qry: query to execute
        :return: list of record object or empty list
        """
        with self._db.cursor() as c:
            qry, values = qry.assemble()
            return c.fetchall(qry, values, self._record)

    def fetch_by_field(self, field, value, cols=None):
        """
        Fetch a list of rows where field=value
        :param field: field name
        :param value: value to match
        :param cols: optional columns to return
        :return: list of record object or empty list
        """
        qry, values = self.select(cols=cols).where(field, '=', value).assemble()
        with self._db.cursor() as c:
            return c.fetchall(qry, values, self._record)

    def fetch_where(self, where_clauses: list, cols=None) -> list:
        """
        Fetch a list of rows that match a list of AND'ed WHERE clauses
        where_clauses = (field, operator, value)
        """
        qry = self.select(cols=cols)
        for clause in where_clauses:
            clen = len(clause)
            if clen == 2:
                qry.where(clause[0], '=', clause[1])
            elif clen == 3:
                qry.where(clause[0], clause[1], clause[2])
            else:
                raise RepositoryError("fetch_where(): invalid length for where clause")

        qry, values = qry.assemble()
        with self._db.cursor() as c:
            return c.fetchall(qry, values, self._record)

    def fetch_all(self):
        """
        Fetch all rows
        :return: list of record object
        """
        qry = self._cache_get('fetch_all')
        if qry is None:
            qry = self.select()
            self._cache_set('fetch_all', qry)

        qry, values = qry.assemble()
        with self._db.cursor() as c:
            return c.fetchall(qry, values, self._record)

    def insert(self, record, cols=None) -> Union[object, None]:
        """
        Insert a record, optionally returning values
        :param record: record object
        :param cols: optional return columns
        :return: if cols != None, record with specified columns
        """
        qry = Insert(self._dialect).into(record)
        if cols is not None:
            qry.returning(cols)
        sql, values = qry.assemble()
        with self._db.cursor() as c:
            result = c.exec(sql, values, self._record)
            if len(result) > 0:
                return result.pop(0)
            return None

    def insert_pk(self, record) -> Any:
        sql, values = Insert(self._dialect).into(record).returning(self._pk).assemble()
        with self._db.cursor() as c:
            result = c.exec(sql, values, self._record)
            if len(result) > 0:
                return result.pop(0).pk()
            return None

    def delete_pk(self, pk_value):
        pass

    def delete_where(self, where_clauses: list):
        pass

    def map_result_id(self, result: list) -> dict:
        pass

    def valid_pk(self, pk_value) -> bool:
        pass

    def exec(self, sql, values):
        pass

    def exists(self, where, pk_to_skip) -> bool:
        pass

    def _cache_get(self, key) -> Union[str, None]:
        return self._query_cache.get(self._key_prefix + key)

    def _cache_set(self, key, value):
        return self._query_cache.set(self._key_prefix + key, value)


# global query cache for all repositories
query_cache = StrCache()
