from rick_db.util import MigrationRecord
from rick_db.util.migrations import MIGRATION_TABLE


class BaseMigrationManager:

    def test_install_manager(self, mm):
        meta = mm._meta

        # ensure no manager
        assert mm.has_manager() is False
        tables = meta.tables()
        assert MIGRATION_TABLE not in tables

        # install manager
        result = mm.install_manager()
        assert result.success is True
        assert result.error == ""
        assert mm.has_manager() is True
        tables = meta.tables()
        assert MIGRATION_TABLE in tables

        # check table has no entries
        m_list = mm.list()
        assert len(m_list) == 0

    def test_register_and_flatten(self, mm):
        # check table has no entries
        if not mm.has_manager():
            mm.install_manager()

        m_list = mm.list()
        assert len(m_list) == 0
        mig_1 = MigrationRecord(name='migration1')
        mig_2 = MigrationRecord(name='migration2')
        mig_3 = MigrationRecord(name='migration3')
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
        flatten = MigrationRecord(name='flattened')
        mm.flatten(flatten)
        # no old records
        m_list = mm.list()
        assert len(m_list) == 1

        # fetch by name
        r = mm.fetch_by_name('flattened')
        assert r.name == flatten.name
        assert len(str(r.applied)) > 0
