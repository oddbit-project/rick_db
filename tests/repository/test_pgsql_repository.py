import pytest
from psycopg2.errors import UniqueViolation

from rick_db import Repository
from rick_db.backend.pg import PgConnection, PgConnectionPool
from .base_repository import BaseRepositoryTest, User

create_table = """
    create table if not exists users(
    id_user serial primary key,
    name text default '',
    email text not null unique default '',
    login text default null,
    active boolean default true
    );
    """
insert_table = "insert into users(name, email, login, active) values(%s,%s,%s,%s)"
drop_table = "drop table if exists users"


def _setup_users(cursor, fixture_users):
    cursor.exec(drop_table)
    cursor.exec(create_table)
    for r in fixture_users:
        cursor.exec(insert_table, list(r.values()))


def _teardown_users(cursor):
    cursor.exec(drop_table)


class TestPgConnRepository(BaseRepositoryTest):

    @pytest.fixture
    def conn(self, pg_settings: dict, fixture_users: list):
        conn = PgConnection(**pg_settings)
        # setup
        with conn.cursor() as c:
            _setup_users(c, fixture_users)

        yield conn

        # teardown
        with conn.cursor() as c:
            _teardown_users(c)
        conn.close()

    def test_exceptions(self, conn):
        repo = Repository(conn, User)
        result = repo.insert_pk(User(name="John", email="john.connor@skynet"))
        assert result is not None
        assert result > 0

        with pytest.raises(UniqueViolation):
            _ = repo.insert_pk(User(name="John", email="john.connor@skynet"))


class TestPgPoolRepository(BaseRepositoryTest):

    @pytest.fixture
    def conn(self, pg_settings: dict, fixture_users: list):
        pool = PgConnectionPool(**pg_settings)
        # setup
        with pool.connection() as db:
            with db.cursor() as c:
                _setup_users(c, fixture_users)

        yield pool

        # teardown
        with pool.connection() as conn:
            with conn.cursor() as c:
                _teardown_users(c)
        pool.close()
