import pytest

from rick_db.backend.pg import PgConnection, PgConnectionPool
from rick_db.backend.pg.manager import PgManager
from rick_db.backend.pg.pginfo import PgInfo
from .common import (
    create_table,
    create_fk_table,
    create_schema,
    create_schema_table,
    create_view,
    create_schema_view,
    create_group,
    add_group,
    drop_group,
    create_identity_table,
)


class BasePgInfoTest:

    @pytest.fixture()
    def conn(self, pg_settings) -> PgConnection:
        pass

    def test_tables(self, conn):
        info = PgInfo(conn)
        meta = PgManager(conn)

        # make sure no tables exist
        meta.drop_table("animal_type")
        meta.drop_table("animal")
        meta.drop_view("list_animal")

        # no tables created yet
        tables = info.list_database_tables()
        assert info.table_exists("animal") is False

        # create one table
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)

        tables = info.list_database_tables()
        assert tables[0].name == "animal"
        assert info.table_exists("animal") is True

        # cleanup
        meta.drop_table("animal")

        # test with schema
        with info.conn() as c:
            with c.cursor() as qry:
                qry.exec(create_schema)
        tables = info.list_database_tables(schema="myschema")
        assert len(tables) == 0
        assert info.table_exists("aliens", schema="myschema") is False

        # create one schema table
        with info.conn() as c:
            with c.cursor() as qry:
                qry.exec(create_schema_table)
        tables = info.list_database_tables("myschema")
        assert tables[0].name == "aliens"
        assert info.table_exists("aliens", schema="myschema") is True

    def test_namespaces(self, conn):
        info = PgInfo(conn)
        namespaces = info.list_database_namespaces()
        schemas = [ns.name for ns in namespaces]
        assert len(schemas) > 2
        assert "public" in schemas
        assert "information_schema" in schemas

        # create schema
        with info.conn() as db:
            with db.cursor() as c:
                c.exec(create_schema)

        namespaces = info.list_database_namespaces()
        schemas = [ns.name for ns in namespaces]
        assert "myschema" in schemas
        assert len(schemas) > 2

    def test_databases(self, conn, pg_settings):
        info = PgInfo(conn)
        dbs = info.list_server_databases()
        assert len(dbs) > 0
        names = [r.name for r in dbs]
        assert pg_settings["database"] in names

    def test_views(self, conn):
        info = PgInfo(conn)
        meta = PgManager(conn)
        # no views created yet
        views = info.list_database_views()
        assert len(views) == 0
        assert info.table_exists("list_animal", info.TYPE_VIEW) is False

        # create one table
        with info.conn() as c:
            with c.cursor() as qry:
                qry.exec(create_table)
                qry.exec(create_view)

        views = info.list_database_views()
        assert len(views) == 1
        assert views[0].name == "list_animal"
        assert info.table_exists("list_animal", info.TYPE_VIEW) is True

        # cleanup
        meta.drop_view("list_animal")
        meta.drop_table("animal")

        # test with schema
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_schema)
        views = info.list_database_views("myschema")
        assert len(views) == 0
        assert (
            info.table_exists("list_aliens", info.TYPE_VIEW, schema="myschema") is False
        )

        # create one schema table
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_schema_table)
                qry.exec(create_schema_view)

        views = info.list_database_views("myschema")
        assert len(views) == 1
        assert views[0].name == "list_aliens"
        assert (
            info.table_exists("list_aliens", info.TYPE_VIEW, schema="myschema") is True
        )

    def test_table_fields(self, conn):
        info = PgInfo(conn)
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)
                qry.exec(create_view)

        # test table fields
        fields = [r.column for r in info.list_table_columns("animal")]
        assert "id_animal" in fields
        assert "name" in fields
        assert len(fields) == 2

        # test view fields
        fields = [r.column for r in info.list_table_columns("list_animal")]
        assert "id_animal" in fields
        assert "name" in fields
        assert len(fields) == 2

    def test_table_keys(self, conn):
        info = PgInfo(conn)
        meta = PgManager(conn)

        # create one table
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)

        # create table
        tables = info.list_database_tables()
        assert len(tables) == 1
        assert tables[0].name == "animal"
        assert info.table_exists("animal") is True

        keys = info.list_table_indexes("animal")
        assert len(keys) == 1
        assert keys[0].field == "id_animal"
        assert keys[0].primary is True

        pk = info.list_table_pk("animal")
        assert pk.column == keys[0].field

        #
        meta.drop_table("animal")

        # create table with schema
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_schema)
                qry.exec(create_schema_table)

        keys = info.list_table_indexes("aliens", "myschema")
        assert len(keys) == 1
        assert keys[0].field == "id_alien"
        assert keys[0].primary is True

        pk = info.list_table_pk("aliens", "myschema")
        assert pk.column == keys[0].field

    def test_users(self, conn, pg_settings):
        info = PgInfo(conn)
        users = info.list_server_roles()
        assert len(users) > 0
        names = [r.name for r in users]
        assert pg_settings["user"] in names

    def test_user_groups(self, conn, pg_settings):
        info = PgInfo(conn)
        groups = info.list_user_groups(pg_settings["user"])
        assert len(groups) == 0

        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_group)
                qry.exec(add_group.format(user=pg_settings["user"]))

        groups = info.list_user_groups(pg_settings["user"])
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(drop_group)

        assert len(groups) == 1
        assert groups[0].name == "staff"

    def test_server_groups(self, conn, pg_settings):
        info = PgInfo(conn)
        groups = info.list_server_groups()
        group_names = [g.name for g in groups]
        assert "staff" not in group_names

        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_group)

        groups = info.list_server_groups()
        group_names = [g.name for g in groups]
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(drop_group)

        assert "staff" in group_names

    def test_list_table_sequences(self, conn):
        info = PgInfo(conn)
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)
                qry.exec(create_view)

        serials = info.list_table_sequences("animal")
        assert len(serials) == 1
        assert serials[0].table == "public.animal"
        assert serials[0].column == "id_animal"
        assert serials[0].sequence == "public.animal_id_animal_seq"

    def test_list_identity_columns(self, conn):
        info = PgInfo(conn)
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)
                qry.exec(create_identity_table)

        serials = info.list_identity_columns("animal")
        assert len(serials) == 0

        serials = info.list_identity_columns("foo")
        assert len(serials) == 1
        assert serials[0].column == "id_foo"
        assert serials[0].generated == ""
        assert serials[0].identity == "a"

    def test_server_version(self, conn):
        info = PgInfo(conn)
        version = info.get_server_version()
        assert len(version) > 0
        chunks = version.split(".")
        assert len(chunks) >= 2

    def test_server_tablespaces(self, conn):
        info = PgInfo(conn)
        ts = info.list_server_tablespaces()
        # to create a tablespace, a superuser and a local path is required;
        # as such, testing can be troublesome; instead we list the local tablespaces
        assert len(ts) > 0
        ts_names = [t.name for t in ts]
        assert "pg_default" in ts_names

    def test_server_settings(self, conn):
        info = PgInfo(conn)
        settings = info.list_server_settings()
        names = [s.name for s in settings]
        # just some settings
        for n in [
            "checkpoint_completion_target",
            "enable_material",
            "huge_pages",
            "work_mem",
        ]:
            assert n in names

    def test_list_database_schemas(self, conn):
        info = PgInfo(conn)
        schema = info.list_database_schemas()
        names = [s.name for s in schema]
        for n in ["information_schema", "pg_catalog", "pg_toast", "public"]:
            assert n in names

    def test_list_server_users(self, conn, pg_settings):
        info = PgInfo(conn)
        users = info.list_server_users()
        names = [u.name for u in users]
        assert pg_settings["user"] in names

    def test_list_table_foreign_keys(self, conn):
        info = PgInfo(conn)
        meta = PgManager(conn)

        # create table with foreign key
        with info.conn() as conn:
            with conn.cursor() as qry:
                qry.exec(create_table)
                qry.exec(create_fk_table)

        fks = info.list_table_foreign_keys("animal_type")
        assert len(fks) == 1
        assert fks[0].table == "animal_type"
        assert fks[0].column == "fk_animal"
        assert fks[0].foreign_table == "animal"
        assert fks[0].foreign_column == "id_animal"
        assert fks[0].schema == "public"

        # cleanup
        meta.drop_table("animal_type")
        meta.drop_table("animal")


class TestPgInfoConn(BasePgInfoTest):

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


class TestPgInfoPool(BasePgInfoTest):

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
