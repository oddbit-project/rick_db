import pytest

from rick_db.conn.pg import PgConnection
from rick_db.util.pg import PgMetadata, PgInfo
from tests.config import postgres_db, connectSimple
from tests.util.pg.common import PgCommon


class TestPgInfo(PgCommon):
    def test_tables(self, conn):
        info = PgInfo(conn)
        # no tables created yet
        tables = info.list_database_tables()
        assert info.table_exists("animals") is False

        # create one table
        with conn.cursor() as qry:
            qry.exec(self.createTable)

        tables = info.list_database_tables()
        assert tables[0].name == "animals"
        assert info.table_exists("animals") is True

        # cleanup
        with conn.cursor() as c:
            c.exec(self.dropTable)

        # test with schema
        with conn.cursor() as qry:
            qry.exec(self.createSchema)
        tables = info.list_database_tables(schema="myschema")
        assert len(tables) is 0
        assert info.table_exists("aliens", schema="myschema") is False

        # create one schema table
        with conn.cursor() as qry:
            qry.exec(self.createSchemaTable)
        tables = info.list_database_tables("myschema")
        assert tables[0].name == "aliens"
        assert info.table_exists("aliens", schema="myschema") is True

        # cleanup
        self.cleanup(conn)

    def test_namespaces(self, conn):
        info = PgInfo(conn)
        namespaces = info.list_database_namespaces()
        schemas = [ns.name for ns in namespaces]
        assert len(schemas) > 2
        assert "public" in schemas
        assert "information_schema" in schemas

        # create schema
        with conn.cursor() as c:
            c.exec(self.createSchema)

        namespaces = info.list_database_namespaces()
        schemas = [ns.name for ns in namespaces]
        assert "myschema" in schemas
        assert len(schemas) > 2

        self.cleanup(conn)

    def test_databases(self, conn):
        info = PgInfo(conn)
        dbs = info.list_server_databases()
        assert len(dbs) > 0
        names = [r.name for r in dbs]
        assert postgres_db["dbname"] in names

    def test_views(self, conn):
        info = PgInfo(conn)
        # no views created yet
        views = info.list_database_views()
        assert len(views) == 0
        assert info.table_exists("list_animals", info.TYPE_VIEW) is False

        # create one table
        with conn.cursor() as qry:
            qry.exec(self.createTable)
            qry.exec(self.createView)

        views = info.list_database_views()
        assert len(views) == 1
        assert views[0].name == "list_animals"
        assert info.table_exists("list_animals", info.TYPE_VIEW) is True

        # cleanup
        with conn.cursor() as qry:
            qry.exec(self.dropView)
            qry.exec(self.dropTable)

        # test with schema
        with conn.cursor() as qry:
            qry.exec(self.createSchema)
        views = info.list_database_views("myschema")
        assert len(views) == 0
        assert (
            info.table_exists("list_aliens", info.TYPE_VIEW, schema="myschema") is False
        )

        # create one schema table
        with conn.cursor() as qry:
            qry.exec(self.createSchemaTable)
            qry.exec(self.createSchemaView)
        views = info.list_database_views("myschema")
        assert len(views) == 1
        assert views[0].name == "list_aliens"
        assert (
            info.table_exists("list_aliens", info.TYPE_VIEW, schema="myschema") is True
        )

        self.cleanup(conn)

    def test_table_fields(self, conn):
        info = PgInfo(conn)
        with conn.cursor() as qry:
            qry.exec(self.createTable)
            qry.exec(self.createView)

        # test table fields
        fields = [r.column for r in info.list_table_columns("animals")]
        assert "legs" in fields
        assert "name" in fields
        assert len(fields) == 2

        # test view fields
        fields = [r.column for r in info.list_table_columns("list_animals")]
        assert "legs" in fields
        assert "name" in fields
        assert len(fields) == 2

        self.cleanup(conn)

    def test_table_keys(self, conn):
        info = PgInfo(conn)
        # create one table
        with conn.cursor() as qry:
            qry.exec(self.createTable)

        # create table
        tables = info.list_database_tables()
        assert len(tables) == 1
        assert tables[0].name == "animals"
        assert info.table_exists("animals") is True

        keys = info.list_table_indexes("animals")
        assert len(keys) == 1
        assert keys[0].field == "legs"
        assert keys[0].primary is True

        pk = info.list_table_pk("animals")
        assert pk.column == keys[0].field

        # cleanup
        with conn.cursor() as qry:
            qry.exec(self.dropTable)

        # create table with schema
        with conn.cursor() as qry:
            qry.exec(self.createSchema)
            qry.exec(self.createSchemaTable)

        keys = info.list_table_indexes("aliens", "myschema")
        assert len(keys) == 1
        assert keys[0].field == "legs"
        assert keys[0].primary is True

        pk = info.list_table_pk("aliens", "myschema")
        assert pk.column == keys[0].field

        self.cleanup(conn)

    def test_users(self, conn):
        info = PgInfo(conn)
        users = info.list_server_roles()
        assert len(users) > 0
        names = [r.name for r in users]
        assert postgres_db["user"] in names

    def test_user_groups(self, conn):
        info = PgInfo(conn)
        groups = info.list_user_groups(postgres_db["user"])
        assert len(groups) == 0

        with conn.cursor() as qry:
            qry.exec(self.createGroup)
            qry.exec(self.addGroup.format(user=postgres_db["user"]))

        groups = info.list_user_groups(postgres_db["user"])
        assert len(groups) == 1
        assert groups[0].name == "staff"

        with conn.cursor() as qry:
            qry.exec(self.dropGroup)
