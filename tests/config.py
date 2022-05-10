import os

from rick_db.conn.pg import PgConnection


def connectSimple() -> PgConnection:
    return PgConnection(**postgres_db)


postgres_db = {
    'dbname': os.getenv('POSTGRES_DB', 'testdb'),
    'user': os.getenv('POSTGRES_USER', 'some_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'somePassword'),
    'host': os.getenv('PG_DB_HOST', ''),
    'port': os.getenv('POSTGRES_PORT', 5432),
}
