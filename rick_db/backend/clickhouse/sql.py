from rick_db.mapper import ATTR_TABLE, ATTR_SCHEMA
from rick_db.sql import (
    SqlStatement,
    SqlDialect,
    SqlError,
    Sql,
    Literal,
    DefaultSqlDialect,
    Select,
    ClickHouseSqlDialect,
)
from rick_db.sql.update import Update
from rick_db.sql.delete import Delete


class ClickHouseUpdate(Update):
    """
    ClickHouse UPDATE builder.

    Generates ALTER TABLE ... UPDATE syntax instead of standard UPDATE ... SET.
    ClickHouse does not support standard SQL UPDATE; mutations must use
    ALTER TABLE ... UPDATE ... WHERE ...
    """

    def assemble(self):
        """
        Assemble the ALTER TABLE ... UPDATE statement
        :return: tuple(str, list)
        """
        lf = len(self._fields)
        if lf == 0:
            raise SqlError("assemble(): field list is empty")
        if lf != len(self._values):
            raise SqlError("assemble(): field and value count mismatch")

        parts = [
            "ALTER TABLE",
            self._dialect.table(self._table, None, schema=self._schema),
            Sql.SQL_UPDATE,
        ]

        # generate field=value assignments
        fields = []
        values = []
        expression = "{}={}"
        for i in range(0, lf):
            name = self._dialect.field(self._fields[i])
            value = self._values[i]
            if isinstance(value, Literal):
                fields.append(expression.format(name, str(value)))
            elif isinstance(value, Select):
                value, sql_values = value.assemble()
                values.extend(sql_values)
                fields.append(expression.format(name, value))
            else:
                fields.append(expression.format(name, self._dialect.placeholder))
                values.append(value)

        parts.append(", ".join(fields))

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


class ClickHouseDelete(Delete):
    """
    ClickHouse DELETE builder.

    Generates ALTER TABLE ... DELETE WHERE syntax instead of standard
    DELETE FROM ... WHERE. ClickHouse does not support standard SQL DELETE;
    mutations must use ALTER TABLE ... DELETE WHERE ...
    """

    def assemble(self):
        """
        Assemble the ALTER TABLE ... DELETE statement
        :return: tuple(str, list)
        """
        parts = [
            "ALTER TABLE",
            self._dialect.table(self._table, None, self._schema),
            "DELETE",
        ]

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
