import collections
from inspect import isclass
from typing import Union

from rick_db.mapper import ATTR_SCHEMA, ATTR_TABLE
from rick_db.sql import SqlError, SqlDialect, DefaultSqlDialect, SqlStatement, Sql, Select, Literal


class Update(SqlStatement):

    def __init__(self, dialect: SqlDialect = None):
        """
        INSERT constructor
        """
        self._table = ""
        self._schema = None
        self._fields = []
        self._values = []
        self._clauses = []
        self._clause_values = []

        if dialect is None:
            dialect = DefaultSqlDialect()
        self._dialect = dialect

    def table(self, table, schema=None):
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
                raise SqlError("table(): invalid type for table name")
            if not isclass(table):
                self.values(table)
            table = tname
        else:
            raise SqlError("table(): invalid type for table name")

        if schema is not None and not isinstance(schema, str):
            raise SqlError("table(): Invalid type for schema name: %s" % str(type(schema)))

        self._table = table
        self._schema = schema
        return self

    def fields(self, fields: list):
        """
        Set fields for update
        :param fields: list of field names
        :return: self
        """
        if not isinstance(fields, (list, tuple)):
            raise SqlError("fields(): invalid type for fields parameter")

        self._fields = fields
        return self

    def values(self, values: Union[list, dict, object]):
        """
        Set fields and/or values for update

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

    def where(self, field, operator=None, value=None):
        """
        WHERE clause
        Multiple calls concat with AND

        :param field: expression
        :param operator: clause operator
        :param value: optional value
        :return: self
        """
        return self._where(field, operator, value)

    def orwhere(self, field, operator=None, value=None):
        """
        WHERE clause
        Multiple calls concat with OR

        :param field: expression
        :param operator: clause operator
        :param value: optional value
        :return: self
        """
        return self._where(field, operator, value, is_and=False)

    def _where(self, field, operator=None, value=None, is_and=True):
        """
        Internal where handler

        :param field: expression
        :param operator: clause operator
        :param value: optional value
        :param is_and: True to interleave with AND, False to OR
        :return: self
        """
        concat = Sql.SQL_AND
        if is_and is False:
            concat = Sql.SQL_OR

        if isinstance(field, str):
            field = self._dialect.field(field)
        elif isinstance(field, Literal):
            field = str(field)
        else:
            raise SqlError("_where(): invalid field name type")

        if value is None:
            if operator is None:
                expression = "{fld}".format(fld=field)
            else:
                expression = "{fld} {op}".format(fld=field, op=operator)
            self._clauses.append([expression, concat])
        else:
            # sanity check, as we actually may have value list if subquery is in use
            if isinstance(value, (list, tuple, dict)):
                raise SqlError("_where(): invalid value type: %s" % str(type(value)))

            if operator is None:
                expression = "{fld} {ph}".format(fld=field, ph=self._dialect.placeholder)
            else:
                if isinstance(value, Select):
                    sql, value = value.assemble()
                    expression = "{fld} {op} ({query})".format(fld=field, op=operator, query=sql)
                else:
                    expression = "{fld} {op} {ph}".format(fld=field, op=operator, ph=self._dialect.placeholder)

            self._clauses.append([expression, concat])
            if isinstance(value, list):
                self._clause_values.extend(value)
            else:
                self._clause_values.append(value)
        return self

    def assemble(self):
        """
        Assemble the UPDATE statement
        :return: tuple(str, list)
        """
        # simple validations
        lf = len(self._fields)
        if lf == 0:
            raise SqlError("assemble(): field list is empty")
        if lf != len(self._values):
            raise SqlError("assemble(): field and value count mismatch")

        parts = [
            Sql.SQL_UPDATE,
            self._dialect.table(self._table, None, schema=self._schema),
            Sql.SQL_SET,
        ]

        # generate field list and placeholder list
        fields = []
        for name in self._fields:
            fields.append("{field}={ph}".format(field=self._dialect.field(name), ph=self._dialect.placeholder))
        parts.append(", ".join(fields))
        values = self._values

        # where clause
        if len(self._clauses) > 0:
            c = 0
            parts.append(Sql.SQL_WHERE)
            values.extend(self._clause_values)

            for clause in self._clauses:
                expr, concat = clause
                if c > 0:
                    parts.append(concat)
                parts.append(expr)
                c += 1

        return " ".join(parts), values
