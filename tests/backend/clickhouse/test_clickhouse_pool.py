import threading
import time

import pytest
from unittest.mock import patch, MagicMock

from rick_db import Connection, Cursor, fieldmapper
from rick_db.backend.clickhouse import ClickHouseConnectionPool, ClickHouseRepository
from rick_db.backend.clickhouse.pool import PoolError
from rick_db.profiler import NullProfiler, DefaultProfiler
from rick_db.sql import ClickHouseSqlDialect


class SampleConnection(Connection):
    pass


@fieldmapper(tablename="pool_test", pk="id")
class PoolTestRecord:
    id = "id"
    value = "value"


create_table = """
CREATE TABLE IF NOT EXISTS pool_test (
    id UInt32,
    value String DEFAULT ''
) ENGINE = MergeTree()
ORDER BY id
"""

drop_table = "DROP TABLE IF EXISTS pool_test"


@pytest.fixture
def ch_pool(ch_settings):
    try:
        pool = ClickHouseConnectionPool(**ch_settings, ping=True, minconn=2, maxconn=10)
    except Exception:
        pytest.skip("ClickHouse server not available")
        return

    # verify connectivity
    try:
        with pool.connection() as conn:
            with conn.cursor() as c:
                c.exec("SELECT 1")
    except Exception:
        pool.close()
        pytest.skip("ClickHouse server not available")
        return

    # setup table
    with pool.connection() as conn:
        with conn.cursor() as c:
            c.exec(drop_table)
            c.exec(create_table)

    yield pool

    # teardown
    if not pool._closed:
        with pool.connection() as conn:
            with conn.cursor() as c:
                c.exec(drop_table)
        pool.close()
    else:
        # pool was closed by test; use a direct connection for cleanup
        from rick_db.backend.clickhouse import ClickHouseConnection
        conn = ClickHouseConnection(**ch_settings)
        with conn.cursor() as c:
            c.exec(drop_table)
        conn.close()


def _mock_get_client(**kwargs):
    client = MagicMock()
    result = MagicMock()
    result.column_names = ["1"]
    result.result_rows = [(1,)]
    client.query.return_value = result
    return client


class TestClickHousePool:

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_init(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=2, maxconn=5
        )
        assert pool is not None
        assert isinstance(pool.profiler, NullProfiler)
        assert isinstance(pool.dialect(), ClickHouseSqlDialect)
        assert pool._factory is Connection
        assert len(pool._pool) == 2
        assert pool._maxconn == 5
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_getconn(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=2, maxconn=5
        )
        conn = pool.getconn()
        assert conn is not None
        assert isinstance(conn, Connection)
        assert len(pool._pool) == 1
        pool.putconn(conn)
        assert conn.db is None
        assert len(pool._pool) == 2
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_cursor(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=2, maxconn=5
        )
        conn = pool.getconn()
        assert isinstance(conn, Connection)
        cursor = conn.get_cursor()
        assert isinstance(cursor, Cursor)
        result = cursor.fetchone("SELECT 1")
        assert result is not None
        pool.putconn(conn)
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_ctx(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=2, maxconn=5
        )
        with pool.connection() as conn:
            assert conn is not None
            assert isinstance(conn, Connection)
        # conn returned to pool
        assert len(pool._pool) == 2
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_exhaust(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=1, maxconn=3
        )
        conns = []
        with pytest.raises(PoolError):
            for i in range(10):
                conns.append(pool.getconn())
        assert len(conns) == 3
        for conn in conns:
            pool.putconn(conn)
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_closed(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=1, maxconn=3
        )
        pool.close()
        with pytest.raises(PoolError):
            pool.getconn()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_factory(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=2, maxconn=5
        )
        assert pool._factory is Connection
        pool.connection_factory(SampleConnection)
        assert pool._factory is SampleConnection
        with pool.connection() as conn:
            assert isinstance(conn, SampleConnection)
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_putconn_twice(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=2, maxconn=5
        )
        conn = pool.getconn()
        pool.putconn(conn)
        assert conn.db is None
        # second putconn should be a no-op
        pool.putconn(conn)
        assert len(pool._pool) == 2
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_ping(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=True, minconn=1, maxconn=3
        )
        conn = pool.getconn()
        assert conn is not None
        pool.putconn(conn)
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_grows_beyond_min(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=1, maxconn=3
        )
        conns = []
        conns.append(pool.getconn())
        conns.append(pool.getconn())
        assert len(conns) == 2
        for conn in conns:
            pool.putconn(conn)
        # pool now has 2 connections (grew from min=1)
        assert len(pool._pool) == 2
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_close_with_checked_out_connections(self, mock_client):
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=2, maxconn=5
        )
        conn = pool.getconn()
        assert len(pool._used) == 1
        pool.close()
        # close() should close both idle and in-use wrappers
        assert len(pool._pool) == 0
        assert len(pool._used) == 0
        assert pool._closed is True

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_stale_connection_recovery(self, mock_client):
        """Ping failure should replace the stale wrapper with a fresh one."""
        pool = ClickHouseConnectionPool(
            host="localhost", ping=True, minconn=1, maxconn=3
        )
        # make the first pooled wrapper's cursor raise on execute (stale)
        stale_wrapper = pool._pool[0]
        stale_cursor = MagicMock()
        stale_cursor.execute.side_effect = Exception("connection lost")
        stale_wrapper.cursor = MagicMock(return_value=stale_cursor)

        conn = pool.getconn()
        assert conn is not None
        # the wrapper should NOT be the stale one
        assert conn.db is not stale_wrapper
        pool.putconn(conn)
        pool.close()

    @patch("clickhouse_connect.get_client", side_effect=_mock_get_client)
    def test_pool_profiler_snapshot_at_checkout(self, mock_client):
        """Profiler is captured at checkout time; reassigning pool.profiler does not affect existing connections."""
        pool = ClickHouseConnectionPool(
            host="localhost", ping=False, minconn=2, maxconn=5
        )
        profiler1 = DefaultProfiler()
        pool.profiler = profiler1

        # checkout conn1 with profiler1
        conn1 = pool.getconn()
        assert conn1.profiler is profiler1

        # reassign pool profiler
        profiler2 = DefaultProfiler()
        pool.profiler = profiler2

        # checkout conn2 with profiler2
        conn2 = pool.getconn()
        assert conn2.profiler is profiler2

        # conn1 still has profiler1
        assert conn1.profiler is profiler1
        assert conn1.profiler is not profiler2

        # execute on both — events go to their respective profilers
        with conn1.cursor() as c:
            c.exec("SELECT 1")
        with conn2.cursor() as c:
            c.exec("SELECT 2")

        assert len(profiler1.get_events()) == 1
        assert profiler1.get_events()[0].query == "SELECT 1"
        assert len(profiler2.get_events()) == 1
        assert profiler2.get_events()[0].query == "SELECT 2"

        pool.putconn(conn1)
        pool.putconn(conn2)
        pool.close()


