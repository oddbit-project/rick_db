from rick_db.mapper import ATTR_TABLE, ATTR_SCHEMA
from rick_db.sql import SqlStatement, SqlDialect, SqlError, Sql, Literal, DefaultSqlDialect, Select


class Delete(SqlStatement):

    def __init__(self, dialect: SqlDialect = None):
        """
        DELETE constructor
        :param dialect: optional SQL dialect

        """
        self._table = None
        self._schema = None
        self._clauses = []
        self._values = []

        if dialect is None:
            dialect = DefaultSqlDialect()
        self._dialect = dialect

    def from_(self, table, schema=None):
        """
        DELETE FROM table name and schema
        :param table: string or record object
        :param schema: optional string
        :return: self

        Possible values for table:
            'table' -> string with table name
            <object_or_class> -> record class or object
        """
        if isinstance(table, str):
            pass
        elif isinstance(table, object):
            schema = getattr(table, ATTR_SCHEMA, schema)
            table = getattr(table, ATTR_TABLE, None)
            if table is None:
                raise SqlError("from_(): invalid type for table name")
        else:
            raise SqlError("from_(): invalid type for table name")

        if schema is not None and type(schema) is not str:
            raise SqlError("from_(): Invalid type for schema name: %s" % str(type(schema)))

        self._table = table
        self._schema = schema
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
                self._values.extend(value)
            else:
                self._values.append(value)
        return self

    def assemble(self):
        """
        Generate SQL
        :return: tuple(str, list)
        """
        parts = [Sql.SQL_DELETE, self._dialect.table(self._table, None, self._schema)]

        if len(self._clauses) > 0:
            c = 0
            parts.append(Sql.SQL_WHERE)
            for clause in self._clauses:
                expr, concat = clause
                if c > 0:
                    parts.append(concat)
                parts.append(expr)
                c += 1

        return " ".join(parts), self._values
