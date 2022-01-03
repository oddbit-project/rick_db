import pytest

from rick_db.conn import Connection
from rick_db.conn.sqlite import Sqlite3Connection
from rick_db.util.sqlite import Sqlite3Metadata


class TestSqlite3Metadata:
    createTable = "create table animals(legs integer primary key autoincrement, name varchar);"
    createIndex = "create index idx01 on animals(legs)"
    dropTable = "drop table if exists animals"
    createView = "create view list_animals as select * from animals"
    dropView = "drop view list_animals"

    @pytest.fixture()
    def conn(self) -> Connection:
        return Sqlite3Connection(":memory:")

    def test_tables(self, conn):
        meta = Sqlite3Metadata(conn)
        # no tables created yet
        tables = meta.tables()
        assert len(tables) == 0
        assert meta.table_exists('animals') is False

        # create one table
        with conn.cursor() as qry:
            qry.exec(self.createTable)

        tables = meta.tables()
        assert len(tables) == 1
        assert tables[0] == 'animals'
        assert meta.table_exists('animals') is True

        # cleanup
        with conn.cursor() as c:
            c.exec(self.dropTable)

    def test_schemas(self, conn):
        meta = Sqlite3Metadata(conn)
        schemas = meta.schemas()
        assert len(schemas) == 0

    def test_databases(self, conn):
        meta = Sqlite3Metadata(conn)
        dbs = meta.databases()
        assert len(dbs) == 0

    def test_views(self, conn):
        meta = Sqlite3Metadata(conn)
        # no views created yet
        views = meta.views()
        assert len(views) == 0
        assert meta.view_exists('list_animals') is False

        # create one table
        with conn.cursor() as qry:
            qry.exec(self.createTable)
            qry.exec(self.createView)

        views = meta.views()
        assert len(views) == 1
        assert views[0] == 'list_animals'
        assert meta.view_exists('list_animals') is True

        # cleanup
        with conn.cursor() as qry:
            qry.exec(self.dropView)
            qry.exec(self.dropTable)

    def test_table_fields(self, conn):
        meta = Sqlite3Metadata(conn)
        with conn.cursor() as qry:
            qry.exec(self.createTable)
            qry.exec(self.createView)

        # test table fields
        fields = meta.table_fields('animals')
        assert len(fields) == 2
        field1, field2 = fields
        assert field1.field == 'legs'
        assert field1.primary is True
        assert field2.field == 'name'
        assert field2.primary is False

        # test view fields
        fields = meta.view_fields('list_animals')
        assert len(fields) == 2
        field1, field2 = fields
        assert field1.field == 'legs'
        assert field1.primary is False  # views don't have keys
        assert field2.field == 'name'
        assert field2.primary is False

        with conn.cursor() as qry:
            qry.exec(self.dropView)
            qry.exec(self.dropTable)

    def test_table_keys(self, conn):
        meta = Sqlite3Metadata(conn)
        # create one table
        with conn.cursor() as qry:
            qry.exec(self.createTable)
            qry.exec(self.createIndex)

        # create table
        tables = meta.tables()
        assert len(tables) == 1
        assert tables[0] == 'animals'
        assert meta.table_exists('animals') is True

        keys = meta.table_indexes('animals')
        assert len(keys) == 1
        assert keys[0].field == 'legs'
        assert keys[0].primary is True

        pk = meta.table_pk('animals')
        assert pk.field == keys[0].field
        assert pk.primary == keys[0].primary
        assert pk.type == keys[0].type

        # cleanup
        with conn.cursor() as qry:
            qry.exec(self.dropTable)

    def test_users(self, conn):
        meta = Sqlite3Metadata(conn)
        assert len(meta.users()) == 0

    def test_user_groups(self, conn):
        meta = Sqlite3Metadata(conn)
        assert len(meta.user_groups('someuser')) == 0
