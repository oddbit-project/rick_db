from typing import Any, Optional

from rick_db.repository import Repository, RepositoryError
from rick_db.mapper import ATTR_PRIMARY_KEY
from rick_db.sql import Insert
from .sql import ClickHouseUpdate, ClickHouseDelete


class ClickHouseRepository(Repository):
    """
    ClickHouse-specific Repository.

    Overrides update/delete operations to use ALTER TABLE mutations,
    and insert_pk to return None (ClickHouse has no RETURNING or lastrowid).
    """

    def insert_pk(self, record) -> Any:
        """
        Insert a record. Returns None since ClickHouse has no RETURNING
        or auto-increment primary keys.

        :param record: record object to insert
        :return: None
        """
        pk = self.pk
        if pk is None:
            pk = getattr(record, ATTR_PRIMARY_KEY, None)

        if pk is None:
            raise RepositoryError("insert_pk(): record has no primary key")

        sql, values = Insert(self.dialect).into(record).assemble()
        with self.cursor() as c:
            c.exec(sql, values)
        return None

    def delete_pk(self, pk_value):
        """
        Delete a record by primary key using ALTER TABLE ... DELETE WHERE.

        :param pk_value: primary key value
        :return: None
        """
        if self.pk is None:
            raise RepositoryError("delete_pk(): record has no primary key")

        sql = self.query_cache.get("delete_pk")
        if sql is None:
            sql, values = (
                ClickHouseDelete(self.dialect)
                .from_(self._record)
                .where(self.pk, "=", pk_value)
                .assemble()
            )
            self.query_cache.set("delete_pk", sql)
        else:
            values = [pk_value]
        with self.cursor() as c:
            c.exec(sql, values)

    def delete_where(self, where_clauses: list):
        """
        Delete rows matching WHERE clauses using ALTER TABLE ... DELETE WHERE.

        :param where_clauses: list of (field, operator, value) tuples
        """
        qry = ClickHouseDelete(self.dialect).from_(self._record)

        if len(where_clauses) == 0:
            raise RepositoryError("delete_where(): where_clauses is empty")

        for clause in where_clauses:
            if len(clause) != 3:
                raise RepositoryError("delete_where(): invalid length for where clause")
            qry.where(clause[0], clause[1], clause[2])

        qry, values = qry.assemble()
        with self.cursor() as c:
            c.exec(qry, values)

    def update(self, record, pk_value=None):
        """
        Update a record using ALTER TABLE ... UPDATE ... WHERE.

        :param record: record object
        :param pk_value: optional primary key value
        """
        if self.pk is None:
            raise RepositoryError("update(): missing primary key")
        data = record.asrecord()

        value = pk_value
        if self.pk in data:
            value = data[self.pk]
            del data[self.pk]

        if value is None:
            raise RepositoryError("update(): missing primary key value")
        sql, values = (
            ClickHouseUpdate(self.dialect)
            .table(self.table_name, self.schema)
            .values(data)
            .where(self.pk, "=", value)
            .assemble()
        )
        with self.cursor() as c:
            c.exec(sql, values)

    def update_where(self, record, where_list: list):
        """
        Update a record with custom WHERE conditions using ALTER TABLE ... UPDATE.

        :param record: record to update
        :param where_list: list of where conditions
        """
        if not isinstance(where_list, (list, tuple)):
            raise RepositoryError("update_where(): invalid type for where clause list")
        if len(where_list) == 0:
            raise RepositoryError("update_where(): where clause list cannot be empty")

        qry = ClickHouseUpdate(self.dialect).table(self.table_name, self.schema).values(record)
        for cond in where_list:
            if not isinstance(cond, (list, tuple)):
                raise RepositoryError(
                    "update_where(): invalid item in where clause list"
                )
            lc = len(cond)
            if lc == 2:
                qry.where(cond[0], operator="=", value=cond[1])
            elif lc == 3:
                qry.where(cond[0], operator=cond[1], value=cond[2])
            else:
                raise RepositoryError(
                    "update_where(): invalid item in where clause list"
                )

        sql, values = qry.assemble()
        with self.cursor() as c:
            c.exec(sql, values)
