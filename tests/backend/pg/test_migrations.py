import pytest


from rick_db.backend.pg import PgManager, PgMigrationManager
from rick_db.migrations import MigrationRecord


class TestPgConnMigrationManager:

    @pytest.fixture()
    def mm(self, pg_conn) -> PgMigrationManager:
        mgr = PgManager(pg_conn)
        mm = PgMigrationManager(mgr)
        yield mm
        mgr.drop_table(mm.MIGRATION_TABLE)

    def test_install_manager(self, mm):
        meta = mm.manager

        # ensure no manager
        assert mm.is_installed() is False
        tables = meta.tables()
        assert mm.MIGRATION_TABLE not in tables

        # install manager
        result = mm.install()
        assert result.success is True
        assert result.error == ""
        assert mm.is_installed() is True
        tables = meta.tables()
        assert mm.MIGRATION_TABLE in tables

        # check table has no entries
        m_list = mm.list()
        assert len(m_list) == 0

    def test_register_and_flatten(self, mm):
        # check table has no entries
        if not mm.is_installed():
            mm.install()

        m_list = mm.list()
        assert len(m_list) == 0
        mig_1 = MigrationRecord(name="migration1")
        mig_2 = MigrationRecord(name="migration2")
        mig_3 = MigrationRecord(name="migration3")
        # insert records
        migs = [mig_1, mig_2, mig_3]
        for r in migs:
            result = mm.register(r)
            assert result.success is True
            assert result.error == ""

        # fetch all
        m_list = mm.list()
        assert len(m_list) == 3
        for i in range(0, len(migs)):
            assert migs[i].name == m_list[i].name
            assert len(str(m_list[i].applied)) > 0
            assert m_list[i].id > 0

        # try to insert duplicates
        for r in migs:
            result = mm.register(r)
            assert result.success is False
            assert len(result.error) > 0

        # flatten
        flatten = MigrationRecord(name="flattened")
        mm.flatten(flatten)
        # no old records
        m_list = mm.list()
        assert len(m_list) == 1

        # fetch by name
        r = mm.fetch_by_name("flattened")
        assert r.name == flatten.name
        assert len(str(r.applied)) > 0


class TestPgPoolMigrationManager(TestPgConnMigrationManager):

    @pytest.fixture()
    def mm(self, pg_pool) -> PgMigrationManager:
        mgr = PgManager(pg_pool)
        mm = PgMigrationManager(mgr)
        yield mm
        mgr.drop_table(mm.MIGRATION_TABLE)
