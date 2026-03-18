class SqlError(Exception):
    pass


class Literal:
    """
    Representation class for literal expressions

    """

    def __init__(self, literal):
        self._literal = literal

    def __str__(self):
        return self._literal


# because Literal is also a typing keyword
class L(Literal):
    pass


class JsonField:
    """
    Specialized class for working with JSON/JSONB fields.

    This class provides a convenient way to work with JSON fields in SQL
    queries, supporting operations like extracting values and checking
    for the existence of paths.
    """

    def __init__(self, field_name, dialect=None):
        """
        Initialize a JsonField

        :param field_name: The name of the JSON field
        :param dialect: Optional SQL dialect to use for JSON operations
        """
        self.field_name = field_name
        self.dialect = dialect

    def extract(self, path, alias=None):
        """
        Extract a value from the JSON field

        :param path: JSON path to extract
        :param alias: Optional alias for the result
        :return: Literal SQL expression
        """
        if self.dialect and self.dialect.json_support:
            expr = self.dialect.json_extract(self.field_name, path, alias)
            return Literal(expr)
        return Literal(f"JSON_EXTRACT({self.field_name}, '{path}')")

    def extract_text(self, path, alias=None):
        """
        Extract a value as text from the JSON field

        :param path: JSON path to extract
        :param alias: Optional alias for the result
        :return: Literal SQL expression
        """
        if self.dialect and self.dialect.json_support:
            expr = self.dialect.json_extract_text(self.field_name, path, alias)
            return Literal(expr)
        return Literal(f"JSON_EXTRACT({self.field_name}, '{path}')")

    def contains(self, value):
        """
        Check if the JSON field contains a value.

        The generated SQL uses a parameter placeholder for the value.
        The value argument is not interpolated into the SQL string;
        it should be passed separately to the query executor for parameter binding.

        :param value: Value to check for (used for parameter binding, not interpolated into SQL)
        :return: Literal SQL expression
        """
        if self.dialect and self.dialect.json_support:
            expr = self.dialect.json_contains(self.field_name, value)
            return Literal(expr)
        return Literal(f"JSON_CONTAINS({self.field_name}, ?)")

    def has_path(self, path):
        """
        Check if a path exists in the JSON field

        :param path: Path to check
        :return: Literal SQL expression
        """
        if self.dialect and self.dialect.json_support:
            expr = self.dialect.json_contains_path(self.field_name, path)
            return Literal(expr)
        return Literal(f"JSON_CONTAINS_PATH({self.field_name}, 'one', '{path}')")

    def __str__(self):
        return self.field_name

    # Support for -> operator overloading for easier path access
    def __getitem__(self, key):
        """
        Allow dictionary-style access to JSON fields using square brackets.

        Example:
            json_field = JsonField('data')
            json_field['name']  # Returns the expression to extract the 'name' field
        """
        # Create a new JsonField with modified field name to represent the JSON path
        field_path = f'{self.field_name}->>"{key}"'
        result = JsonField(field_path, self.dialect)
        return result


class PgJsonField(JsonField):
    """
    PostgreSQL-specific JSON field implementation with extended functionality.
    """

    def __init__(self, field_name, dialect=None, is_jsonb=True):
        """
        Initialize a PostgreSQL JsonField

        :param field_name: The name of the JSON field
        :param dialect: Optional SQL dialect to use
        :param is_jsonb: Whether the field is JSONB (True) or JSON (False)
        """
        super().__init__(field_name, dialect)
        self.is_jsonb = is_jsonb

    def extract_object(self, path, alias=None):
        """
        Extract a JSON object using the -> operator

        :param path: JSON path to extract
        :param alias: Optional alias for the result
        :return: Literal SQL expression
        """
        if self.dialect and hasattr(self.dialect, "json_extract_object"):
            expr = self.dialect.json_extract_object(self.field_name, path, alias)
            return Literal(expr)
        return self.extract(path, alias)

    def path_query(self, path, alias=None):
        """
        PostgreSQL specific jsonpath query (for PostgreSQL 12+)

        :param path: jsonpath expression
        :param alias: Optional alias for the result
        :return: Literal SQL expression
        """
        if self.dialect and hasattr(self.dialect, "json_path_query"):
            expr = self.dialect.json_path_query(self.field_name, path, alias)
            return Literal(expr)
        return self.has_path(path)

    def as_jsonb(self):
        """
        Cast field to JSONB type

        :return: This instance with JSONB type set to True
        """
        self.is_jsonb = True
        return self

    def as_json(self):
        """
        Cast field to JSON type

        :return: This instance with JSONB type set to False
        """
        self.is_jsonb = False
        return self

    def __getitem__(self, key):
        """
        Allow dictionary-style access to JSON fields using PostgreSQL arrow operators.

        Example:
            json_field = PgJsonField('data')
            json_field['name']  # Returns an object representing data->"name"
        """
        # For PostgreSQL we use -> which preserves the JSON type
        field_path = f'{self.field_name}->"{key}"'
        result = PgJsonField(field_path, self.dialect, self.is_jsonb)
        return result

    def __str__(self):
        """
        String representation of the field with appropriate type cast
        """
        if self.is_jsonb:
            return f"{self.field_name}::jsonb"
        return f"{self.field_name}::json"


