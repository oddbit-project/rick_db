import copy
import inspect
from typing import Union, Any, Optional

from rick_db import Record
from rick_db.cache import StrCache
from rick_db.conn import Connection
from rick_db.mapper import ATTR_RECORD_MAGIC, ATTR_TABLE, ATTR_SCHEMA, ATTR_PRIMARY_KEY
from rick_db.sql import SqlDialect, Select, Insert, Delete, Update, Literal


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
        self._key_prefix = "{0}:{1}.{2}:".format(type(db).__name__, self.__class__.__module__, self.__class__.__name__)

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

    def fetch_pk(self, pk_value) -> Optional[object]:
        """
        Retrieve a single row by primary key
        :param pk_value: primary key value
        :return: record object of self._record type or None

        Example:
            .fetch_pk(32)    # search for record with id 32
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

    def fetch_one(self, qry: Select) -> Optional[object]:
        """
        Retrieve a single row
        :param qry: query to execute
        :return: record object of self._record or None

        Example:
            r.fetch_one(r.select().where('login', '=', 'gandalf@lotr'))     # fetch record if exists, else returns None
        """
        with self._db.cursor() as c:
            sql, values = qry.limit(1).assemble()
            return c.fetchone(sql, values, cls=self._record)

    def fetch(self, qry: Select, cls=None) -> Optional[list]:
        """
        Fetch a list of rows

        :param qry: query to execute
        :param cls: optional record class (useful for joins that may return different record structures)
        :return: list of record object or empty list

        Example:
            r.fetch(r.select().where('name', 'like', 'gandalf%'))     # fetch records that match query
        """
        with self._db.cursor() as c:
            sql, values = qry.assemble()
            if cls is None:
                cls = self._record
            return c.fetchall(sql, values, cls=cls)

    def fetch_raw(self, qry: Select) -> Optional[list]:
        """
        Fetch a list of rows
        Result is not serialized to record, instead it returns a list of dict-like records directly from the DB driver

        :param qry: query to execute
        :return: list of dict-like result

        Example:
            r.fetch_raw(r.select().where('name', 'like', 'gandalf%'))     # fetch records that match query
        """
        with self._db.cursor() as c:
            sql, values = qry.assemble()
            return c.fetchall(sql, values)

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

        :param where_clauses: list of where clauses
        :param cols: list of optional column names

        Example:
            .fetch_where([('name', 'like', 'john %')])               # return records whose name starts with john
            .fetch_where([('name', 'like', 'john %')], cols=['id'])  # return records with only ids whose name starts with john
        """
        if len(where_clauses) == 0:
            raise RepositoryError("fetch_where(): empty where_clauses")

        qry = self.select(cols=cols)

        for clause in where_clauses:
            if len(clause) != 3:
                raise RepositoryError("fetch_where(): invalid length for where clause")
            qry.where(clause[0], clause[1], clause[2])

        qry, values = qry.assemble()
        with self._db.cursor() as c:
            return c.fetchall(qry, values, self._record)

    def fetch_all(self) -> list:
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

    def insert(self, record, cols=None) -> Optional[object]:
        """
        Insert a record, optionally returning values

        Notes:
        If the database does not support INSERT...RETURNING, cols can only have one entry, and the primary key will be returned
        regardless of the actual field name specified in cols
        Alternatively, use insert_pk()

        :param record: record object
        :param cols: optional return columns
        :return: if cols != None, record with specified columns

        Example:
            .insert(MyTable(name="John", surname="connor"))         # insert a new record, returns None
            .insert(MyTable(name="John", surname="connor"), cols=['id'])  # insert a new record, returns a record with id filled
        """
        qry = Insert(self._dialect).into(record)
        if cols is not None:
            if self._dialect.insert_returning:
                if len(cols) > 0:
                    qry.returning(cols)
            else:
                if len(cols) != 1:
                    raise RepositoryError("insert(): database does not support returning multiple columns")

        sql, values = qry.assemble()
        with self._db.cursor() as c:
            result = c.exec(sql, values, self._record)
            if not self._dialect.insert_returning and cols is not None:
                # assemble a record with only primary key
                record = self._record()
                record.fromrecord({self._pk: c.get_cursor().lastrowid})
                return record

            if len(result) > 0:
                return result.pop(0)
            return None

    def insert_pk(self, record) -> Any:
        """
        Insert a record returning the primary key value

        :param record: record object to insert
        :return: record id or None
        """
        pk = self._pk
        if pk is None:
            pk = getattr(record, ATTR_PRIMARY_KEY, None)
        if pk is None:
            raise RepositoryError("insert_pk(): record has no primary key")

        qry = Insert(self._dialect).into(record)
        if self._dialect.insert_returning:
            sql, values = qry.returning(pk).assemble()
        else:
            sql, values = qry.assemble()

        with self._db.cursor() as c:
            result = c.exec(sql, values, cls=self._record)
            if not self._dialect.insert_returning:
                return c.get_cursor().lastrowid

            if len(result) > 0:
                return result.pop(0).pk()
            return None

    def delete_pk(self, pk_value):
        """
        Delete a record by primary key value

        :param pk_value: search value for record to delete
        :return: none
        """
        if self._pk is None:
            raise RepositoryError("delete_pk(): record has no primary key")

        sql = self._cache_get('delete_pk')
        if sql is None:
            sql, values = Delete(self._dialect).from_(self._record).where(self._pk, '=', pk_value).assemble()
            self._cache_set('delete_pk', sql)
        else:
            values = [pk_value]
        with self._db.cursor() as c:
            c.exec(sql, values)

    def delete_where(self, where_clauses: list):
        """
        Delete a set of rows that match a list of AND'ed WHERE clauses

        :param where_clauses: list of where clauses
        where_clauses = (field, operator, value)
        """
        qry = Delete(self._dialect).from_(self._record)

        if len(where_clauses) == 0:
            # avoid catastrophe if an empty list is passed
            raise RepositoryError("delete_where(): where_clauses is empty")

        for clause in where_clauses:
            if len(clause) != 3:
                raise RepositoryError("delete_where(): invalid length for where clause")
            qry.where(clause[0], clause[1], clause[2])

        qry, values = qry.assemble()
        with self._db.cursor() as c:
            c.exec(qry, values)

    def map_result_id(self, result: list) -> dict:
        """
        Transform a list of records into a dict indexed by primary key

        :param result: list to transform
        :return: dict of id:record
        """
        if self._pk is None:
            raise RepositoryError("map_result_id(): missing primary key")
        tmp = {}
        for r in result:
            tmp[r.pk()] = r
        return tmp

    def valid_pk(self, pk_value) -> bool:
        """
        Check if a given id is an existing record

        :param pk_value: primary key value to check
        :return: bool
        """
        if self._pk is None:
            raise RepositoryError("valid_pk(): missing primary key")

        sql = self._cache_get('valid_pk')
        values = [pk_value]
        if sql is None:
            sql, values = self.select(self._pk).where(self._pk, '=', pk_value).limit(1).assemble()
            self._cache_set('valid_pk', sql)

        with self._db.cursor() as c:
            result = c.fetchone(sql, values, cls=self._record)
            return result is not None

    def exec(self, sql, values=None, cls=None, useCls=True):
        """
        Execute a raw SQL query

        :param sql: query to execute
        :param values:values for the query
        :param cls: optional record-type to use for result deserialization
        :param useCls: if false, no record deserialization will be attempted
        :return: list
        """
        with self._db.cursor() as c:
            if cls is None and useCls:
                cls = self._record
            return c.exec(sql, values, cls=cls)

    def exists(self, field, value, pk_to_skip) -> bool:
        """
        Check DB for condition field=value AND pk <> pk_to_skip
        This is useful to check for a unique constraint
        :param field: field to check
        :param value: field value
        :param pk_to_skip: pk value to skip
        :return: bool
        """
        if self._pk is None:
            raise RepositoryError("exists(): missing primary key")

        sql, values = self.select(self._pk).where(self._pk, '<>', pk_to_skip) \
            .where(field, '=', value) \
            .limit(1) \
            .assemble()
        with self._db.cursor() as c:
            result = c.fetchone(sql, values, cls=self._record)
            return result is not None

    def update(self, record, pk_value=None):
        """
        Updates a record on the database by primary key

        The record may or may not contain the primary key value; if exists, pk_value is ignored; if not, pk_value
        is required

        :param record: record object
        :param pk_value: optional primary key value
        :return:
        """
        if self._pk is None:
            raise RepositoryError("update(): missing primary key")
        data = record.asrecord()  # type:dict

        value = pk_value
        if self._pk in data.keys():
            # if primary key already on record, extract it and remove it from update list
            value = data[self._pk]
            del data[self._pk]

        if value is None:
            raise RepositoryError("update(): missing primary key value")
        sql, values = Update(self._dialect).table(self._tablename, self._schema) \
            .values(data) \
            .where(self._pk, '=', value).assemble()
        with self._db.cursor() as c:
            c.exec(sql, values)

    def update_where(self, record, where_list: list):
        """
        Updates a record with a custom where condition list

        Each where condition must be in the form (fieldname, value) or (fieldname, operator, value)

        :param record: record to update
        :param where_list: list of where conditions
        :return:
        """
        if type(where_list) not in [list, tuple]:
            raise RepositoryError("update_where(): invalid type for where clause list")
        if len(where_list) == 0:
            raise RepositoryError("update_where(): where clause list cannot be empty")

        qry = Update(self._dialect).table(self._tablename, self._schema).values(record)
        for cond in where_list:
            if type(cond) not in [list, tuple]:
                raise RepositoryError("update_where(): invalid item in where clause list")
            lc = len(cond)
            if lc == 2:
                qry.where(cond[0], operator='=', value=cond[1])
            elif lc == 3:
                qry.where(cond[0], operator=cond[1], value=cond[2])
            else:
                raise RepositoryError("update_where(): invalid item in where clause list")

        sql, values = qry.assemble()
        with self._db.cursor() as c:
            c.exec(sql, values)

    def count(self) -> int:
        """
        Retrieve number of records in the table

        :return: int
        """
        values = None
        sql = self._cache_get('count')
        if sql is None:
            sql, values = self.select(cols={Literal('COUNT(*)'): 'total'}).assemble()
            self._cache_set('count', sql)
        result = self._db.cursor().fetchone(sql, values)
        if result is not None:
            return result['total']
        return 0

    def count_where(self, where_list: list):
        """
        Retrieve record count using WHERE clause

        Each where condition must be in the form (fieldname, value) or (fieldname, operator, value)

        :param where_list: list of where conditions
        :return:
        """
        if type(where_list) not in [list, tuple]:
            raise RepositoryError("count_where(): invalid type for where clause list")
        if len(where_list) == 0:
            raise RepositoryError("count_where(): where clause list cannot be empty")

        qry = self.select(cols={Literal('COUNT(*)'): 'total'})
        for cond in where_list:
            if type(cond) not in [list, tuple]:
                raise RepositoryError("count_where(): invalid item in where clause list")
            lc = len(cond)
            if lc == 2:
                qry.where(cond[0], operator='=', value=cond[1])
            elif lc == 3:
                qry.where(cond[0], operator=cond[1], value=cond[2])
            else:
                raise RepositoryError("count_where(): invalid item in where clause list")

        sql, values = qry.assemble()
        with self._db.cursor() as c:
            result = c.fetchone(sql, values)
            if result is not None:
                return result['total']
            return 0

    def list(self, qry: Select, limit=None, offset=None, cls=None):
        """
        Performs a query with offset and limit
        Returns a tuple with total record count for the query, and the rows returned by applying offset and limit

        The original query object is left intact

        :param qry: query to use
        :param limit:
        :param offset:
        :param cls: optional Record class to use for rows
        :return: (total_rows, selected_row_list)
        """
        total = 0
        qry = copy.deepcopy(qry)
        sql, values = qry.assemble()
        qry_count = Select(self._dialect).from_({Literal(sql): "qry"}, cols={Literal('COUNT(*)'): 'total'})
        if limit:
            qry.limit(limit, offset)

        with self._db.cursor() as c:
            # count total rows
            sql, _ = qry_count.assemble()
            count_record = c.fetchone(sql, values)
            if count_record:
                total = count_record['total']

        # fetch rows
        rows = self.fetch(qry, cls=cls)
        return total, rows

    def _cache_get(self, key) -> Union[str, None]:
        return self._query_cache.get(self._key_prefix + key)

    def _cache_set(self, key, value):
        return self._query_cache.set(self._key_prefix + key, value)


# global query cache for all repositories
query_cache = StrCache()
