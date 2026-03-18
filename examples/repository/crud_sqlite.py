"""
Basic CRUD operations with SQLite (no external dependencies required).

Demonstrates:
 - Sqlite3Connection with in-memory database
 - fieldmapper record definitions
 - Repository insert, fetch, update, delete
 - fetch_where with conditions
"""
from rick_db import fieldmapper, Repository
from rick_db.backend.sqlite import Sqlite3Connection


@fieldmapper(tablename="users", pk="id_user")
class User:
    id = "id_user"
    name = "name"
    email = "email"
    active = "active"


def create_schema(conn):
    with conn.cursor() as c:
        c.exec(
            """
            CREATE TABLE users (
                id_user INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
            """
        )
        c.close()


def main():
    conn = Sqlite3Connection(":memory:")
    create_schema(conn)
    repo = Repository(conn, User)

    # Insert
    alice_id = repo.insert_pk(User(name="Alice", email="alice@example.com", active=1))
    bob_id = repo.insert_pk(User(name="Bob", email="bob@example.com", active=1))
    charlie_id = repo.insert_pk(User(name="Charlie", email="charlie@example.com", active=0))
    print("Inserted Alice (id={}), Bob (id={}), Charlie (id={})".format(alice_id, bob_id, charlie_id))

    # Fetch all
    print("\nAll users:")
    for user in repo.fetch_all():
        print("  {} - {} ({})".format(user.id, user.name, user.email))

    # Fetch by primary key
    alice = repo.fetch_pk(alice_id)
    print("\nFetched by pk: {} - {}".format(alice.name, alice.email))

    # Fetch with conditions
    active_users = repo.fetch_where([("active", "=", 1)])
    print("\nActive users:")
    for user in active_users:
        print("  {} - {}".format(user.name, user.email))

    # Update
    alice.name = "Alice Updated"
    repo.update(alice)
    alice = repo.fetch_pk(alice_id)
    print("\nAfter update: {} - {}".format(alice.name, alice.email))

    # Delete
    repo.delete_pk(charlie_id)
    print("\nAfter deleting Charlie:")
    for user in repo.fetch_all():
        print("  {} - {}".format(user.name, user.email))

    conn.close()


if __name__ == "__main__":
    main()
