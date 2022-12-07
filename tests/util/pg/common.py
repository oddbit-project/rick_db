import pytest

from rick_db.conn.pg import PgConnection
from tests.config import connectSimple


class PgCommon:
    dropMigrations = "drop table if exists _migration;"
    createTable = "create table if not exists animals(legs serial not null primary key, name varchar);"
    dropTable = "drop table if exists animals;"
    createSchema = "create schema myschema;"
    dropSchema = "drop schema if exists myschema;"
    createSchemaTable = "create table if not exists myschema.aliens(legs serial not null primary key, name varchar);"
    dropSchemaTable = "drop table if exists myschema.aliens;"
    createView = "create view list_animals as select * from animals;"
    dropView = "drop view if exists list_animals;"
    createSchemaView = (
        "create view myschema.list_aliens as select * from myschema.aliens;"
    )
    dropSchemaView = "drop view if exists myschema.list_aliens;"
    createGroup = "create group staff;"
    addGroup = "alter group staff add user {user}"
    dropGroup = "drop group staff"

    @pytest.fixture()
    def conn(self) -> PgConnection:
        conn = connectSimple()
        self.cleanup(conn)
        return conn

    def cleanup(self, conn):
        with conn.cursor() as c:
            c.exec(self.dropMigrations)
            c.exec(self.dropView)
            c.exec(self.dropTable)
            c.exec(self.dropSchemaView)
            c.exec(self.dropSchemaTable)
            c.exec(self.dropSchema)
