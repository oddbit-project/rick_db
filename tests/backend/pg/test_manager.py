import pytest
from .common import (
    create_table,
    create_schema,
    create_schema_table,
    create_view,
    create_schema_view,
    create_group,
    add_group,
    drop_group,
)

from rick_db.backend.pg import PgManager, PgConnection, PgConnectionPool


class BasePgManagerTest:
    def test_tables(self, conn):
        pgmeta = PgManager(conn)
        # no tables created yet
        tables = pgmeta.tables()
        assert len(tables) == 0
        assert pgmeta.table_exists("animal") is False

        # create one table
        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)

        tables = pgmeta.tables()
        assert len(tables) == 1
        assert tables[0] == "animal"
        assert pgmeta.table_exists("animal") is True

        # cleanup
        pgmeta.drop_table("animal")

        # test with schema
        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_schema)
        tables = pgmeta.tables("myschema")
        assert len(tables) == 0
        assert pgmeta.table_exists("aliens", "myschema") is False

        # create one schema table
        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_schema_table)
        tables = pgmeta.tables("myschema")
        assert len(tables) == 1
        assert tables[0] == "aliens"
        assert pgmeta.table_exists("aliens", "myschema") is True

    def test_schemas(self, conn):
        pgmeta = PgManager(conn)
        schemas = pgmeta.schemas()
        assert len(schemas) > 2
        assert "public" in schemas
        assert "information_schema" in schemas

        # create schema
        with pgmeta.conn() as conn:
            with conn.cursor() as c:
                c.exec(create_schema)

        schemas = pgmeta.schemas()
        assert "myschema" in schemas
        assert len(schemas) > 2

    def test_databases(self, conn, pg_settings):
        pgmeta = PgManager(conn)
        dbs = pgmeta.databases()
        assert len(dbs) > 0
        assert pg_settings["database"] in dbs

    def test_views(self, conn):
        pgmeta = PgManager(conn)
        # no views created yet
        views = pgmeta.views()
        assert len(views) == 0
        assert pgmeta.view_exists("list_animal") is False

        # create one table
        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)
                qry.exec(create_view)

        views = pgmeta.views()
        assert len(views) == 1
        assert views[0] == "list_animal"
        assert pgmeta.view_exists("list_animal") is True

    def test_view_schema(self, conn, pg_settings):
        pgmeta = PgManager(conn)

        # test with schema
        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_schema)
        views = pgmeta.tables("myschema")
        assert len(views) == 0
        assert pgmeta.view_exists("list_aliens", "myschema") is False

        # create one schema table
        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_schema_table)
                qry.exec(create_schema_view)
        views = pgmeta.views("myschema")
        assert len(views) == 1
        assert views[0] == "list_aliens"
        assert pgmeta.view_exists("list_aliens", "myschema") is True

    def test_table_fields(self, conn):
        pgmeta = PgManager(conn)
        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)
                qry.exec(create_view)

        # test table fields
        fields = pgmeta.table_fields("animal")
        assert len(fields) == 2
        field1, field2 = fields
        assert field1.field == "id_animal"
        assert field1.primary is True
        assert field2.field == "name"
        assert field2.primary is False

        # test view fields
        fields = pgmeta.view_fields("list_animal")
        assert len(fields) == 2
        field1, field2 = fields
        assert field1.field == "id_animal"
        assert field1.primary is False  # views don't have keys
        assert field2.field == "name"
        assert field2.primary is False

    def test_table_keys(self, conn):
        pgmeta = PgManager(conn)
        # create one table
        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)

        # create table
        tables = pgmeta.tables()
        assert len(tables) == 1
        assert tables[0] == "animal"
        assert pgmeta.table_exists("animal") is True

        keys = pgmeta.table_indexes("animal")
        assert len(keys) == 1
        assert keys[0].field == "id_animal"
        assert keys[0].primary is True

        pk = pgmeta.table_pk("animal")
        assert pk.field == keys[0].field
        assert pk.primary == keys[0].primary
        assert pk.type is None  # table_pk does not retrieve type

        # cleanup
        pgmeta.drop_table("animal")

        # create table with schema
        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_schema)
                qry.exec(create_schema_table)

        keys = pgmeta.table_indexes("aliens", "myschema")
        assert len(keys) == 1
        assert keys[0].field == "id_alien"
        assert keys[0].primary is True

        pk = pgmeta.table_pk("aliens", "myschema")
        assert pk.field == keys[0].field
        assert pk.primary == keys[0].primary
        assert pk.type is None  # table_pk does not retrieve type

    def test_users(self, conn, pg_settings):
        pgmeta = PgManager(conn)
        users = pgmeta.users()
        assert len(users) > 0
        names = []
        for r in users:
            names.append(r.name)
        assert pg_settings["user"] in names

    def test_user_groups(self, conn, pg_settings):
        pgmeta = PgManager(conn)
        groups = pgmeta.user_groups(pg_settings["user"])
        assert len(groups) == 0

        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_group)
                qry.exec(add_group.format(user=pg_settings["user"]))

        groups = pgmeta.user_groups(pg_settings["user"])
        assert len(groups) == 1
        assert groups[0] == "staff"

        with pgmeta.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(drop_group)

    def test_create_drop_db(self, conn):
        pgmeta = PgManager(conn)
        pgmeta.create_database("sample_database")
        assert pgmeta.database_exists("sample_database") is True
        pgmeta.drop_database("sample_database")
        assert pgmeta.database_exists("sample_database") is False

    def test_create_drop_schema(self, conn):
        pgmeta = PgManager(conn)
        pgmeta.create_schema("sample_schema")
        assert pgmeta.schema_exists("sample_schema") is True
        pgmeta.drop_schema("sample_schema")
        assert pgmeta.schema_exists("sample_schema") is False


class TestPgManagerConn(BasePgManagerTest):

    @pytest.fixture
    def conn(self, pg_settings):
        conn = PgConnection(**pg_settings)

        yield conn

        # teardown
        md = PgManager(conn)
        md.drop_table("_migration")
        md.drop_view("list_animal")
        md.drop_table("animal")
        md.drop_table("foo")
        md.drop_schema("myschema", True)

        conn.close()


class TestPgManagerPool(BasePgManagerTest):

    @pytest.fixture
    def conn(self, pg_settings: dict):
        pool = PgConnectionPool(**pg_settings)

        yield pool

        # teardown
        with pool.connection() as conn:
            md = PgManager(conn)
            md.drop_table("_migration")
            md.drop_view("list_animal")
            md.drop_table("animal")
            md.drop_table("foo")
            md.drop_schema("myschema", True)
        pool.close()
