import pytest
from rick_db.backend.sqlite import Sqlite3Connection
from .base_repository import BaseRepositoryTest

create_table = """
    create table if not exists users(
    id_user integer primary key autoincrement,
    name text default '',
    email text default '',
    login text default null,
    active boolean default true
    );
    """
insert_table = "insert into users(name, email, login, active) values(?,?,?,?)"


class TestSqlite3Repository(BaseRepositoryTest):

    @pytest.fixture
    def conn(self, fixture_users: list):
        conn = Sqlite3Connection("file::memory:?cache=shared")

        # setup
        with conn.cursor() as c:
            c.exec(create_table)
            for r in fixture_users:
                c.exec(insert_table, list(r.values()))

        yield conn

        # teardown
        conn.close()
