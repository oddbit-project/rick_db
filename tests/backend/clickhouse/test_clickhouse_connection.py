import pytest

from rick_db.backend.clickhouse import ClickHouseConnection
from rick_db.sql import ClickHouseSqlDialect


@pytest.fixture
def conn(ch_settings):
    try:
        c = ClickHouseConnection(**ch_settings)
    except Exception:
        pytest.skip("ClickHouse server not available")
        return

    yield c
    c.close()


class TestClickHouseConnectionIntegration:
    def test_connect(self, conn):
        assert conn is not None
        assert isinstance(conn.dialect(), ClickHouseSqlDialect)

    def test_client_property(self, conn):
        assert conn.client is not None

    def test_autocommit(self, conn):
        assert conn.autocommit is False

    def test_dialect(self, conn):
        d = conn.dialect()
        assert d.placeholder == "%s"
        assert d.insert_returning is False
        assert d.ilike is True

    def test_cursor_select(self, conn):
        with conn.cursor() as c:
            result = c.exec("SELECT 1 AS val")
            assert len(result) == 1
            assert result[0]["val"] == 1

    def test_cursor_fetchone(self, conn):
        with conn.cursor() as c:
            result = c.fetchone("SELECT 1 AS val")
            assert result is not None
            assert result["val"] == 1

    def test_cursor_fetchall(self, conn):
        with conn.cursor() as c:
            result = c.fetchall("SELECT number AS n FROM system.numbers LIMIT 3")
            assert len(result) == 3

    def test_begin_commit(self, conn):
        assert conn.in_transaction() is False
        conn.begin()
        assert conn.in_transaction() is True
        conn.commit()
        assert conn.in_transaction() is False

    def test_begin_rollback(self, conn):
        conn.begin()
        assert conn.in_transaction() is True
        conn.rollback()
        assert conn.in_transaction() is False

    def test_commit_noop(self, conn):
        # commit outside transaction should work (no-op)
        conn.commit()

    def test_rollback_noop(self, conn):
        # rollback outside transaction should work (no-op)
        conn.rollback()
