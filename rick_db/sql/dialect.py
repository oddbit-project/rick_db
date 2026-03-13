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
        self.json_support = False  # if true, JSON operations are supported

        # internal properties
        self._quote_table = '"{table}"'
        self._quote_field = '"{field}"'
        self._quote_schema = '"{schema}"'
        self._quote_database = '"{database}"'
        self._separator = "."
        self._as = " AS "
        self._cast = "CAST({field} AS {cast})"

        # JSON operators (to be overridden by specific dialects)
        self._json_extract = "JSON_EXTRACT({field}, {path})"  # Extract value from JSON
        self._json_extract_text = "JSON_EXTRACT({field}, {path})"  # Extract as text
        self._json_contains = (
            "JSON_CONTAINS({field}, {value})"  # Check if JSON contains value
        )
        self._json_contains_path = (
            "JSON_CONTAINS_PATH({field}, 'one', {path})"  # Check if path exists
        )

    def _qi(self, identifier):
        """
        Quote a SQL identifier, escaping embedded double-quotes by doubling them
        (SQL standard).

        :param identifier: identifier name (table, field, schema, database)
        :return: quoted identifier string, e.g. '"my_table"'
        """
        escaped = identifier.replace('"', '""')
        return '"{}"'.format(escaped)

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
            table_name = self._qi(table_name)

            if schema is not None:
                table_name = (
                    self._qi(schema)
                    + self._separator
                    + table_name
                )
        else:
            # table_name is actually a Literal expression, just add parenthesis
            table_name = "({table})".format(table=table_name)

        if alias is None:
            return table_name
        return self._as.join([table_name, self._qi(alias)])

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
            table = self._qi(table) + self._separator
            if schema is not None:
                table = (
                    self._qi(schema) + self._separator + table
                )
        else:
            table = ""

        if isinstance(field, Literal):
            field = str(field)
            table = ""
        elif field != "*":
            field = self._qi(field)
        field = table + field

        if field_alias is None:
            return field
        elif isinstance(field_alias, str):
            return self._as.join([field, self._qi(field_alias)])
        elif isinstance(field_alias, (list, tuple)):
            _len = len(field_alias)
            if _len == 0:
                raise SqlError("Alias for field %s cannot be empty" % field)
            field = self._cast.format(field=field, cast=field_alias[0])
            if _len > 1:
                return self._as.join(
                    [field, self._qi(field_alias[1])]
                )
            else:
                return field
        else:
            raise SqlError("Cannot parse fields")

    def database(self, database_name, alias=None):
        """
        Quotes a database name
        :param database_name: database name
        :param alias: optional alias
        :return: str

        Examples:
            database('name', None, None) -> "name"
            table('name', 'alias') -> "name" AS "alias"
        """
        if not isinstance(database_name, Literal):
            # database_name is a string to be quoted
            database_name = self._qi(database_name)
        else:
            # database_name is actually a Literal expression, just add parenthesis
            database_name = "({database})".format(database=database_name)

        if alias is None:
            return database_name
        return self._as.join(
            [database_name, self._qi(alias)]
        )

    def _json_field_expr(self, field):
        """
        Resolve a field reference for JSON operations.
        Handles plain strings, table-qualified strings (with dot), and Literal expressions.

        :param field: field name, table.field string, or Literal
        :return: quoted field expression string
        """
        if isinstance(field, Literal):
            return str(field)
        elif isinstance(field, str):
            if "." in field:
                parts = field.split(".", 1)
                return self.field(parts[1], table=parts[0])
            else:
                return self._qi(field)
        else:
            return str(field)

    def json_extract(self, field, path, alias=None):
        """
        Extract a value from a JSON field

        :param field: JSON field name, table-qualified string, or Literal expression
        :param path: JSON path to extract
        :param alias: optional alias for the result
        :return: SQL expression string
        :raises: SqlError if JSON is not supported

        Examples:
            json_extract('data', '$.name') -> JSON_EXTRACT("data", '$.name')
            json_extract('data', '$.name', 'username') -> JSON_EXTRACT("data", '$.name') AS "username"
        """
        if not self.json_support:
            raise SqlError("JSON operations not supported in this SQL dialect")

        field_expr = self._json_field_expr(field)

        if (
            isinstance(path, str)
            and not path.startswith("'")
            and not path.startswith('"')
        ):
            path = "'{}'".format(path)

        expr = self._json_extract.format(field=field_expr, path=path)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr

    def json_extract_text(self, field, path, alias=None):
        """
        Extract a value from a JSON field as text

        :param field: JSON field name, table-qualified string, or Literal expression
        :param path: JSON path to extract
        :param alias: optional alias for the result
        :return: SQL expression string
        :raises: SqlError if JSON is not supported

        Examples:
            json_extract_text('data', '$.name') -> JSON_EXTRACT("data", '$.name')
            json_extract_text('data', '$.name', 'username') -> JSON_EXTRACT("data", '$.name') AS "username"
        """
        if not self.json_support:
            raise SqlError("JSON operations not supported in this SQL dialect")

        field_expr = self._json_field_expr(field)

        if (
            isinstance(path, str)
            and not path.startswith("'")
            and not path.startswith('"')
        ):
            path = "'{}'".format(path)

        expr = self._json_extract_text.format(field=field_expr, path=path)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr

    def json_contains(self, field, value, alias=None):
        """
        Check if a JSON field contains a value.

        The generated SQL uses a parameter placeholder for the value.
        The value argument itself is not interpolated into the SQL string;
        it should be passed separately to the query executor for parameter binding.

        :param field: JSON field name, table-qualified string, or Literal expression
        :param value: Value to check for (used for parameter binding, not interpolated into SQL)
        :param alias: optional alias for the result
        :return: SQL expression string
        :raises: SqlError if JSON is not supported
        """
        if not self.json_support:
            raise SqlError("JSON operations not supported in this SQL dialect")

        field_expr = self._json_field_expr(field)

        expr = self._json_contains.format(field=field_expr, value=self.placeholder)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr

    def json_contains_path(self, field, path, alias=None):
        """
        Check if a JSON path exists in a JSON field

        :param field: JSON field name, table-qualified string, or Literal expression
        :param path: JSON path to check
        :param alias: optional alias for the result
        :return: SQL expression string
        :raises: SqlError if JSON is not supported

        Examples:
            json_contains_path('data', '$.name') -> JSON_CONTAINS_PATH("data", 'one', '$.name')
            json_contains_path('data', '$.name', 'has_name') -> JSON_CONTAINS_PATH("data", 'one', '$.name') AS "has_name"
        """
        if not self.json_support:
            raise SqlError("JSON operations not supported in this SQL dialect")

        field_expr = self._json_field_expr(field)

        if (
            isinstance(path, str)
            and not path.startswith("'")
            and not path.startswith('"')
        ):
            path = "'{}'".format(path)

        expr = self._json_contains_path.format(field=field_expr, path=path)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr


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
        super().__init__()
        # public properties
        self.placeholder = "%s"
        self.insert_returning = True  # if true, INSERT...RETURNING syntax is supported
        self.ilike = True  # if true, ILIKE is supported
        self.json_support = True  # PostgreSQL has excellent JSON support

        # internal properties
        self._cast = "::"

        # PostgreSQL specific JSON operators
        self._json_extract = (
            "{field}->>{path}"  # ->> gets as text (most common use case)
        )
        self._json_extract_text = "{field}->>{path}"  # Same as extract for PostgreSQL
        self._json_extract_object = "{field}->{path}"  # -> gets as JSON
        self._json_contains = (
            "{field} @> {value}::jsonb"  # @> contains operator (for JSONB)
        )
        self._json_contains_path = (
            "{field} ?? {path}"  # ?? checks if path exists (for JSONB)
        )

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
            table = self._qi(table) + self._separator
            if schema is not None:
                table = (
                    self._qi(schema) + self._separator + table
                )
        else:
            table = ""

        if isinstance(field, Literal):
            field = str(field)
            table = ""
        elif field != "*":
            field = self._qi(field)
        field = table + field

        if field_alias is None:
            return field
        elif isinstance(field_alias, str):
            return self._as.join([field, self._qi(field_alias)])
        elif isinstance(field_alias, (list, tuple)):
            _len = len(field_alias)
            if _len == 0:
                raise SqlError("Alias for field %s cannot be empty" % field)
            # generate pg-style cast with ::<type>
            cast = self._cast + field_alias[0]
            if _len > 1:
                return self._as.join(
                    [field + cast, self._qi(field_alias[1])]
                )
            else:
                return field + cast
        else:
            raise SqlError("Cannot parse fields")

    def _pg_path_expr(self, path):
        """
        Convert a path argument to PostgreSQL key/index format.
        Strips jsonpath prefix (e.g. $.name -> name), handles numeric indices.

        :param path: key name, array index, or jsonpath expression
        :return: formatted path expression
        """
        if isinstance(path, int) or (isinstance(path, str) and path.isdigit()):
            return str(path)
        if isinstance(path, str):
            if path.startswith("$."):
                path = path[2:]
            path = path.strip("'\"")
            return "'{}'".format(path)
        return str(path)

    def json_extract(self, field, path, alias=None):
        """
        Extract a value from a JSON/JSONB field as text using ->> operator.

        :param field: JSON field name, table-qualified string, or Literal expression
        :param path: key name or array index (jsonpath $. prefix is stripped automatically)
        :param alias: optional alias for the result
        :return: SQL expression string

        Examples:
            json_extract('data', 'name') -> "data"->>'name'
            json_extract('data', '$.name') -> "data"->>'name'
            json_extract('data', 0) -> "data"->>0
        """
        if not self.json_support:
            raise SqlError("JSON operations not supported in this SQL dialect")

        field_expr = self._json_field_expr(field)
        path_expr = self._pg_path_expr(path)

        expr = self._json_extract.format(field=field_expr, path=path_expr)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr

    def json_extract_text(self, field, path, alias=None):
        """
        Extract a value from a JSON/JSONB field as text using ->> operator.

        :param field: JSON field name, table-qualified string, or Literal expression
        :param path: key name or array index (jsonpath $. prefix is stripped automatically)
        :param alias: optional alias for the result
        :return: SQL expression string

        Examples:
            json_extract_text('data', 'name') -> "data"->>'name'
            json_extract_text('data', '$.name') -> "data"->>'name'
        """
        if not self.json_support:
            raise SqlError("JSON operations not supported in this SQL dialect")

        field_expr = self._json_field_expr(field)
        path_expr = self._pg_path_expr(path)

        expr = self._json_extract_text.format(field=field_expr, path=path_expr)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr

    def json_extract_object(self, field, path, alias=None):
        """
        Extract a JSON object from a JSON/JSONB field (PostgreSQL specific)
        Uses the -> operator which preserves the JSON type

        :param field: JSON field name, table-qualified string, or Literal expression
        :param path: key name or array index (jsonpath $. prefix is stripped automatically)
        :param alias: optional alias for the result
        :return: SQL expression string

        Examples:
            json_extract_object('data', 'name') -> "data"->'name'
            json_extract_object('data', 0) -> "data"->0
        """
        field_expr = self._json_field_expr(field)
        path_expr = self._pg_path_expr(path)

        expr = self._json_extract_object.format(field=field_expr, path=path_expr)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr

    def json_path_query(self, field, path, alias=None):
        """
        PostgreSQL specific jsonpath query (for PostgreSQL 12+)
        Uses the @? operator with jsonpath syntax

        :param field: JSON field name, table-qualified string, or Literal expression
        :param path: jsonpath expression
        :param alias: optional alias for the result
        :return: SQL expression string

        Examples:
            json_path_query('data', '$.name') -> "data"::jsonb @? '$.name'
        """
        field_expr = self._json_field_expr(field)

        if not path.startswith("'"):
            path = "'{}'".format(path)

        expr = "{}::jsonb @? {}".format(field_expr, path)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr


