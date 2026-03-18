"""
Programmatic migration workflow using SQLite (no external dependencies).

Demonstrates:
 - Installing the migration tracking table
 - Executing migrations with SQL content
 - Listing applied migrations
 - Checking migration status
"""
from rick_db import fieldmapper, Repository
from rick_db.backend.sqlite import Sqlite3Connection, Sqlite3Manager, Sqlite3MigrationManager
from rick_db.migrations import MigrationRecord


# SQL content for each migration
MIGRATIONS = [
    (
        "001_create_users",
        """
        CREATE TABLE users (
            id_user INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            active INTEGER DEFAULT 1
        );
        """,
    ),
    (
        "002_create_orders",
        """
        CREATE TABLE orders (
            id_order INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_user INTEGER NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fk_user) REFERENCES users(id_user)
        );
        """,
    ),
    (
        "003_add_user_role",
        """
        ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';
        """,
    ),
]


def run_migrations(conn):
    mgr = Sqlite3Manager(conn)
    mm = Sqlite3MigrationManager(mgr)

    # Install the migration tracking table if not already present
    if not mm.is_installed():
        result = mm.install()
        if result.success:
            print("Migration table installed.")
        else:
            print("Failed to install migration table: {}".format(result.error))
            return

    # Check which migrations are already applied
    applied = {m.name for m in mm.list()}
    print("Already applied: {}".format(applied if applied else "(none)"))

    # Execute pending migrations
    pending = [(name, sql) for name, sql in MIGRATIONS if name not in applied]
    if not pending:
        print("No pending migrations.")
        return

    for name, sql in pending:
        record = MigrationRecord(name=name)
        result = mm.execute(record, sql)
        if result.success:
            print("Applied: {}".format(name))
        else:
            print("Failed: {} - {}".format(name, result.error))
            return

    # List all applied migrations
    print("\nAll applied migrations:")
    for m in mm.list():
        print("  {} (applied: {})".format(m.name, m.applied))


def verify_schema(conn):
    """Verify the migrations worked by checking the schema."""
    mgr = Sqlite3Manager(conn)

    print("\nTables in database:")
    for table in mgr.tables():
        print("  {}".format(table))
        fields = mgr.table_fields(table)
        for f in fields:
            print("    - {} ({})".format(f.field, f.type))


def main():
    conn = Sqlite3Connection(":memory:")

    print("=== Running migrations ===")
    run_migrations(conn)

    print("\n=== Running again (should be idempotent) ===")
    run_migrations(conn)

    verify_schema(conn)

    # Verify by inserting data through the migrated schema
    @fieldmapper(tablename="users", pk="id_user")
    class User:
        id = "id_user"
        name = "name"
        email = "email"

    repo = Repository(conn, User)
    user_id = repo.insert_pk(User(name="Alice", email="alice@example.com"))
    user = repo.fetch_pk(user_id)
    print("\nInserted user via migrated schema: {} - {}".format(user.name, user.email))

    conn.close()


if __name__ == "__main__":
    main()
