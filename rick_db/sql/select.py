# SQL Query Builder
#
# Notes:
# The Select() implementation is heavily inspired from the Zend_Db_Select approach. You can check the
# Zend_Db_Select code and licensing at https://github.com/zendframework/zf1/blob/master/library/Zend/Db/Select.php

import collections

from .common import SqlStatement, Sql, Literal, SqlError
from .dialect import SqlDialect, DefaultSqlDialect
from ..mapper import ATTR_TABLE, ATTR_SCHEMA


class Select(SqlStatement):
    """
    SELECT query builder
    """
    ORDER_DESC = Sql.SQL_DESC
    ORDER_ASC = Sql.SQL_ASC

    UNION = Sql.SQL_UNION
    UNION_ALL = Sql.SQL_UNION_ALL

    WHERE_AND = 1
    WHERE_OR = 2
    WHERE_CLOSE = 3

    # validation rules
    _valid_joins = [
        Sql.INNER_JOIN,
        Sql.LEFT_JOIN,
        Sql.RIGHT_JOIN,
        Sql.FULL_JOIN,
        Sql.CROSS_JOIN,
        Sql.NATURAL_JOIN,
    ]
    _valid_unions = [
        Sql.SQL_UNION,
        Sql.SQL_UNION_ALL
    ]
    _valid_order = [
        Sql.SQL_ASC,
        Sql.SQL_DESC
    ]

    def __init__(self, dialect: SqlDialect = None):
        """
        Constructor
        :param dialect: optional SqlDialect object; if omitted, DefaultSqlDialect is used
        """
        self._values = []
        self._query_values = {
            Sql.WHERE: [],
            Sql.HAVING: []
        }
        self._distinct = False
        self._for_update = False
        self._limit_offset = None

        # parts
        self._parts_union = []
        self._parts_from = {}
        self._parts_columns = {}
        self._parts_where = []
        self._parts_group = []
        self._parts_having = []
        self._parts_order = []

        self._where_blocks = 0

        # SQL dialect options
        if dialect is None:
            self._dialect = DefaultSqlDialect()
        else:
            if not isinstance(dialect, SqlDialect):
                raise RuntimeError("dialect must be a SqlDialect instance, not '{}'".format(type(dialect).__name__))
            self._dialect = dialect

    def distinct(self, flag=True):
        """
        Enables/disables DISTINCT

        Limitations:
            - Does not work with wildcard columns;
            - Dos not work with specific columns;

        :param flag: bool
        :return: self
        """

        self._distinct = flag
        return self

    def expr(self, cols=None):
        """
        Adds an anonymous expression to the select
        The purpose is to generate simple non-table related queries

        Limitations:
            - Placeholder values are not supported
            - Can be called only 1 time per query

        :param cols: columnar expression
        :return: self

        Possible values for cols:
            'string' -> string with contents
            ['list','of','strings'] -> list of string contents
            Literal('string') -> Literal with contents
            [Literal('string'),] -> list of Literal and/or strings with contents

        Example:
            .expr("1")                  # SELECT 1
            .expr(["1","2","3"])        # SELECT 1,2,3
            .expr({Literal("NEXTVAL('some_sequence_name')": "seq_next") # select NEXTVAL('some_sequence_name') AS "seq_next"
        """
        if not isinstance(cols, collections.abc.Mapping):
            if type(cols) in [list, tuple]:
                cols = dict((col, None) for col in cols)
            else:
                cols = {str(cols): None}

        columns = {}
        for field, alias in cols.items():
            if not isinstance(field, Literal):
                columns[Literal(str(field))] = alias
            else:
                columns[field] = alias

        self._add_columns(Sql.ANONYMOUS, columns, False)
        return self

    def from_(self, table, cols=None, schema=None):
        """
        Adds a FROM clause
        :param table: table name string, dict {name:alias}, or fieldmapper Record
        :param cols: columns to include
        :param schema: optional table schema
        :return: self

        Possible values for table:
            'table' -> string with table name
            {'table':'alias'} -> dict with table and alias
            {class_or_object:'alias'} -> dict with fieldmapper class with table and schema information, and table alias

        Possible values for cols:
            None -> "*" is assumed
            'field' -> string with field name
            {'field': 'alias'} -> dict with field name and alias
            {'field': None, 'other_field':'alias} -> dict with multiple field names and alias
            ['field', 'field',] -> list with field names
            [{'field': 'alias'}, 'field', ] -> list with dicts and strings

        Example:
            .from("foo")                        # SELECT "foo".* FROM "foo"
            .from("foo", None, "public")        # SELECT "foo".* FROM "public"."foo"
            .from({"foo":"bar"})                # SELECT "bar".* FROM "foo" AS "bar"
            .from("foo", {"field1":None, "field2":"alias"})     # SELECT "field1","field2" AS "alias" FROM "foo"

            .from("foo", "field")               # SELECT "field" FROM "foo"
            .from("foo", ["field1", "field2"])  # SELECT "field1", "field2" FROM "foo"
            .from({"foo": "bar"}, ["field1"])   # SELECT "bar.field1" FROM "foo" AS "bar"
            .from(class_or_object, ["field1"])           # SELECT "field1" FROM "<object_table_name>"
            .from({class_or_object: "bar"}, ["field1"])  # SELECT "bar"."field1" FROM "<object_table_name>" AS "bar"
        """
        if cols is None or (type(cols) in (list, tuple) and len(cols) == 0):
            cols = Sql.SQL_WILDCARD

        return self._join(Sql.FROM, table, None, None, None, None, cols, schema, None)

    def limit(self, limit: int, offset: int = None):
        """
        LIMIT clause
        :param limit: LIMIT value
        :param offset: OFFSET value
        :return: self

        Example:
            .limit(10)         # LIMIT 10
            .limit(10, 5)      # LIMIT 10 OFFSET 5
        """
        self._limit_offset = [limit, offset]
        return self

    def page(self, page: int, page_rows: int):
        """
        Helper for LIMIT page calculation

        :param page: page to show; first page is 1
        :param page_rows: rows per page
        :return: self

        Example:
            .page(1, 10)    # LIMIT 10 OFFSET 0
            .page(2, 10)    # LIMIT 10 OFFSET 10
        """
        page = int(page)
        page_rows = int(page_rows)
        if page < 1:
            raise SqlError("page(): page number must be >=1")
        if page_rows < 1:
            raise SqlError("page(): page_rows must be >=1")
        return self.limit(page_rows, page_rows * (page - 1))

    def for_update(self, flag: bool = True):
        """
        FOR UPDATE clause
        :param flag: if True, adds clause
        :return: self
        """
        self._for_update = flag
        return self

    def order(self, fields, order=Sql.SQL_ASC):
        """
        ORDER BY clause

        :param fields: fields to sort by
        :param order: either Select.ORDER_ASC or Select.ORDER_DESC
        :return: self

        Example:
            .order("id")                            # ORDER BY id ASC
            .order(["id", "a"], Select.ORDER_DESC)  # ORDER BY id DESC, a DESC
        """
        ftype = type(fields)
        if ftype not in (list, tuple, dict):
            fields = [fields]

        if order is not None:
            if order.upper() not in self._valid_order:
                raise SqlError("order(): invalid order direction: %s" % order)
        else:
            order = ""

        if ftype is dict:
            for v in fields.values():
                if v.upper() not in self._valid_order:
                    raise SqlError("order(): Invalid order direction: %s" % v)

        self._parts_order.append([fields, order])
        return self

    def where_and(self):
        """
        Starts a parenthesis AND block in the where clause
        :return: self
        """
        self._parts_where.append([self.WHERE_AND])
        self._where_blocks += 1
        return self

    def where_or(self):
        """
        Starts a parenthesis ORblock in the where clause
        :return: self
        """
        self._parts_where.append([self.WHERE_OR])
        self._where_blocks += 1
        return self

    def where_end(self):
        """
        Closes a parenthesis AND/OR block in the where clause
        :return: self
        """
        self._parts_where.append([self.WHERE_CLOSE])
        self._where_blocks -= 1
        return self

    def where(self, field, operator=None, value=None):
        """
        WHERE clause

        Multiple calls to this method are concatenated with AND

        :param field: field name, dict or Literal
        :param operator: optional operator
        :param value: optional value
        :return: self

        Possible values for field:
            'string' -> string field name
            Literal('string') -> literal expression
            {'table':'field'} -> dict with table and field
            {<class_or_object>:'field'} -> dict with class or object with table info, and field name

        Examples:
            .where('id', '>', 5)                      # WHERE ("id" > ?)
            .where('id', 'IS NULL')                   # WHERE ("id" IS NULL)
            .where({'table':'id'}, '>', 5)            # WHERE ("table"."id" > ?)
            .where(Literal("MAX(field1)", '>', 5)     # WHERE (MAX(field1) > ?)
            .where({<class_or_object>:"field"}, '=', 5)  # WHERE ("<object_table_name>"."field" = ?)
        """
        return self._where(field, operator, value)

    def orwhere(self, field, operator=None, value=None):
        """
        WHERE clause with OR concatenation
        See where() documentation

        :param field:  field name, dict or Literal
        :param operator: optional operator
        :param value: optional value
        :return: self
        """
        return self._where(field, operator, value, False)

    def group(self, fields):
        """
        GROUP BY clause

        :param fields: field name, field list or Literal
        :return: self

        Possible values for fields:
            'string' -> field name
            Literal('string') -> Literal expression
            ['string'] -> list of field names
            [Literal('string'),] -> list of Literal expressions or strings

        Example:
            .group('field')                     # GROUP BY "field"
            .group(Literal('SUM(field)'))       # GROUP BY SUM(field)
            .group(['field1', 'field2'])        # GROUP BY "field1", "field2"
        """
        if type(fields) not in [list, tuple]:
            fields = [fields]

        for field in fields:
            if isinstance(field, (str, Literal)):
                if field in self._parts_group:
                    raise SqlError(f"group(): duplicate field in group clause: {field}")
                self._parts_group.append(field)
            else:
                raise SqlError("group(): invalid field type: %s" % str(type(field)))
        return self

    def having(self, field, operator=None, value=None, schema=None):
        """
        HAVING clause

        :param field: field name, dict with table name and field, or Literal
        :param operator: optional operator
        :param value: optional value
        :param schema: optional schema name for table
        :return:self

        Possible values for field:
            'field' -> string with field name
            Literal('field') -> literal expression
            {'table':'field'} -> dict with table and field names
            {class_or_object:'field'} -> dict with fieldmapper class with table and schema information, and field name

        Examples:
            .having('field')                                    # HAVING ("field1")
            .having('field', '=', 5)                            # HAVING ("field1" = ?)
            .having({'some_table':'field'}, '>', 5, 'public')   # HAVING ("public"."some_table"."field" > ?)
            .having(Literal('COUNT(field) > 5'))                # HAVING (COUNT(field) > 5)
            .having(Literal('COUNT(field)'), '>', 5)            # HAVING (COUNT(field) > %s)
        """
        table = None

        if isinstance(field, collections.abc.Mapping):
            # field is actually a mapping table:field
            if len(field) != 1:
                raise SqlError("having(): field collection must have exactly 1 record")
            table, field = list(field.items()).pop()

        if table is not None:
            if not isinstance(table, str):
                if isinstance(table, object):
                    schema = getattr(table, ATTR_SCHEMA, schema)
                    table = getattr(table, ATTR_TABLE, None)
                    if table is None:
                        raise SqlError("having(): invalid _tablename attribute in class/object")
                else:
                    raise SqlError("having(): invalid table name type")

        if isinstance(field, str):
            field = self._dialect.field(field, None, table, schema)
        elif isinstance(field, Literal):
            field = str(field)
        else:
            raise SqlError("having(): invalid field name type")

        if value is None:
            if operator is None:
                expression = "{fld}".format(fld=field)
            else:
                expression = "{fld} {op}".format(fld=field, op=operator)
            self._parts_having.append(expression)
        else:
            if operator is None:
                expression = "{fld} {ph}".format(fld=field, ph=self._dialect.placeholder)
            else:
                expression = "{fld} {op} {ph}".format(fld=field, op=operator, ph=self._dialect.placeholder)
            self._parts_having.append(expression)
            self._query_values[Sql.HAVING].append(value)
        return self

    def union(self, queries: list, union_type: str = Sql.SQL_UNION):
        """
        UNION clause

        :param queries: list of Select() or string queries to Union
        :param union_type: type of union
        :return: self

        Examples:
            Select().union([Select().from_('table'), Select().from_('other_table')])  # SELECT "table".* FROM "table" UNION SELECT "other_table".* FROM "other_table"
        """
        if union_type not in self._valid_unions:
            raise SqlError("Invalid union type %s" % union_type)

        if isinstance(queries, (str, Select)):
            queries = [queries]

        for q in queries:
            self._parts_union.append([q, union_type])
        return self

    def join(self, table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None,
             expr_schema=None):
        """
        INNER JOIN

        :param table: table to join to
        :param field: expression or field for join
        :param expr_table: existing table to join to
        :param expr_field: join expression for existing table
        :param operator: optional join operator
        :param cols: optional columns to include in the SELECT statement
        :param schema: optional joined table schema
        :param expr_schema: optional existing table schema
        :return: self

        Possible table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible field values:
            'string' -> string with field name

        Possible expr_table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible expr_field values:
            'string' -> string with field name

        Examples:
            .join('table1', 'table1_id', 'table2', 'table2_id')
            .join({'table1':'t1'}, 'table1_id', {'table2':'t2'}, 'table2_id')
            .join(JoinToRecordObject, JoinToRecordObject.Field, JoinFromRecordObject, JoinFromRecordObject.Field)
        """
        return self.join_inner(table, field, expr_table, expr_field, operator, cols, schema, expr_schema)

    def join_inner(self, table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None,
                   expr_schema=None):
        """
        INNER JOIN

        :param table: table to join to
        :param field: expression or field for join
        :param expr_table: existing table to join to
        :param expr_field: join expression for existing table
        :param operator: optional join operator
        :param cols: optional columns to include in the SELECT statement
        :param schema: optional joined table schema
        :param expr_schema: optional existing table schema
        :return: self

        Possible table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible field values:
            'string' -> string with field name

        Possible expr_table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible expr_field values:
            'string' -> string with field name

        Examples:
            .join('table1', 'table1_id', 'table2', 'table2_id')
            .join({'table1':'t1'}, 'table1_id', {'table2':'t2'}, 'table2_id')
            .join(JoinToRecordObject, JoinToRecordObject.Field, JoinFromRecordObject, JoinFromRecordObject.Field)
        """
        return self._join(Sql.INNER_JOIN, table, field, expr_table, expr_field, operator, cols, schema,
                          expr_schema)

    def join_left(self, table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None,
                  expr_schema=None):
        """
        LEFT JOIN

        :param table: table to join to
        :param field: expression or field for join
        :param expr_table: existing table to join to
        :param expr_field: join expression for existing table
        :param operator: optional join operator
        :param cols: optional columns to include in the SELECT statement
        :param schema: optional joined table schema
        :param expr_schema: optional existing table schema
        :return: self

        Possible table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible field values:
            'string' -> string with field name

        Possible expr_table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible expr_field values:
            'string' -> string with field name

        Examples:
            .join_left('table1', 'table1_id', 'table2', 'table2_id')
            .join_left({'table1':'t1'}, 'table1_id', {'table2':'t2'}, 'table2_id')
            .join_left(JoinToRecordObject, JoinToRecordObject.Field, JoinFromRecordObject, JoinFromRecordObject.Field)
        """
        return self._join(Sql.LEFT_JOIN, table, field, expr_table, expr_field, operator, cols, schema, expr_schema)

    def join_right(self, table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None,
                   expr_schema=None):
        """
        RIGHT JOIN

        :param table: table to join to
        :param field: expression or field for join
        :param expr_table: existing table to join to
        :param expr_field: join expression for existing table
        :param operator: optional join operator
        :param cols: optional columns to include in the SELECT statement
        :param schema: optional joined table schema
        :param expr_schema: optional existing table schema
        :return: self

        Possible table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible field values:
            'string' -> string with field name

        Possible expr_table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible expr_field values:
            'string' -> string with field name

        Examples:
            .join_right('table1', 'table1_id', 'table2', 'table2_id')
            .join_right({'table1':'t1'}, 'table1_id', {'table2':'t2'}, 'table2_id')
            .join_right(JoinToRecordObject, JoinToRecordObject.Field, JoinFromRecordObject, JoinFromRecordObject.Field)
        """
        return self._join(Sql.RIGHT_JOIN, table, field, expr_table, expr_field, operator, cols, schema,
                          expr_schema)

    def join_full(self, table, field, expr_table=None, expr_field=None, operator=None, cols=None, schema=None,
                  expr_schema=None):
        """
        FULL OUTER JOIN

        :param table: table to join to
        :param field: expression or field for join
        :param expr_table: existing table to join to
        :param expr_field: join expression for existing table
        :param operator: optional join operator
        :param cols: optional columns to include in the SELECT statement
        :param schema: optional joined table schema
        :param expr_schema: optional existing table schema
        :return: self

        Possible table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible field values:
            'string' -> string with field name

        Possible expr_table values:
            'string' -> string with table name
            <class_or_object> -> class or object with table and optional schema information
            {'string':'alias'} -> dict with table name and alias
            {<class_or_object>:'alias'} -> dict with class or object table and alias

        Possible expr_field values:
            'string' -> string with field name

        Examples:
            .join_full('table1', 'table1_id', 'table2', 'table2_id')
            .join_full({'table1':'t1'}, 'table1_id', {'table2':'t2'}, 'table2_id')
            .join_full(JoinToRecordObject, JoinToRecordObject.Field, JoinFromRecordObject, JoinFromRecordObject.Field)
        """
        return self._join(Sql.FULL_JOIN, table, field, expr_table, expr_field, operator, cols, schema,
                          expr_schema)

    def join_cross(self, table, cols=None, schema=None):
        """
        Performs a CROSS JOIN
        See join() for more information

        :param table: table to perform join
        :param cols: columns to be selected from the joined table
        :param schema: optional schema for joined table
        :return: self

        Examples:
            .join_cross('table2')
            .join_cross({'table2':'alias'})
            .join_cross('table2', 'field1')
            .join_cross('table2', ['field1', 'field2'])
            .join_cross(JoinToRecordObject)
        """
        return self._join(Sql.CROSS_JOIN, table, None, None, None, None, cols, schema, None)

    def join_natural(self, table, cols=None, schema=None):
        """
        NATURAL INNER JOIN
        See join() for more information

        :param table: table to perform join
        :param cols: columns to be selected from the joined table
        :param schema: optional schema for joined table
        :return: self

        Examples:
            .join_natural('table2')
            .join_natural({'table2':'alias'})
            .join_natural('table2', 'field1')
            .join_natural('table2', ['field1', 'field2'])
            .join_natural(JoinToRecordObject)
        """
        return self._join(Sql.NATURAL_JOIN, table, None, None, None, None, cols, schema, None)

    def _where(self, field, operator=None, value=None, is_and=True, table=None):
        """
        Internal WHERE handler

        :param field: expression
        :param operator: clause operator
        :param value: optional value
        :param is_and: True to interleave with AND, False to OR
        :param table: optional table name
        :return: self
        """
        concat_with = Sql.SQL_AND
        if is_and is False:
            concat_with = Sql.SQL_OR

        if isinstance(field, collections.abc.Mapping):
            # field is actually a mapping table:field
            if len(field) != 1:
                raise SqlError("_where(): field collection must have exactly 1 record")
            table, field = list(field.items()).pop()

        if table is not None:
            if not isinstance(table, str):
                if isinstance(table, object):
                    table = getattr(table, ATTR_TABLE, None)
                    if table is None:
                        raise SqlError("_where(): invalid _tablename attribute in class/object")
                else:
                    raise SqlError("_where(): invalid table name type")

        if isinstance(field, str):
            field = self._dialect.field(field, None, table)
        elif isinstance(field, Literal):
            field = str(field)
        else:
            raise SqlError("_where(): invalid field name type")

        if value is None:
            if operator is None:
                expression = "{fld}".format(fld=field)
            else:
                expression = "{fld} {op}".format(fld=field, op=operator)
            self._parts_where.append([expression, concat_with])
        else:
            if operator is None:
                expression = "{fld} {ph}".format(fld=field, ph=self._dialect.placeholder)
            else:
                if isinstance(value, Select):
                    sql, value = value.assemble()
                    expression = "{fld} {op} ({query})".format(fld=field, op=operator, query=sql)
                    for v in value:
                        self._query_values[Sql.WHERE].append(v)
                    value = None
                elif isinstance(value, collections.abc.Mapping):
                    if len(value) != 1:
                        raise SqlError("_where(): value collection must have exactly 1 record")
                    tgt_tbl, tgt_field = list(value.items()).pop()
                    tmp_field_expr = self._dialect.field(tgt_field, None, tgt_tbl)
                    expression = "{fld} {op} {to_fld}".format(fld=field, op=operator, to_fld=tmp_field_expr)
                    value = None
                elif isinstance(value, Literal):
                    expression = "{fld} {op} {lit}".format(fld=field, op=operator, lit=str(value))
                    value = None
                else:
                    expression = "{fld} {op} {ph}".format(fld=field, op=operator, ph=self._dialect.placeholder)
            self._parts_where.append([expression, concat_with])
            if value is not None:
                self._query_values[Sql.WHERE].append(value)

        return self

    def _join(self, join_type, join_table, expr_or_field, from_table, from_field, operator, cols, schema, from_schema):
        """
        :param join_type: one of of self._valid_joins
        :param join_table: table name expression
        :param expr_or_field: field expression
        :param from_table: existing table
        :param from_field: existing table field
        :param operator: operator to use on join_table.expr_or_field <operator> from_table.from_field
        :param cols: columns to select from table schema
        :param schema: joined table schema
        :param from_schema: source table schema
        :return:
        """
        if join_type not in self._valid_joins and join_type != Sql.FROM:
            raise SqlError(f"_join(): invalid join type {join_type}")

        if len(self._parts_union) > 0:
            raise SqlError("_join(): invalid use of table with union")

        # join table
        join_table, alias, schema = self._parse_table_def(join_table, schema)
        if alias in self._parts_from.keys():
            raise SqlError("_join(): duplicate alias for table {tbl}")

        # join expression (if necessary)
        if from_table is None:
            # its a join(table,expression)
            if from_field is None and operator is None:
                expression = expr_or_field
            else:
                raise SqlError("_join(): missing expression field")
        else:
            # its a join (table, field, table, field, operator)
            expr_alias = None
            if isinstance(from_table, collections.abc.Mapping):
                # if dict, extract the first key:value pair
                if len(from_table) != 1:
                    raise SqlError("_join(): atmost one name:alias mapping per call is required")
                from_table, expr_alias = list(from_table.items()).pop()
                if not isinstance(expr_alias, str):
                    raise SqlError("_join(): invalid alias type")

            # if name is not string, attempt to parse from type
            if not isinstance(from_table, str):
                # expr_table must be either a Mapping, fieldmapper object or a string
                # as it references an already referenced table
                if isinstance(from_table, object):
                    from_schema = getattr(from_table, ATTR_SCHEMA, from_schema)
                    from_table = getattr(from_table, ATTR_TABLE, None)
                    if from_table is None:
                        raise SqlError("_join(): invalid _tablename attribute in class/object")
                else:
                    raise SqlError("_join(): invalid table type: %s" % str(type(from_table)))

            if expr_alias is None:
                expr_alias = from_table
            if expr_alias not in self._parts_from.keys():
                raise SqlError(f"_join(): table {expr_alias} not found")

            if operator is None:
                operator = "="
            # build expression
            if self._parts_from[expr_alias]['tableName'] != expr_alias:
                # if match is alias.field, ignore schema, as table is already aliased
                from_schema = None

            left_part = self._dialect.field(from_field, None, expr_alias, from_schema)
            expression = left_part + operator + self._dialect.field(expr_or_field, table=alias)

        self._parts_from[alias] = {
            'joinType': join_type,
            'tableName': join_table,
            'joinCondition': expression,
            'schema': schema,
        }

        # always alias wildcard tables
        has_alias = False
        if join_type == Sql.FROM:
            has_alias = (join_table != alias) or str(cols) == "*"
        else:
            # in joins, cols are always prefixed by alias
            if cols is not None:
                has_alias = True

        self._add_columns(alias, cols, has_alias)
        return self

    def _parse_table_def(self, table, schema):
        """
        Parse a table definition from a parameter

        :param table: one of: str, FieldMapper Object, Select, Literal
        :param schema: explicit schema name or None
        :return: (table:str, alias:str, schema:str)
        """
        alias = None
        # if dict, extract the first key:value pair
        if isinstance(table, collections.abc.Mapping):
            if len(table) != 1:
                raise SqlError("_join(): atmost one name:alias mapping per call is required")
            table, alias = list(table.items()).pop()
            if not isinstance(alias, str):
                raise SqlError("_join(): invalid alias type")

        # if name is not string, attempt to parse from type
        if not isinstance(table, str):

            # if select or Literal, convert to string
            if isinstance(table, (Literal, Select)):
                if alias is None:
                    alias = self._alias('t')

            # if object, try to access fieldmapper info
            elif isinstance(table, object):
                schema = getattr(table, ATTR_SCHEMA, schema)
                table = getattr(table, ATTR_TABLE, None)
                if table is None:
                    raise SqlError("_join(): invalid _tablename attribute in class/object")

            # if other type, abort
            else:
                raise SqlError("_join(): invalid table type: %s" % str(type(table)))

        # name cannot be empty
        if not table:
            raise SqlError("_join(): empty name")

        # if alias is still missing, build one
        if alias is None:
            alias = self._alias(table)

        return table, alias, schema

    def _alias(self, name):
        """
        Generate an internal table alias that is not in use yet
        :param name:
        :return: string
        """
        i = 2
        alias = name
        while alias in self._parts_from.keys():
            alias = "_".join([name, str(i)])
            i += 1
        return alias

    def _add_columns(self, table_name, columns, alias=False):
        """
        Add columns to select
        :param table_name: str
        :param columns: str, Literal, list, dict
        :param alias: str, table alias
        :return: self
        """
        if table_name in self._parts_columns.keys():
            if table_name == Sql.ANONYMOUS:
                raise SqlError("Columns for anonymous expression table already exist")
            raise SqlError("Columns for table %s already exist" % table_name)

        self._parts_columns[table_name] = (columns, alias)
        return self

    def _render_columns(self):
        """
        Render select columns
        :return: string
        """
        cols = []
        for tbl_alias, details in self._parts_columns.items():
            fields, alias = details
            if fields is None:
                continue

            if isinstance(fields, (str, Literal)):
                fields = [str(fields)]
            elif isinstance(fields, collections.abc.Mapping):
                fields = [fields]
            elif not isinstance(fields, (list, tuple)):
                raise SqlError("Invalid column type: %s" % str(type(fields)))

            if alias is True and tbl_alias != Sql.ANONYMOUS:  # masks anonymous expressions
                alias = tbl_alias
            else:
                alias = None

            if len(fields) == 0:
                raise SqlError("missing columns")

            for f in fields:
                if isinstance(f, collections.abc.Mapping):
                    for field, field_alias in f.items():
                        if isinstance(field, (str, Literal)):
                            cols.append(self._dialect.field(field, field_alias, alias))
                        else:
                            raise SqlError("Invalid column type: %s" % str(type(field)))

                elif isinstance(f, (str, Literal)):
                    cols.append(self._dialect.field(f, None, alias))
                else:
                    raise SqlError("Invalid column type: %s" % str(type(f)))
        return ",".join(cols)

    def _render_from(self):
        """
        Renders FROM and JOIN clauses
        :return: string
        """
        parts = [Sql.SQL_FROM]
        from_parts = {}
        join_parts = {}
        for alias, details in self._parts_from.items():
            if details['joinType'] == Sql.FROM:
                from_parts[alias] = details
            else:
                join_parts[alias] = details

        # FROM clause
        names = []
        for alias, details in from_parts.items():
            tbl_alias = None
            if alias != details['tableName']:
                tbl_alias = alias
            names.append(self._dialect.table(details['tableName'], tbl_alias, details['schema']))
        parts.append(", ".join(names))

        # JOIN clauses
        names = []
        for alias, details in join_parts.items():
            stmt = []
            tbl_alias = None
            stmt.append(details['joinType'])
            if alias != details['tableName']:
                tbl_alias = alias
            stmt.append(self._dialect.table(details['tableName'], tbl_alias, details['schema']))

            if details['joinCondition'] is not None:
                stmt.append(Sql.SQL_ON)
                stmt.append(details['joinCondition'])
            names.append(" ".join(stmt))  # complete join statement
        if len(names) > 0:
            parts.append(" ".join(names))  # combine all join statements

        return " ".join(parts)

    def _render_limitoffset(self):
        """
        Render LIMIT OFFSET clause
        :return: string
        """
        limit, offset = self._limit_offset
        if limit is None and offset is None:
            return ""

        parts = [Sql.SQL_LIMIT]
        if int(limit) < 0:
            parts.append(Sql.SQL_ALL)
        else:
            parts.append(str(limit))

        if offset is not None:
            parts.append(Sql.SQL_OFFSET)
            parts.append(str(offset))

        return " ".join(parts)

    def _render_union(self):
        """
        Render UNION clause
        :return: string
        """
        parts = []
        count = len(self._parts_union)
        for item in self._parts_union:
            query, qtype = item
            if isinstance(query, Select):
                sql, values = query.assemble()
                self._values.extend(values)
            elif isinstance(query, str):
                sql = query
            elif isinstance(query, Literal):
                sql = str(query)
            else:
                raise SqlError("union(): invalid type for UNION query")
            parts.append(sql)
            count -= 1
            if count > 0:
                parts.append(qtype)

        return " ".join(parts)

    def _render_order(self):
        """
        Renders ORDER BY clause
        :return: string
        """
        if len(self._parts_order) == 0:
            return ""

        parts = []
        for row in self._parts_order:
            expr, order = row
            stmt = []
            if isinstance(expr, collections.abc.Mapping):
                for field, _order in expr.items():
                    stmt.append(self._dialect.field(field))
                    if _order is None:
                        stmt.append(order)
                    else:
                        stmt.append(_order)
            elif isinstance(expr, (list, tuple)):
                for field in expr:
                    stmt.append(self._dialect.field(field))
                    stmt.append(order)
            elif isinstance(expr, Literal):
                stmt.append(str(expr))
                stmt.append(order)
            elif isinstance(expr, str):
                stmt.append(self._dialect.field(expr))
                stmt.append(order)
            else:
                raise SqlError("order(): invalid field type: %s" % str(type(expr)))
            parts.append(" ".join(stmt))

        return " ".join([Sql.SQL_ORDER_BY, ",".join(parts)])

    def _render_where(self):
        """
        Renders WHERE clause

        Will fill self._values

        :return: string
        """
        clauses = self._parts_where
        parts = [Sql.SQL_WHERE]
        i = 0
        for row in clauses:
            if len(row) == 1:
                # if len == 1, it is a marker token
                token = row[0]
                if token == self.WHERE_CLOSE:
                    parts.append(Sql.SQL_LIST_DELIMITER_RIGHT)
                else:
                    if token == self.WHERE_AND:
                        statement = Sql.SQL_AND
                    else:
                        statement = Sql.SQL_OR
                    if i > 0:
                        parts.append(statement)
                    parts.append(Sql.SQL_LIST_DELIMITER_LEFT)
                    i = 0
            else:
                expr, glue = row
                if i > 0:
                    parts.append(glue)
                parts.append(Sql.SQL_LIST_DELIMITER_LEFT + expr + Sql.SQL_LIST_DELIMITER_RIGHT)
                i += 1

        # copy values so they match the rendering sequence
        for v in self._query_values[Sql.WHERE]:
            self._values.append(v)

        return " ".join(parts)

    def _render_group(self):
        """
        Renders GROUP BY clause
        :return: string
        """
        parts = []
        for f in self._parts_group:
            parts.append(self._dialect.field(f))

        if len(parts) == 0:
            return ""
        return " ".join([Sql.SQL_GROUP_BY, ", ".join(parts)])

    def _render_having(self):
        """
        Renders HAVING clause
        :return: string
        """
        having = self._parts_having
        if len(having) == 0:
            return ""

        parts = []
        for row in having:
            clause = Sql.SQL_LIST_DELIMITER_LEFT + str(row) + Sql.SQL_LIST_DELIMITER_RIGHT
            parts.append(clause)

        for v in self._query_values[Sql.HAVING]:
            self._values.append(v)

        glue = " " + Sql.SQL_AND + " "
        return " ".join([Sql.SQL_HAVING, glue.join(parts)])

    def assemble(self):
        """
        Retrieve assembled query and binded values
        :return: tuple(str, list)
        """
        self._values = []
        parts = []
        # union queries don't have select clause
        union_len = len(self._parts_union)
        if union_len == 0:
            parts.append(Sql.SQL_SELECT)

        if self._distinct is True:
            parts.append(Sql.SQL_DISTINCT)

        if len(self._parts_columns) > 0:
            parts.append(self._render_columns())

        if union_len > 0:
            parts.append(self._render_union())

        if len(self._parts_from) > 0:
            parts.append(self._render_from())

        if len(self._parts_where) > 0:
            if self._where_blocks != 0:
                raise RuntimeError("assemble(): where block count mismatch; did you forget to close a AND/OR block?")
            parts.append(self._render_where())

        if len(self._parts_group) > 0:
            parts.append(self._render_group())

        if len(self._parts_having) > 0:
            parts.append(self._render_having())

        if len(self._parts_order) > 0:
            parts.append(self._render_order())

        if self._limit_offset is not None:
            parts.append(self._render_limitoffset())

        if self._for_update is True:
            parts.append(Sql.SQL_FOR_UPDATE)

        # convert Literal() to str in values
        for k, v in enumerate(self._values):
            if isinstance(v, Literal):
                self._values[k] = str(v)

        return " ".join(parts).strip(), self._values

    def dialect(self) -> SqlDialect:
        """
        Retrieve current dialect
        :return: SqlDialect
        """
        return self._dialect
