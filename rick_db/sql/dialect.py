from rick_db.sql import SqlError, Literal


class SqlDialect:
    """
    Base SqlDialect class

    SqlDialect implements schema, table and field quoting specifics to be used on the query builder
    """

    def __init__(self):
        # public properties
        self.placeholder = "?"
        self.insert_returning = True  # if true, INSERT...RETURNING syntax is supported
        self.ilike = True  # if true, ILIKE is supported

        # internal properties
        self._quote_table = '"{table}"'
        self._quote_field = '"{field}"'
        self._quote_schema = '"{schema}"'
        self._separator = "."
        self._as = " AS "
        self._cast = "CAST({field} AS {cast})"

    def table(self, table_name, alias=None, schema=None):
        """
        Quotes a table name
        :param table_name: table name
        :param alias: optional alias
        :param schema: optional schema
        :return: str

        Examples:
            table('tbl', None, None) -> "tbl"
            table('tbl', 'alias', 'schema') -> "schema"."tbl" AS "alias"
        """
        if not isinstance(table_name, Literal):
            # table is a string to be quoted and schema-prefixed
            table_name = self._quote_table.format(table=table_name)

            if schema is not None:
                table_name = self._quote_schema.format(schema=schema) + self._separator + table_name
        else:
            # table_name is actually a Literal expression, just add parenthesis
            table_name = "({table})".format(table=table_name)

        if alias is None:
            return table_name
        return self._as.join([table_name, self._quote_table.format(table=alias)])

    def field(self, field, field_alias=None, table=None, schema=None):
        """
        Quotes a field name
        :param field: field name or Literal
        :param field_alias: optional alias and/or cast information
        :param table: optional table
        :param schema: optional schema (not supported)
        :return: str

        Examples:
            field('field', None) -> "field"
            field('field', 'alias') -> "field" AS "alias"
            field('field', ['text']) -> CAST("field" AS text)
            field('field', ['text', 'alias']) -> CAST("field" AS text) AS "alias"
            field(Literal('COUNT(*)'), ['int', 'total']) -> CAST(COUNT(*) AS int) AS "total"
            field('field', 'alias', 'table') -> "table"."field" AS "alias"
            field('field', 'alias', 'table', 'public') -> "public"."table"."field" AS "alias"
        """
        if table is not None:
            table = self._quote_table.format(table=table) + self._separator
            if schema is not None:
                table = self._quote_schema.format(schema=schema) + self._separator + table
        else:
            table = ""

        if isinstance(field, Literal):
            field = str(field)
            table = ""
        elif field != "*":
            field = self._quote_field.format(field=field)
        field = table + field

        if field_alias is None:
            return field
        elif isinstance(field_alias, str):
            return self._as.join([field, self._quote_field.format(field=field_alias)])
        elif isinstance(field_alias, (list, tuple)):
            _len = len(field_alias)
            if _len == 0:
                raise SqlError("Alias for field %s cannot be empty" % field)
            field = self._cast.format(field=field, cast=field_alias[0])
            if _len > 1:
                return self._as.join([field, self._quote_field.format(field=field_alias[1])])
            else:
                return field
        else:
            raise SqlError("Cannot parse fields")


class DefaultSqlDialect(SqlDialect):
    """
    Default SqlDialect
    """
    pass


class PgSqlDialect(SqlDialect):
    """
    PostgreSQL SqlDialect implementation
    """

    def __init__(self):
        # public properties
        self.placeholder = "%s"
        self.insert_returning = True  # if true, INSERT...RETURNING syntax is supported
        self.ilike = True  # if true, ILIKE is supported

        self._quote_table = '"{table}"'
        self._quote_field = '"{field}"'
        self._quote_schema = '"{schema}"'
        self._separator = "."
        self._cast = "::"
        self._as = " AS "

    def field(self, field, field_alias=None, table=None, schema=None):
        """
        Quotes a field name, optimizing for PostgreSQL syntax

        :param field: field name or Literal
        :param field_alias: optional alias and/or cast information
        :param table: optional table
        :param schema: optional schema
        :return: str

        Examples:
            field('field', None) -> "field"
            field('field', 'alias') -> "field" AS "alias"
            field('field', ['text']) -> "field"::text
            field('field', ['text', 'alias']) -> "field"::text AS "alias"
            field(Literal('COUNT(*)'), ['int', 'total']) -> COUNT(*)::int AS "total"
            field('field', 'alias', 'table') -> "table"."field" AS "alias"
            field('field', 'alias', 'table', 'public') -> "public"."table"."field" AS "alias"
        """
        if table is not None:
            table = self._quote_table.format(table=table) + self._separator
            if schema is not None:
                table = self._quote_schema.format(schema=schema) + self._separator + table
        else:
            table = ""

        if isinstance(field, Literal):
            field = str(field)
            table = ""
        elif field != "*":
            field = self._quote_field.format(field=field)
        field = table + field

        if field_alias is None:
            return field
        elif isinstance(field_alias, str):
            return self._as.join([field, self._quote_field.format(field=field_alias)])
        elif isinstance(field_alias, (list, tuple)):
            _len = len(field_alias)
            if _len == 0:
                raise SqlError("Alias for field %s cannot be empty" % field)
            # generate pg-style cast with ::<type>
            cast = self._cast + field_alias[0]
            if _len > 1:
                return self._as.join([field + cast, self._quote_field.format(field=field_alias[1])])
            else:
                return field + cast
        else:
            raise SqlError("Cannot parse fields")


class Sqlite3SqlDialect(SqlDialect):

    def __init__(self):
        super(Sqlite3SqlDialect, self).__init__()
        self.placeholder = "?"
        self.insert_returning = False
        self.ilike = False