class TestClickHousePoolIntegration:

    def test_pool_connect(self, ch_pool):
        assert ch_pool is not None
        assert isinstance(ch_pool.dialect(), ClickHouseSqlDialect)

    def test_pool_cursor_select(self, ch_pool):
        with ch_pool.connection() as conn:
            with conn.cursor() as c:
                result = c.exec("SELECT 1 AS val")
                assert len(result) == 1
                assert result[0]["val"] == 1

    def test_pool_getconn_putconn(self, ch_pool):
        conn = ch_pool.getconn()
        assert conn is not None
        assert isinstance(conn, Connection)
        with conn.cursor() as c:
            result = c.fetchone("SELECT 1 AS val")
            assert result["val"] == 1
        ch_pool.putconn(conn)
        assert conn.db is None

    def test_pool_multiple_connections(self, ch_pool):
        conns = [ch_pool.getconn() for _ in range(5)]
        assert len(conns) == 5
        for conn in conns:
            with conn.cursor() as c:
                r = c.fetchone("SELECT 1 AS val")
                assert r["val"] == 1
        for conn in conns:
            ch_pool.putconn(conn)

    def test_pool_connection_reuse(self, ch_pool):
        with ch_pool.connection() as conn1:
            db1 = conn1.db
        # after returning, get another connection - should reuse
        with ch_pool.connection() as conn2:
            db2 = conn2.db
        assert db1 is db2

    def test_pool_insert_and_read(self, ch_pool):
        with ch_pool.connection() as conn:
            repo = ClickHouseRepository(conn, PoolTestRecord)
            repo.insert(PoolTestRecord(id=1, value="hello"))

        with ch_pool.connection() as conn:
            repo = ClickHouseRepository(conn, PoolTestRecord)
            record = repo.fetch_pk(1)
            assert record is not None
            assert record.value == "hello"

    def test_pool_exhaust(self, ch_pool):
        conns = []
        with pytest.raises(PoolError):
            for _ in range(20):
                conns.append(ch_pool.getconn())
        for conn in conns:
            ch_pool.putconn(conn)

    def test_pool_closed(self, ch_pool):
        ch_pool.close()
        with pytest.raises(PoolError):
            ch_pool.getconn()

    def test_pool_context_returns_on_exception(self, ch_pool):
        initial_count = len(ch_pool._pool)
        try:
            with ch_pool.connection() as conn:
                raise ValueError("test error")
        except ValueError:
            pass
        assert len(ch_pool._pool) == initial_count

    def test_pool_profiler(self, ch_pool):
        profiler = DefaultProfiler()
        ch_pool.profiler = profiler

        with ch_pool.connection() as conn:
            with conn.cursor() as c:
                c.exec("SELECT 1 AS val")
                c.exec("SELECT 2 AS val")

        events = profiler.get_events()
        assert len(events) >= 2
        queries = [e.query for e in events]
        assert "SELECT 1 AS val" in queries
        assert "SELECT 2 AS val" in queries
        for e in events:
            assert e.elapsed >= 0

    def test_pool_profiler_across_connections(self, ch_pool):
        profiler = DefaultProfiler()
        ch_pool.profiler = profiler

        with ch_pool.connection() as conn:
            with conn.cursor() as c:
                c.exec("SELECT 'conn1' AS src")

        with ch_pool.connection() as conn:
            with conn.cursor() as c:
                c.exec("SELECT 'conn2' AS src")

        events = profiler.get_events()
        queries = [e.query for e in events]
        assert "SELECT 'conn1' AS src" in queries
        assert "SELECT 'conn2' AS src" in queries

    def test_pool_stale_connection_recovery(self, ch_pool):
        """Force a wrapper to be stale and verify ping replaces it."""
        # get a connection and sabotage its wrapper before returning
        conn = ch_pool.getconn()
        wrapper = conn.db
        ch_pool.putconn(conn)

        # sabotage the wrapper so ping fails
        original_cursor = wrapper.cursor
        def broken_cursor():
            c = MagicMock()
            c.execute.side_effect = Exception("connection lost")
            return c
        wrapper.cursor = broken_cursor

        # getconn should detect stale via ping and create a fresh wrapper
        conn2 = ch_pool.getconn()
        assert conn2 is not None
        assert conn2.db is not wrapper
        # the fresh connection should work
        with conn2.cursor() as c:
            result = c.fetchone("SELECT 1 AS val")
            assert result["val"] == 1
        ch_pool.putconn(conn2)

    def test_concurrent_reads(self, ch_pool):
        # seed data
        with ch_pool.connection() as conn:
            with conn.cursor() as c:
                for i in range(100, 110):
                    c.exec(
                        "INSERT INTO pool_test (id, value) VALUES (%s, %s)",
                        [i, f"row_{i}"],
                    )

        errors = []
        results = []
        barrier = threading.Barrier(5, timeout=10)

        def worker():
            try:
                barrier.wait()
                with ch_pool.connection() as conn:
                    repo = ClickHouseRepository(conn, PoolTestRecord)
                    rows = repo.fetch_all()
                    results.append(len(rows))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 5
        for count in results:
            assert count >= 10

    def test_concurrent_writes(self, ch_pool):
        errors = []
        barrier = threading.Barrier(5, timeout=10)

        def writer(offset):
            try:
                barrier.wait()
                with ch_pool.connection() as conn:
                    with conn.cursor() as c:
                        for i in range(5):
                            row_id = offset + i
                            c.exec(
                                "INSERT INTO pool_test (id, value) VALUES (%s, %s)",
                                [row_id, f"concurrent_{row_id}"],
                            )
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(1000 + i * 100,))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(errors) == 0, f"Thread errors: {errors}"

        # verify all rows were written
        with ch_pool.connection() as conn:
            with conn.cursor() as c:
                result = c.fetchone(
                    "SELECT count() AS cnt FROM pool_test WHERE id >= 1000"
                )
                assert result["cnt"] == 25

    def test_concurrent_checkout_return(self, ch_pool):
        """Verify pool integrity under rapid concurrent checkout/return cycles."""
        errors = []
        barrier = threading.Barrier(8, timeout=10)

        def churn():
            try:
                barrier.wait()
                for _ in range(10):
                    conn = ch_pool.getconn()
                    with conn.cursor() as c:
                        c.exec("SELECT 1")
                    ch_pool.putconn(conn)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=churn) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Thread errors: {errors}"
        # all connections should be back in the pool
        assert len(ch_pool._used) == 0
        assert len(ch_pool._pool) > 0

    def test_concurrent_pool_exhaust_and_return(self, ch_pool):
        """Threads compete for a limited pool; all should succeed since maxconn=10."""
        errors = []
        completed = []
        lock = threading.Lock()
        barrier = threading.Barrier(10, timeout=10)

        def grab_and_hold(hold_time):
            try:
                barrier.wait()
                conn = ch_pool.getconn()
                with conn.cursor() as c:
                    c.exec("SELECT 1")
                time.sleep(hold_time)
                ch_pool.putconn(conn)
                with lock:
                    completed.append(True)
            except PoolError:
                with lock:
                    completed.append(False)
            except Exception as e:
                errors.append(e)

        # 10 threads compete for maxconn=10 pool
        threads = [
            threading.Thread(target=grab_and_hold, args=(0.05,))
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(errors) == 0, f"Thread errors: {errors}"
        # all 10 should succeed since maxconn=10
        assert completed.count(True) == 10
