import os

import pytest
from rick_db.conn.sqlite import Sqlite3Connection
from rick_db import fieldmapper, Repository, RepositoryError
from rick_db.profiler import NullProfiler
from rick_db.sql import Sqlite3SqlDialect

dbfile = '/tmp/rick_db_sqlite_test.db'


@fieldmapper(tablename='users', pk='id_user')
class User:
    id = 'id_user'
    name = 'name'
    email = 'email'
    login = 'login'
    active = 'active'


rows_users = [
    {
        'name': 'aragorn',
        'email': 'aragorn@lotr',
        'login': 'aragorn',
        'active': True,
    },
    {
        'name': 'bilbo',
        'email': 'bilbo@lotr',
        'login': 'bilbo',
        'active': True,
    },
    {
        'name': 'samwise',
        'email': 'samwise@lotr',
        'login': 'samwise',
        'active': True,
    },
    {
        'name': 'gandalf',
        'email': 'gandalf@lotr',
        'login': 'gandalf',
        'active': True,
    },
    {
        'name': 'gollum',
        'email': 'gollum@lotr',
        'login': 'gollum',
        'active': True,
    },

]


class TestSqlite3Connection:
    createTable = """
        create table if not exists users(
        id_user integer primary key autoincrement,
        name text default '',
        email text default '',
        login text default null,
        active boolean default true
        );
        """
    insertTable = "insert into users(name, email, login, active) values(?,?,?,?)"

    def setup_method(self, test_method):
        self.conn = Sqlite3Connection(dbfile)
        with self.conn.cursor() as c:
            c.exec(self.createTable)
            for r in rows_users:
                c.exec(self.insertTable, list(r.values()))

    def teardown_method(self, test_method):
        self.conn.close()
        os.unlink(dbfile)

    @pytest.fixture()
    def conn(self):
        return self.conn

    def test_create_repository(self, conn):
        repo = Repository(conn, User)
        assert repo._pk == 'id_user'
        assert repo._tablename == 'users'

    def test_fetchall(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert type(users) is list
        assert len(users) == len(rows_users)
        for r in users:
            assert isinstance(r, User)
            assert r.id is not None and type(r.id) is int
            assert r.name is not None and type(r.name) is str and len(r.name) > 0
            assert r.email is not None and type(r.email) is str and len(r.email) > 0
            assert r.active is not None and type(r.active) is int  # bools are mapped as ints

    def test_fetch_pk(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == len(rows_users)
        for u in users:
            record = repo.fetch_pk(u.id)
            assert record is not None
            assert record.asdict() == u.asdict()

        record = repo.fetch_pk(-1)
        assert record is None

    def test_fetch_one(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == len(rows_users)
        for u in users:
            record = repo.fetch_one(repo.select().where(User.id, '=', u.id))
            assert record is not None
            assert record.asdict() == u.asdict()

        # if not found, returns None
        record = repo.fetch_one(repo.select().where(User.id, '=', -1))
        assert record is None

    def test_fetch(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == len(rows_users)
        ids = []
        for u in users:
            ids.append(u.id)

        users = repo.fetch(repo.select().where(User.id, '>', -1))
        assert users is not None
        assert len(users) == len(ids)
        for u in users:
            assert u.id in ids

        # test empty result query
        users = repo.fetch(repo.select().where(User.id, '=', -1))
        assert type(users) is list
        assert len(users) == 0

    def test_fetch_by_field(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == len(rows_users)
        for u in users:
            # fetch all columns
            records = repo.fetch_by_field(User.id, u.id)
            assert len(records) == 1
            assert records.pop().asdict() == u.asdict()

            # fetch single column
            records = repo.fetch_by_field(User.id, u.id, cols=[User.name])
            assert len(records) == 1
            record = records.pop().asdict()
            assert len(record) == 1
            assert record['name'] == u.name

        # fetch non-existing record
        records = repo.fetch_by_field(User.id, -1)
        assert len(records) == 0

    def test_fetch_where(self, conn):
        repo = Repository(conn, User)
        # fetch with one condition
        records = repo.fetch_where([(User.name, '=', 'gandalf')])
        assert len(records) == 1
        record = records.pop()
        assert record.name == 'gandalf'

        # fetch with 2 conditions
        records = repo.fetch_where([(User.name, '=', 'gandalf'), (User.id,'is not null', None)])
        assert len(records) == 1
        record = records.pop()
        assert record.name == 'gandalf'

        # fetch only some columns
        records = repo.fetch_where([(User.name, '=', 'gandalf')], cols=[User.id, User.name])
        record = records.pop()
        assert record.name == 'gandalf'
        assert record.id > 0
        assert len(record.asdict()) == 2

        # fetch non-existing record
        records = repo.fetch_where([(User.name, 'like', '%john%')])
        assert len(records) == 0

        # incomplete
        with pytest.raises(RepositoryError):
            repo.fetch_where([(User.name, 'like')])

        # wrong type
        with pytest.raises(RepositoryError):
            repo.fetch_where([({}, 'like')])

        # empty where_list
        with pytest.raises(RepositoryError):
            repo.fetch_where([])

    def test_insert(self, conn):
        repo = Repository(conn, User)
        result = repo.insert(User(name="John", email="john.connor@skynet"))
        assert result is None

        # try to read inserted record
        records = repo.fetch_by_field(User.name, 'John')
        assert len(records) == 1
        record = records.pop()
        assert record.name == 'John'
        assert record.email == 'john.connor@skynet'
        assert record.login is None

        # note: sqlite does not support returning multiple columns
        # it will always return a record with the inserted primary key
        result = repo.insert(User(name="Sarah", email="sarah.connor@skynet"), cols=[User.id])
        assert isinstance(result, User)
        assert result.id > 0
        record = repo.fetch_pk(result.id)
        assert record.name == "Sarah"

    def test_insert_pk(self, conn):
        repo = Repository(conn, User)
        result = repo.insert_pk(User(name="Sarah", email="sarah.connor@skynet"))
        assert isinstance(result, User)
        assert result.id > 0
        record = repo.fetch_pk(result.id)
        assert record.name == "Sarah"


    def test_delete_pk(self, conn):
        repo = Repository(conn, User)
        result = repo.insert_pk(User(name="Sarah", email="sarah.connor@skynet"))
        assert isinstance(result, User)
        assert result.id > 0
        record = repo.fetch_pk(result.id)
        assert record.name == "Sarah"

        repo.delete_pk(result.id)
        record = repo.fetch_pk(result.id)
        assert record is None

    def test_delete_where(self, conn):
        repo = Repository(conn, User)
        result = repo.insert_pk(User(name="Sarah", email="sarah.connor@skynet"))
        assert isinstance(result, User)
        assert result.id > 0
        record = repo.fetch_pk(result.id)
        assert record.name == "Sarah"

        # failed delete, as where doesn't match
        repo.delete_where([(User.id, '=', result.id), (User.name,'=', 'John')])
        record = repo.fetch_pk(result.id)
        assert record is not None
        assert record.id == result.id

        # proper delete
        repo.delete_where([(User.id, '=', result.id), (User.name,'=', 'Sarah')])
        record = repo.fetch_pk(result.id)
        assert record is None

    def test_map_result_id(self, conn):
        repo = Repository(conn, User)
        users = repo.map_result_id(repo.fetch_all())
        assert len(users) == len(rows_users)
        for id, record in users.items():
            assert id == record.id
