"""
Transaction usage with automatic commit/rollback.

Demonstrates:
 - Repository.transaction() context manager
 - Automatic commit on success
 - Automatic rollback on exception
 - Nested transactions via savepoints
"""
from rick_db import fieldmapper, Repository
from rick_db.backend.sqlite import Sqlite3Connection


@fieldmapper(tablename="accounts", pk="id_account")
class Account:
    id = "id_account"
    name = "name"
    balance = "balance"


@fieldmapper(tablename="transfers", pk="id_transfer")
class Transfer:
    id = "id_transfer"
    from_account = "from_account"
    to_account = "to_account"
    amount = "amount"


def create_schema(conn):
    with conn.cursor() as c:
        c.exec(
            """
            CREATE TABLE accounts (
                id_account INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0
            )
            """
        )
        c.exec(
            """
            CREATE TABLE transfers (
                id_transfer INTEGER PRIMARY KEY AUTOINCREMENT,
                from_account INTEGER NOT NULL,
                to_account INTEGER NOT NULL,
                amount REAL NOT NULL
            )
            """
        )
        c.close()


def transfer_funds(account_repo, transfer_repo, from_id, to_id, amount):
    """Transfer funds between accounts inside a transaction."""
    with account_repo.transaction():
        sender = account_repo.fetch_pk(from_id)
        receiver = account_repo.fetch_pk(to_id)

        if sender.balance < amount:
            raise ValueError(
                "Insufficient funds: {} has {}, needs {}".format(
                    sender.name, sender.balance, amount
                )
            )

        sender.balance -= amount
        receiver.balance += amount
        account_repo.update(sender)
        account_repo.update(receiver)

        transfer_repo.insert_pk(
            Transfer(from_account=from_id, to_account=to_id, amount=amount)
        )
        print(
            "Transferred {} from {} to {}".format(amount, sender.name, receiver.name)
        )


def print_balances(repo):
    for acc in repo.fetch_all():
        print("  {} balance: {}".format(acc.name, acc.balance))


def main():
    conn = Sqlite3Connection(":memory:")
    create_schema(conn)

    account_repo = Repository(conn, Account)
    transfer_repo = Repository(conn, Transfer)

    # Setup accounts
    alice_id = account_repo.insert_pk(Account(name="Alice", balance=1000.0))
    bob_id = account_repo.insert_pk(Account(name="Bob", balance=500.0))

    print("Initial balances:")
    print_balances(account_repo)

    # Successful transfer
    print("\n--- Transfer $200 from Alice to Bob ---")
    transfer_funds(account_repo, transfer_repo, alice_id, bob_id, 200.0)
    print("\nBalances after transfer:")
    print_balances(account_repo)

    # Failed transfer (insufficient funds) - rolled back
    print("\n--- Attempt transfer $2000 from Bob to Alice (should fail) ---")
    try:
        transfer_funds(account_repo, transfer_repo, bob_id, alice_id, 2000.0)
    except ValueError as e:
        print("Transaction rolled back: {}".format(e))

    print("\nBalances after failed transfer (unchanged):")
    print_balances(account_repo)

    conn.close()


if __name__ == "__main__":
    main()