class MySqlSqlDialect(SqlDialect):
    """
    MySQL SqlDialect implementation
    """

    def __init__(self):
        super().__init__()
        self.placeholder = "%s"
        self.insert_returning = False
        self.ilike = False
        self.json_support = True

        # Override only _json_extract_text for unquoted text extraction
        self._json_extract_text = "JSON_UNQUOTE(JSON_EXTRACT({field}, {path}))"

    def _qi(self, identifier):
        """
        Quote a SQL identifier with backticks, escaping embedded backticks by doubling.

        :param identifier: identifier name (table, field, schema, database)
        :return: quoted identifier string, e.g. `my_table`
        """
        escaped = identifier.replace('`', '``')
        return '`{}`'.format(escaped)


class ClickHouseSqlDialect(SqlDialect):
    """
    ClickHouse SqlDialect implementation
    """

    def __init__(self):
        super().__init__()
        self.placeholder = "%s"
        self.insert_returning = False  # ClickHouse has no RETURNING
        self.ilike = True  # ClickHouse supports ILIKE
        self.json_support = True  # ClickHouse has JSON functions

        self._cast = "CAST({field} AS {cast})"

        # ClickHouse JSON operators use function syntax
        self._json_extract = "JSONExtractString({field}, {path})"
        self._json_extract_text = "JSONExtractString({field}, {path})"
        self._json_contains = "JSONHas({field}, {value})"
        self._json_contains_path = "JSON_EXISTS({field}, {path})"

    def _ch_path_expr(self, path):
        """
        Convert a path argument to ClickHouse JSON function format.
        Strips jsonpath prefix (e.g. $.name -> name).

        :param path: key name or jsonpath expression
        :return: formatted path expression
        """
        if isinstance(path, str):
            if path.startswith("$."):
                path = path[2:]
            path = path.strip("'\"")
            return "'{}'".format(path)
        return str(path)

    def json_extract(self, field, path, alias=None):
        """
        Extract a value from a JSON field using JSONExtractString.

        :param field: JSON field name, table-qualified string, or Literal expression
        :param path: key name (jsonpath $. prefix is stripped automatically)
        :param alias: optional alias for the result
        :return: SQL expression string
        """
        if not self.json_support:
            raise SqlError("JSON operations not supported in this SQL dialect")

        field_expr = self._json_field_expr(field)
        path_expr = self._ch_path_expr(path)

        expr = self._json_extract.format(field=field_expr, path=path_expr)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr

    def json_extract_text(self, field, path, alias=None):
        """
        Extract a value from a JSON field as text using JSONExtractString.

        :param field: JSON field name, table-qualified string, or Literal expression
        :param path: key name (jsonpath $. prefix is stripped automatically)
        :param alias: optional alias for the result
        :return: SQL expression string
        """
        if not self.json_support:
            raise SqlError("JSON operations not supported in this SQL dialect")

        field_expr = self._json_field_expr(field)
        path_expr = self._ch_path_expr(path)

        expr = self._json_extract_text.format(field=field_expr, path=path_expr)

        if alias:
            return self._as.join([expr, self._qi(alias)])
        return expr


class Sqlite3SqlDialect(SqlDialect):
    def __init__(self):
        super(Sqlite3SqlDialect, self).__init__()
        self.placeholder = "?"
        self.insert_returning = True  # since 3.35.0
        self.ilike = False
