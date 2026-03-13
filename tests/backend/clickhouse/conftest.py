import pytest

from rick_db.backend.clickhouse import ClickHouseConnection, ClickHouseManager


def _clickhouse_available(settings):
    """Check if a ClickHouse server is reachable."""
    try:
        conn = ClickHouseConnection(**settings)
        with conn.cursor() as c:
            c.exec("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture
def ch_backend(ch_settings):
    if not _clickhouse_available(ch_settings):
        pytest.skip("ClickHouse server not available")

    conn = ClickHouseConnection(**ch_settings)
    yield conn

    # teardown
    mgr = ClickHouseManager(conn)
    mgr.drop_table("_migration")
    mgr.drop_view("list_animal")
    mgr.drop_table("animal")
    mgr.drop_table("users")

    conn.close()
