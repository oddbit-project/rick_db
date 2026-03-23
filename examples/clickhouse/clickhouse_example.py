"""
ClickHouse connection, repository, and introspection example.

Demonstrates:
 - ClickHouseConnection and ClickHouseConnectionPool setup
 - ClickHouseManager for schema introspection (with connection and pool)
 - Repository usage with ClickHouse
 - Query builder with ClickHouseSqlDialect

Requirements:
 - A running ClickHouse server (default: localhost:8123)
 - pip install clickhouse-connect
"""
from rick_db import fieldmapper, Repository
from rick_db.backend.clickhouse import (
    ClickHouseConnection,
    ClickHouseConnectionPool,
    ClickHouseManager,
    ClickHouseRepository,
)
from rick_db.sql import Select, Fn


@fieldmapper(tablename="events", pk="id")
class Event:
    id = "id"
    event_type = "event_type"
    user_id = "user_id"
    amount = "amount"
    created_at = "created_at"


# -- Connection setup --

db_cfg = {
    "host": "localhost",
    "port": 8123,
    "database": "default",
    "username": "default",
    "password": "",
}


def create_schema(conn):
    """Create the example table using raw SQL."""
    with conn.cursor() as c:
        c.exec(
            """
            CREATE TABLE IF NOT EXISTS events (
                id UInt64,
                event_type String,
                user_id UInt32,
                amount Float64,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (id, created_at)
            """
        )
        c.close()


def seed_data(conn):
    """Insert sample data."""
    with conn.cursor() as c:
        c.exec(
            """
            INSERT INTO events (id, event_type, user_id, amount) VALUES
                (1, 'purchase', 101, 29.99),
                (2, 'purchase', 102, 149.50),
                (3, 'refund', 101, 29.99),
                (4, 'purchase', 103, 75.00),
                (5, 'purchase', 101, 50.00),
                (6, 'purchase', 102, 200.00),
                (7, 'refund', 103, 75.00),
                (8, 'purchase', 104, 99.99)
            """
        )
        c.close()


def introspect(conn):
    """Database introspection with ClickHouseManager."""
    mgr = ClickHouseManager(conn)

    print("=== Introspection ===")
    print("Databases:", mgr.databases())
    print("Tables:", mgr.tables())

    if mgr.table_exists("events"):
        print("\nFields in 'events':")
        for f in mgr.table_fields("events"):
            print("  {} ({})".format(f.field, f.type))

        pk = mgr.table_pk("events")
        if pk:
            print("Primary key:", pk.field)


def query_examples(conn):
    """Query builder examples with ClickHouse dialect."""
    repo = Repository(conn, Event)
    dialect = conn.dialect()

    # Fetch all events
    print("\n=== All events ===")
    for event in repo.fetch_all():
        print(
            "  id={} type={} user={} amount={}".format(
                event.id, event.event_type, event.user_id, event.amount
            )
        )

    # Fetch with WHERE
    print("\n=== Purchases only ===")
    purchases = repo.fetch_where([("event_type", "=", "purchase")])
    for event in purchases:
        print("  user={} amount={}".format(event.user_id, event.amount))

    # Aggregation query using query builder
    qry = (
        Select(dialect)
        .from_(
            Event,
            {
                Event.event_type: None,
                Fn.count(): "cnt",
                Fn.sum(Event.amount): "total",
                Fn.round(Fn.avg(Event.amount), 2): "avg_amount",
            },
        )
        .group(Event.event_type)
    )
    print("\n=== Aggregation by event type ===")
    sql, values = qry.assemble()
    print("SQL:", sql)
    with conn.cursor() as c:
        for row in c.fetchall(sql, values):
            print("  {}".format(row))

    # Per-user purchase totals
    qry = (
        Select(dialect)
        .from_(
            Event,
            {
                Event.user_id: None,
                Fn.sum(Event.amount): "total_spent",
                Fn.count(): "num_purchases",
            },
        )
        .where(Event.event_type, "=", "purchase")
        .group(Event.user_id)
    )
    print("\n=== Per-user purchase totals ===")
    sql, values = qry.assemble()
    with conn.cursor() as c:
        for row in c.fetchall(sql, values):
            print("  {}".format(row))


def cleanup(conn):
    with conn.cursor() as c:
        c.exec("DROP TABLE IF EXISTS events")
        c.close()


def pool_examples():
    """Connection pool usage with ClickHouseConnectionPool."""
    pool = ClickHouseConnectionPool(**db_cfg, minconn=2, maxconn=10)

    print("\n=== Connection Pool ===")

    # Manager works with pool directly
    mgr = ClickHouseManager(pool)
    print("Tables via pool:", mgr.tables())

    # Repository via pool connection
    with pool.connection() as conn:
        repo = ClickHouseRepository(conn, Event)
        events = repo.fetch_all()
        print("Events via pool:", len(events))

    # Multiple connections from pool
    with pool.connection() as conn1:
        with pool.connection() as conn2:
            repo1 = ClickHouseRepository(conn1, Event)
            repo2 = ClickHouseRepository(conn2, Event)
            print("Conn1 count:", repo1.count())
            print("Conn2 count:", repo2.count())

    pool.close()


def main():
    conn = ClickHouseConnection(**db_cfg)

    try:
        create_schema(conn)
        seed_data(conn)
        introspect(conn)
        query_examples(conn)
        pool_examples()
    finally:
        cleanup(conn)
        conn.close()


if __name__ == "__main__":
    main()
