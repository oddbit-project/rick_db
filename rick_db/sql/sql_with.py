from rick_db.sql import (
    SqlDialect,
    DefaultSqlDialect,
    SqlStatement,
    Sql,
)


class With(SqlStatement):

    def __init__(self, dialect: SqlDialect = None):
        """
        WITH constructor
        """
        self._clauses = []  # each clause is (name, with_query, [columns], materialized)
        self._query = None

        if dialect is None:
            dialect = DefaultSqlDialect()
        self._dialect = dialect

    def clause(self, name: str, with_query: SqlStatement, columns: list = None, materialized: bool = True):
        """
        Adds a WITH <clause>(columns) AS <with_query>
        :param name:
        :param with_query:
        :param columns:
        :param materialized:
        :return:
        """
        if columns is None:
            columns = []
        self._clauses.append((name, with_query, columns, materialized))
        return self

    def query(self, query: SqlStatement):
        """
        CTE query
        :param query:
        :return:
        """
        self._query = query
        return self

    def assemble(self) -> tuple:
        if not isinstance(self._query, SqlStatement):
            raise RuntimeError("assemble(): missing CTE query")
        if len(self._clauses) == 0:
            raise RuntimeError("assemble(): missing CTE clauses")

        parts = [Sql.SQL_WITH]
        values = []

        with_clauses = []
        for clause in self._clauses:
            name, qry, cols, materialized = clause

            chunks = []
            # optional expression columns
            if len(cols) > 0:
                fields = []
                for field in cols:
                    fields.append(self._dialect.field(field))
                chunks.append(self._dialect.table(name) + "(" + ",".join(fields) + ")")
            else:
                chunks.append(self._dialect.table(name))

            chunks.append(Sql.SQL_AS)
            if not materialized:
                chunks.append(Sql.SQL_NOT_MATERIALIZED)

            qry_sql, qry_values = qry.assemble()
            values.extend(qry_values)

            stmt = "{} ({})".format(" ".join(chunks), qry_sql)
            with_clauses.append(stmt)

        parts.append(",".join(with_clauses))
        qry_sql, qry_values = self._query.assemble()
        values.extend(qry_values)
        parts.append(qry_sql)

        return " ".join(parts).strip(), values
