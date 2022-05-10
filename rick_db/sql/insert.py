import collections
from inspect import isclass
from typing import Union

from rick_db.mapper import ATTR_SCHEMA, ATTR_TABLE
from rick_db.sql import SqlError, SqlDialect, DefaultSqlDialect, SqlStatement, Sql


class Insert(SqlStatement):

    def __init__(self, dialect: SqlDialect = None):
        """
        INSERT constructor
        """
        self._table = ""
        self._schema = None
        self._fields = []
        self._values = []
        self._returning = []

        if dialect is None:
            dialect = DefaultSqlDialect()
        self._dialect = dialect

    def into(self, table, schema=None):
        """
        Sets table name and schema
        if table is object, it will also set fields and values
        :param table: string or record object
        :param schema: optional string
        :return: self
        """
        if isinstance(table, str):
            pass
        elif isinstance(table, object):
            schema = getattr(table, ATTR_SCHEMA, schema)
            tname = getattr(table, ATTR_TABLE, None)
            if tname is None:
                raise SqlError("into(): invalid type for table name")
            if not isclass(table):
                self.values(table)
            table = tname
        else:
            raise SqlError("into(): invalid type for table name")

        if schema is not None and not isinstance(schema, str):
            raise SqlError("into(): Invalid type for schema name: %s" % str(type(schema)))

        self._table = table
        self._schema = schema
        return self

    def fields(self, fields: list):
        """
        Set fields for insertion
        :param fields: list of field names
        :return: self
        """
        if not isinstance(fields, (list, tuple)):
            raise SqlError("fields(): invalid type for fields parameter")

        self._fields = fields
        return self

    def values(self, values: Union[list, dict, object]):
        """
        Set fields and/or values for insertion

        This method can be called multiple times; new field/value pairs will be added to the internal structure;
        Existing fields will have their value overridden

        :param values: list, dict or record object
        :return: self
        """
        # if list, replace values
        if isinstance(values, (list, tuple)):
            self._values = values

        elif isinstance(values, collections.abc.Mapping):
            self._fields = values.keys()
            self._values = list(values.values())

        elif isinstance(values, object):
            # support any object that has a method "asrecord"
            if not callable(getattr(values, 'asrecord', None)):
                raise SqlError("values(): invalid object type for data parameter")
            values = values.asrecord()
            self._fields = values.keys()
            self._values = list(values.values())
        else:
            raise SqlError("values(): Invalid data type")

        return self

    def returning(self, fields):
        """
        RETURNING clause
        :param fields: str or list with fields to be returned
        :return: self
        """
        if isinstance(fields, str):
            fields = [fields]

        if not isinstance(fields, (list, tuple)):
            raise SqlError("returning(): invalid return field type: %s" % str(type(fields)))

        if len(fields) == 0:
            raise SqlError("returning(): field list cannot be empty")

        self._returning = fields
        return self

    def get_values(self):
        """
        Retrieve current values
        :return: list
        """
        return self._values

    def assemble(self):
        """
        Assemble the INSERT SQL
        :return: tuple(str, list)
        """
        # simple validations
        lf = len(self._fields)
        if lf == 0:
            raise SqlError("assemble(): field list is empty")
        if lf != len(self._values):
            raise SqlError("assemble(): field and value count mismatch")

        parts = [
            Sql.SQL_INSERT,
            self._dialect.table(self._table, None, schema=self._schema)
        ]

        # generate field list and placeholder list
        fields = []
        placeholders = []
        for name in self._fields:
            fields.append(self._dialect.field(name))
            placeholders.append(self._dialect.placeholder)

        parts.append("({})".format(", ".join(fields)))
        parts.append(Sql.SQL_VALUES)
        parts.append("({})".format(", ".join(placeholders)))

        # optional returning clause
        if self._returning:
            fields = []
            for name in self._returning:
                fields.append(self._dialect.field(name))

            parts.append(Sql.SQL_RETURNING)
            parts.append(", ".join(fields))

        return " ".join(parts), self._values
