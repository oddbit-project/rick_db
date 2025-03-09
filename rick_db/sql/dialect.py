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
        self._json_contains = "JSON_CONTAINS({field}, {value})"  # Check if JSON contains value
        self._json_contains_path = "JSON_CONTAINS_PATH({field}, 'one', {path})"  # Check if path exists

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
                table_name = (
                    self._quote_schema.format(schema=schema)
                    + self._separator
                    + table_name
                )
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
                table = (
                    self._quote_schema.format(schema=schema) + self._separator + table
                )
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
                return self._as.join(
                    [field, self._quote_field.format(field=field_alias[1])]
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
            # database_name is a string to be
            database_name = self._quote_database.format(database=database_name)
        else:
            # database_name is actually a Literal expression, just add parenthesis
            database_name = "({database})".format(database=database_name)

        if alias is None:
            return database_name
        return self._as.join(
            [database_name, self._quote_database.format(database=alias)]
        )
        
    def json_extract(self, field, path, alias=None):
        """
        Extract a value from a JSON field
        
        :param field: JSON field name or expression
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
            
        field_expr = self.field(field) if not isinstance(field, str) or "." in field else self._quote_field.format(field=field)
        
        if isinstance(path, str) and not path.startswith("'") and not path.startswith('"'):
            # Add quotes to path if needed
            path = f"'{path}'"
            
        expr = self._json_extract.format(field=field_expr, path=path)
        
        if alias:
            return self._as.join([expr, self._quote_field.format(field=alias)])
        return expr
        
    def json_extract_text(self, field, path, alias=None):
        """
        Extract a value from a JSON field as text
        
        :param field: JSON field name or expression
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
            
        field_expr = self.field(field) if not isinstance(field, str) or "." in field else self._quote_field.format(field=field)
        
        if isinstance(path, str) and not path.startswith("'") and not path.startswith('"'):
            # Add quotes to path if needed
            path = f"'{path}'"
            
        expr = self._json_extract_text.format(field=field_expr, path=path)
        
        if alias:
            return self._as.join([expr, self._quote_field.format(field=alias)])
        return expr
        
    def json_contains(self, field, value, alias=None):
        """
        Check if a JSON field contains a value
        
        :param field: JSON field name or expression
        :param value: Value to check for (will be converted to JSON)
        :param alias: optional alias for the result
        :return: SQL expression string
        :raises: SqlError if JSON is not supported
        
        Examples:
            json_contains('data', '"value"') -> JSON_CONTAINS("data", '"value"')
            json_contains('data', '"value"', 'has_value') -> JSON_CONTAINS("data", '"value"') AS "has_value"
        """
        if not self.json_support:
            raise SqlError("JSON operations not supported in this SQL dialect")
            
        field_expr = self.field(field) if not isinstance(field, str) or "." in field else self._quote_field.format(field=field)
        
        # For value, we'll use placeholder
        expr = self._json_contains.format(field=field_expr, value=self.placeholder)
        
        if alias:
            return self._as.join([expr, self._quote_field.format(field=alias)])
        return expr
        
    def json_contains_path(self, field, path, alias=None):
        """
        Check if a JSON path exists in a JSON field
        
        :param field: JSON field name or expression
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
            
        field_expr = self.field(field) if not isinstance(field, str) or "." in field else self._quote_field.format(field=field)
        
        if isinstance(path, str) and not path.startswith("'") and not path.startswith('"'):
            # Add quotes to path if needed
            path = f"'{path}'"
            
        expr = self._json_contains_path.format(field=field_expr, path=path)
        
        if alias:
            return self._as.join([expr, self._quote_field.format(field=alias)])
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
        self._json_extract = "{field}->>{path}"  # ->> gets as text (most common use case)
        self._json_extract_text = "{field}->>{path}"  # Same as extract for PostgreSQL
        self._json_extract_object = "{field}->{path}"  # -> gets as JSON
        self._json_contains = "{field} @> {value}::jsonb"  # @> contains operator (for JSONB)
        self._json_contains_path = "{field} ?? {path}"  # ?? checks if path exists (for JSONB)

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
                table = (
                    self._quote_schema.format(schema=schema) + self._separator + table
                )
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
                return self._as.join(
                    [field + cast, self._quote_field.format(field=field_alias[1])]
                )
            else:
                return field + cast
        else:
            raise SqlError("Cannot parse fields")
            
    def json_extract_object(self, field, path, alias=None):
        """
        Extract a JSON object from a JSON/JSONB field (PostgreSQL specific)
        Uses the -> operator which preserves the JSON type
        
        :param field: JSON field name or expression
        :param path: JSON path to extract (without quotes for numeric path, with quotes for key names)
        :param alias: optional alias for the result
        :return: SQL expression string
        
        Examples:
            json_extract_object('data', '0') -> "data"->0
            json_extract_object('data', '"name"') -> "data"->"name"
            json_extract_object('data', '"name"', 'user_obj') -> "data"->"name" AS "user_obj"
        """
        field_expr = self.field(field) if not isinstance(field, str) or "." in field else self._quote_field.format(field=field)
        
        # In PostgreSQL, numeric paths don't need quotes, text keys do
        if path.isdigit():
            path_expr = path
        elif path.startswith('"') and path.endswith('"'):
            path_expr = path  # Already quoted
        else:
            path_expr = f'"{path}"'  # Add quotes to text keys
            
        expr = self._json_extract_object.format(field=field_expr, path=path_expr)
        
        if alias:
            return self._as.join([expr, self._quote_field.format(field=alias)])
        return expr
        
    def json_path_query(self, field, path, alias=None):
        """
        PostgreSQL specific jsonpath query (for PostgreSQL 12+)
        Uses the @? operator with jsonpath syntax
        
        :param field: JSON field name or expression
        :param path: jsonpath expression
        :param alias: optional alias for the result
        :return: SQL expression string
        
        Examples:
            json_path_query('data', '$.name') -> "data" @? '$.name'
            json_path_query('data', '$.name', 'has_name') -> "data" @? '$.name' AS "has_name"
        """
        field_expr = self.field(field) if not isinstance(field, str) or "." in field else self._quote_field.format(field=field)
        
        if not path.startswith("'"):
            path = f"'{path}'"
            
        expr = f"{field_expr}::jsonb @? {path}"
        
        if alias:
            return self._as.join([expr, self._quote_field.format(field=alias)])
        return expr


class Sqlite3SqlDialect(SqlDialect):
    def __init__(self):
        super(Sqlite3SqlDialect, self).__init__()
        self.placeholder = "?"
        self.insert_returning = True  # since 3.35.0
        self.ilike = False