class Fn:
    """
    SQL function helpers that return Literal instances.

    Use with dict-style column definitions for aliasing:
        Select(dialect).from_(User, {Fn.count("*"): "total"})
        Select(dialect).from_(User, {User.name: None, Fn.sum("amount"): "total_amount"})
    """

    # Aggregate functions
    @staticmethod
    def count(field="*"):
        return Literal("COUNT({})".format(field))

    @staticmethod
    def sum(field):
        return Literal("SUM({})".format(field))

    @staticmethod
    def avg(field):
        return Literal("AVG({})".format(field))

    @staticmethod
    def min(field):
        return Literal("MIN({})".format(field))

    @staticmethod
    def max(field):
        return Literal("MAX({})".format(field))

    # Math functions
    @staticmethod
    def abs(field):
        return Literal("ABS({})".format(field))

    @staticmethod
    def ceil(field):
        return Literal("CEIL({})".format(field))

    @staticmethod
    def floor(field):
        return Literal("FLOOR({})".format(field))

    @staticmethod
    def round(field, decimals=None):
        if decimals is not None:
            return Literal("ROUND({}, {})".format(field, int(decimals)))
        return Literal("ROUND({})".format(field))

    @staticmethod
    def power(field, exponent):
        return Literal("POWER({}, {})".format(field, exponent))

    @staticmethod
    def sqrt(field):
        return Literal("SQRT({})".format(field))

    @staticmethod
    def mod(field, divisor):
        return Literal("MOD({}, {})".format(field, divisor))

    @staticmethod
    def sign(field):
        return Literal("SIGN({})".format(field))

    @staticmethod
    def trunc(field, decimals=None):
        if decimals is not None:
            return Literal("TRUNC({}, {})".format(field, int(decimals)))
        return Literal("TRUNC({})".format(field))

    # General functions
    @staticmethod
    def coalesce(*fields):
        return Literal("COALESCE({})".format(", ".join(str(f) for f in fields)))

    @staticmethod
    def cast(field, type_name):
        return Literal("CAST({} AS {})".format(field, type_name))


class Sql:
    DISTINCT = "distinct"
    COLUMNS = "columns"
    FROM = "from"
    LATERAL = "lateral"
    UNION = "union"
    WHERE = "where"
    GROUP = "group"
    HAVING = "having"
    ORDER = "order"
    LIMIT_OFFSET = "limitoffset"
    FOR_UPDATE = "forupdate"
    ANONYMOUS = "_"

    JOIN = "JOIN"
    INNER_JOIN = "INNER JOIN"
    LEFT_JOIN = "LEFT JOIN"
    RIGHT_JOIN = "RIGHT JOIN"
    FULL_JOIN = "FULL JOIN"
    CROSS_JOIN = "CROSS JOIN"
    NATURAL_JOIN = "NATURAL JOIN"
    INNER_JOIN_LATERAL = "INNER JOIN LATERAL"
    LEFT_JOIN_LATERAL = "LEFT JOIN LATERAL"
    SQL_LATERAL = "LATERAL"

    SQL_WILDCARD = "*"
    SQL_SELECT = "SELECT"
    SQL_UNION = "UNION"
    SQL_UNION_ALL = "UNION ALL"
    SQL_FROM = "FROM"
    SQL_WHERE = "WHERE"
    SQL_DISTINCT = "DISTINCT"
    SQL_GROUP_BY = "GROUP BY"
    SQL_ORDER_BY = "ORDER BY"
    SQL_HAVING = "HAVING"
    SQL_FOR_UPDATE = "FOR UPDATE"
    SQL_AND = "AND"
    SQL_AS = "AS"
    SQL_OR = "OR"
    SQL_ON = "ON"
    SQL_ASC = "ASC"
    SQL_DESC = "DESC"
    SQL_OFFSET = "OFFSET"
    SQL_LIMIT = "LIMIT"
    SQL_INSERT = "INSERT INTO"
    SQL_VALUES = "VALUES"
    SQL_RETURNING = "RETURNING"
    SQL_LIST_DELIMITER_LEFT = "("
    SQL_LIST_DELIMITER_RIGHT = ")"
    SQL_ALL = "ALL"
    SQL_DELETE = "DELETE FROM"
    SQL_CASCADE = "CASCADE"
    SQL_UPDATE = "UPDATE"
    SQL_SET = "SET"
    SQL_WITH = "WITH"
    SQL_NOT_MATERIALIZED = "NOT MATERIALIZED"
    SQL_RECURSIVE = "RECURSIVE"


class SqlStatement:
    def assemble(self) -> tuple:
        pass
