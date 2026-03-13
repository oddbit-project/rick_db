import pytest

from rick_db.backend.clickhouse import ClickHouseConnection, ClickHouseManager

create_table = """
CREATE TABLE IF NOT EXISTS animal (
    id_animal UInt32,
    name String
) ENGINE = MergeTree()
ORDER BY id_animal
"""

create_view = "CREATE VIEW IF NOT EXISTS list_animal AS SELECT * FROM animal"


class TestClickHouseManager:
    def test_tables(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        # no tables created yet
        tables = mgr.tables()
        assert "animal" not in tables
        assert mgr.table_exists("animal") is False

        # create one table
        with mgr.conn() as conn:
            with conn.cursor() as c:
                c.exec(create_table)

        tables = mgr.tables()
        assert "animal" in tables
        assert mgr.table_exists("animal") is True

        # cleanup
        mgr.drop_table("animal")
        assert mgr.table_exists("animal") is False

    def test_views(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        # no views created yet
        assert mgr.view_exists("list_animal") is False

        # create table and view
        with mgr.conn() as conn:
            with conn.cursor() as c:
                c.exec(create_table)
                c.exec(create_view)

        views = mgr.views()
        assert "list_animal" in views
        assert mgr.view_exists("list_animal") is True

        # views should not appear in tables()
        tables = mgr.tables()
        assert "list_animal" not in tables

        # cleanup
        mgr.drop_view("list_animal")
        assert mgr.view_exists("list_animal") is False

    def test_databases(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        dbs = mgr.databases()
        assert len(dbs) > 0
        # system databases should always exist
        assert "system" in dbs

    def test_schemas_equals_databases(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        assert mgr.schemas() == mgr.databases()

    def test_table_fields(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        with mgr.conn() as conn:
            with conn.cursor() as c:
                c.exec(create_table)

        fields = mgr.table_fields("animal")
        assert len(fields) == 2
        field1, field2 = fields
        assert field1.field == "id_animal"
        assert field1.primary is True
        assert field2.field == "name"
        assert field2.primary is False

    def test_view_fields(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        with mgr.conn() as conn:
            with conn.cursor() as c:
                c.exec(create_table)
                c.exec(create_view)

        fields = mgr.view_fields("list_animal")
        assert len(fields) == 2

    def test_table_pk(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        with mgr.conn() as conn:
            with conn.cursor() as c:
                c.exec(create_table)

        pk = mgr.table_pk("animal")
        assert pk is not None
        assert pk.field == "id_animal"

    def test_table_pk_none(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        # non-existing table
        pk = mgr.table_pk("nonexistent_table")
        assert pk is None

    def test_table_indexes(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        with mgr.conn() as conn:
            with conn.cursor() as c:
                c.exec(create_table)

        # MergeTree tables without explicit skip indexes return empty
        indexes = mgr.table_indexes("animal")
        assert isinstance(indexes, list)

    def test_users(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        users = mgr.users()
        assert isinstance(users, list)
        # at least the default user should exist
        assert len(users) > 0

    def test_user_groups(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        groups = mgr.user_groups("default")
        assert groups == []

    def test_create_drop_database(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        db_name = "rickdb_test_tmp"

        # create
        mgr.create_database(db_name)
        assert mgr.database_exists(db_name) is True

        # drop
        mgr.drop_database(db_name)
        assert mgr.database_exists(db_name) is False

    def test_schema_exists_delegates(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        # system database always exists
        assert mgr.schema_exists("system") is True
        assert mgr.schema_exists("nonexistent_schema_xyz") is False

    def test_create_schema_raises(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        with pytest.raises(NotImplementedError):
            mgr.create_schema("test")

    def test_drop_schema_raises(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        with pytest.raises(NotImplementedError):
            mgr.drop_schema("test")

    def test_kill_clients_raises(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        with pytest.raises(NotImplementedError):
            mgr.kill_clients("test")

    def test_backend(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        assert mgr.backend() is ch_backend

    def test_drop_table(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        with mgr.conn() as conn:
            with conn.cursor() as c:
                c.exec(create_table)
        assert mgr.table_exists("animal") is True
        mgr.drop_table("animal")
        assert mgr.table_exists("animal") is False

    def test_drop_view(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        with mgr.conn() as conn:
            with conn.cursor() as c:
                c.exec(create_table)
                c.exec(create_view)
        assert mgr.view_exists("list_animal") is True
        mgr.drop_view("list_animal")
        assert mgr.view_exists("list_animal") is False
