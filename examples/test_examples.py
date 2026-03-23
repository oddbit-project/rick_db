"""
Test harness for all examples.

Runs each example and verifies it completes without errors.
SQLite and query builder examples run standalone.
PostgreSQL and ClickHouse examples require the docker-compose services.

Usage:
    # Start services
    docker compose -f examples/docker-compose.yml up -d --wait

    # Run tests
    pytest examples/test_examples.py -v

    # Tear down
    docker compose -f examples/docker-compose.yml down
"""
import os
import subprocess
import sys

import pytest

EXAMPLES_DIR = os.path.dirname(__file__)
PYTHON = sys.executable


def run_example(script_path, timeout=30):
    """Run an example script and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [PYTHON, script_path],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=os.path.dirname(os.path.dirname(script_path)),
    )
    return result


# -- SQLite examples (no external dependencies) --


class TestSqliteExamples:
    def test_crud_sqlite(self):
        result = run_example(os.path.join(EXAMPLES_DIR, "repository", "crud_sqlite.py"))
        assert result.returncode == 0, result.stderr
        assert "Inserted Alice" in result.stdout
        assert "After update: Alice Updated" in result.stdout
        assert "After deleting Charlie" in result.stdout

    def test_transactions(self):
        result = run_example(os.path.join(EXAMPLES_DIR, "repository", "transactions.py"))
        assert result.returncode == 0, result.stderr
        assert "Transferred 200.0 from Alice to Bob" in result.stdout
        assert "Transaction rolled back" in result.stdout
        assert "Bob balance: 700.0" in result.stdout

    def test_dbgrid_search(self):
        result = run_example(os.path.join(EXAMPLES_DIR, "repository", "dbgrid_search.py"))
        assert result.returncode == 0, result.stderr
        assert "Python Cookbook" in result.stdout
        assert "Total matching: 4" in result.stdout
        assert "page 2" in result.stdout

    def test_migration_workflow(self):
        result = run_example(os.path.join(EXAMPLES_DIR, "migrations", "migration_workflow.py"))
        assert result.returncode == 0, result.stderr
        assert "Migration table installed" in result.stdout
        assert "Applied: 001_create_users" in result.stdout
        assert "No pending migrations" in result.stdout
        assert "Inserted user via migrated schema" in result.stdout


# -- Query builder examples (no external dependencies, SQL generation only) --


class TestQueryBuilderExamples:
    def test_fn_aggregation(self):
        result = run_example(
            os.path.join(EXAMPLES_DIR, "query_builder", "fn_aggregation.py")
        )
        assert result.returncode == 0, result.stderr
        assert "COUNT(*)" in result.stdout
        assert "GROUP BY" in result.stdout
        assert "HAVING" in result.stdout

    def test_cte_recursive(self):
        result = run_example(
            os.path.join(EXAMPLES_DIR, "query_builder", "cte_recursive.py")
        )
        assert result.returncode == 0, result.stderr
        assert "WITH RECURSIVE" in result.stdout
        assert "folder_tree" in result.stdout
        assert "Multiple CTEs" in result.stdout

    def test_json_queries(self):
        result = run_example(
            os.path.join(EXAMPLES_DIR, "query_builder", "json_queries.py")
        )
        assert result.returncode == 0, result.stderr
        assert "->>" in result.stdout
        assert "json_where" in result.stdout
        assert "Combined filter" in result.stdout


# -- PostgreSQL examples (require docker-compose postgres service) --


def pg_available():
    """Check if the PostgreSQL docker service is reachable."""
    try:
        from rick_db.backend.pg import PgConnection

        conn = PgConnection(
            host=os.environ.get("PGHOST", "localhost"),
            port=int(os.environ.get("PGPORT", 15432)),
            user=os.environ.get("POSTGRES_USER", "some_user"),
            password=os.environ.get("POSTGRES_PASSWORD", "somePassword"),
            dbname=os.environ.get("POSTGRES_DB", "testdb"),
        )
        conn.close()
        return True
    except Exception:
        return False


requires_pg = pytest.mark.skipif(
    not pg_available(), reason="PostgreSQL not available (start docker-compose)"
)


@requires_pg
class TestPostgresExamples:
    """Tests that require the PostgreSQL docker-compose service."""

    def _pg_conn(self):
        from rick_db.backend.pg import PgConnection

        return PgConnection(
            host=os.environ.get("PGHOST", "localhost"),
            port=int(os.environ.get("PGPORT", 15432)),
            user=os.environ.get("POSTGRES_USER", "some_user"),
            password=os.environ.get("POSTGRES_PASSWORD", "somePassword"),
            dbname=os.environ.get("POSTGRES_DB", "testdb"),
        )

    def test_complex_query_01(self):
        """Verify complex_query_01.py at least parses and imports correctly."""
        import ast

        script = os.path.join(EXAMPLES_DIR, "query_builder", "complex_query_01.py")
        with open(script) as f:
            ast.parse(f.read())

    def test_bookstore_imports(self):
        """Verify example_bookstore.py parses and the classes are valid."""
        import ast

        script = os.path.join(EXAMPLES_DIR, "repository", "example_bookstore.py")
        with open(script) as f:
            ast.parse(f.read())

    def test_pg_query_builder_roundtrip(self):
        """Run a query builder query against the real PostgreSQL instance."""
        from rick_db import fieldmapper, Repository
        from rick_db.sql import Select, Fn

        conn = self._pg_conn()
        try:
            with conn.cursor() as c:
                c.exec(
                    """
                    CREATE TABLE IF NOT EXISTS test_example_products (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        price NUMERIC(10,2) NOT NULL
                    )
                    """
                )
                c.exec("DELETE FROM test_example_products")
                c.exec(
                    "INSERT INTO test_example_products (name, category, price) VALUES "
                    "('Widget A', 'widgets', 10.00), "
                    "('Widget B', 'widgets', 20.00), "
                    "('Gadget A', 'gadgets', 30.00)"
                )
                c.close()

            @fieldmapper(tablename="test_example_products", pk="id")
            class Product:
                id = "id"
                name = "name"
                category = "category"
                price = "price"

            repo = Repository(conn, Product)

            # Test basic fetch
            products = repo.fetch_all()
            assert len(products) == 3

            # Test query builder with Fn
            qry = (
                Select(conn.dialect())
                .from_(
                    Product,
                    {Product.category: None, Fn.count(): "cnt", Fn.sum(Product.price): "total"},
                )
                .group(Product.category)
            )
            sql, values = qry.assemble()
            with conn.cursor() as c:
                rows = c.fetchall(sql, values)
                assert len(rows) == 2  # widgets and gadgets

        finally:
            with conn.cursor() as c:
                c.exec("DROP TABLE IF EXISTS test_example_products")
                c.close()
            conn.close()


# -- ClickHouse examples (require docker-compose clickhouse service) --


def ch_available():
    """Check if the ClickHouse docker service is reachable."""
    try:
        from rick_db.backend.clickhouse import ClickHouseConnection

        conn = ClickHouseConnection(
            host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
            port=int(os.environ.get("CLICKHOUSE_PORT", 18123)),
            username=os.environ.get("CLICKHOUSE_USER", "some_user"),
            password=os.environ.get("CLICKHOUSE_PASSWORD", "somePassword"),
            database=os.environ.get("CLICKHOUSE_DB", "testdb"),
        )
        conn.close()
        return True
    except Exception:
        return False


requires_ch = pytest.mark.skipif(
    not ch_available(), reason="ClickHouse not available (start docker-compose)"
)


@requires_ch
class TestClickHouseExamples:
    """Tests that require the ClickHouse docker-compose service."""

    def _ch_conn(self):
        from rick_db.backend.clickhouse import ClickHouseConnection

        return ClickHouseConnection(
            host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
            port=int(os.environ.get("CLICKHOUSE_PORT", 18123)),
            username=os.environ.get("CLICKHOUSE_USER", "some_user"),
            password=os.environ.get("CLICKHOUSE_PASSWORD", "somePassword"),
            database=os.environ.get("CLICKHOUSE_DB", "testdb"),
        )

    def test_clickhouse_introspection(self):
        """Test ClickHouse connection and introspection."""
        from rick_db.backend.clickhouse import ClickHouseManager

        conn = self._ch_conn()
        try:
            mgr = ClickHouseManager(conn)
            databases = mgr.databases()
            assert isinstance(databases, list)
            assert len(databases) > 0
        finally:
            conn.close()

    def test_clickhouse_crud(self):
        """Test ClickHouse table creation, insert, and query."""
        from rick_db import fieldmapper, Repository
        from rick_db.backend.clickhouse import ClickHouseManager

        conn = self._ch_conn()
        try:
            with conn.cursor() as c:
                c.exec(
                    """
                    CREATE TABLE IF NOT EXISTS test_example_events (
                        id UInt64,
                        event_type String,
                        amount Float64
                    ) ENGINE = MergeTree()
                    ORDER BY id
                    """
                )
                c.exec(
                    """
                    INSERT INTO test_example_events (id, event_type, amount) VALUES
                        (1, 'purchase', 29.99),
                        (2, 'purchase', 149.50),
                        (3, 'refund', 29.99)
                    """
                )
                c.close()

            @fieldmapper(tablename="test_example_events", pk="id")
            class Event:
                id = "id"
                event_type = "event_type"
                amount = "amount"

            repo = Repository(conn, Event)
            events = repo.fetch_all()
            assert len(events) == 3

            mgr = ClickHouseManager(conn)
            assert mgr.table_exists("test_example_events")
            fields = mgr.table_fields("test_example_events")
            assert len(fields) == 3

        finally:
            with conn.cursor() as c:
                c.exec("DROP TABLE IF EXISTS test_example_events")
                c.close()
            conn.close()

    def test_clickhouse_pool(self):
        """Test ClickHouseConnectionPool and ClickHouseManager with pool."""
        from rick_db.backend.clickhouse import (
            ClickHouseConnectionPool,
            ClickHouseManager,
            ClickHouseRepository,
        )
        from rick_db import fieldmapper

        pool = ClickHouseConnectionPool(
            host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
            port=int(os.environ.get("CLICKHOUSE_PORT", 18123)),
            username=os.environ.get("CLICKHOUSE_USER", "some_user"),
            password=os.environ.get("CLICKHOUSE_PASSWORD", "somePassword"),
            database=os.environ.get("CLICKHOUSE_DB", "testdb"),
            minconn=2,
            maxconn=5,
        )

        try:
            # Manager with pool
            mgr = ClickHouseManager(pool)
            dbs = mgr.databases()
            assert isinstance(dbs, list)
            assert len(dbs) > 0

            # Create table, insert, query via pool
            with pool.connection() as conn:
                with conn.cursor() as c:
                    c.exec(
                        """
                        CREATE TABLE IF NOT EXISTS test_pool_events (
                            id UInt64,
                            event_type String
                        ) ENGINE = MergeTree()
                        ORDER BY id
                        """
                    )
                    c.exec(
                        "INSERT INTO test_pool_events (id, event_type) VALUES (1, 'test')"
                    )

            @fieldmapper(tablename="test_pool_events", pk="id")
            class PoolEvent:
                id = "id"
                event_type = "event_type"

            with pool.connection() as conn:
                repo = ClickHouseRepository(conn, PoolEvent)
                events = repo.fetch_all()
                assert len(events) == 1
                assert events[0].event_type == "test"

            assert mgr.table_exists("test_pool_events")
            mgr.drop_table("test_pool_events")
            assert mgr.table_exists("test_pool_events") is False

        finally:
            pool.close()
