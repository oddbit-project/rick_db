import pytest

from rick_db.conn.pg import PgConnection
from tests.config import connectSimple


class PgCommon:
    createTable = "create table if not exists animals(legs serial not null primary key, name varchar);"
    createSchema = "create schema myschema;"
    createSchemaTable = "create table if not exists myschema.aliens(legs serial not null primary key, name varchar);"
    createView = "create view list_animals as select * from animals;"
    createSchemaView = (
        "create view myschema.list_aliens as select * from myschema.aliens;"
    )
    createGroup = "create group staff;"
    addGroup = "alter group staff add user {user}"
    dropGroup = "drop group staff"

    @pytest.fixture()
    def conn(self) -> PgConnection:
        conn = connectSimple()
        self.cleanup(conn)
        return conn

    def cleanup(self, conn):
        md = conn.metadata()
        with conn.cursor():
            md.drop_table("_migration")
            md.drop_view("list_animals")
            md.drop_table("animals")
            md.drop_schema("myschema", True)
