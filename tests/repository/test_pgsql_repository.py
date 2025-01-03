import pytest

from rick_db.backend.pg import PgConnection, PgConnectionPool
from .base_repository import BaseRepositoryTest

create_table = """
    create table if not exists users(
    id_user serial primary key,
    name text default '',
    email text default '',
    login text default null,
    active boolean default true
    );
    """
insert_table = "insert into users(name, email, login, active) values(%s,%s,%s,%s)"
drop_table = "drop table if exists users"


class TestPgConnRepository(BaseRepositoryTest):

    @pytest.fixture
    def conn(self, pg_settings: dict, fixture_users: list):
        conn = PgConnection(**pg_settings)
        # setup
        with conn.cursor() as c:
            c.exec(drop_table)
            c.exec(create_table)
            for r in fixture_users:
                c.exec(insert_table, list(r.values()))

        yield conn

        # teardown
        with conn.cursor() as c:
            c.exec(drop_table)
        conn.close()


class TestPgPoolRepository(BaseRepositoryTest):

    @pytest.fixture
    def conn(self, pg_settings: dict, fixture_users: list):
        pool = PgConnectionPool(**pg_settings)
        # setup
        with pool.connection() as db:
            with db.cursor() as c:
                c.exec(drop_table)
                c.exec(create_table)
                for r in fixture_users:
                    c.exec(insert_table, list(r.values()))

        yield pool

        # teardown
        with pool.connection() as conn:
            with conn.cursor() as c:
                c.exec(drop_table)
        pool.close()
