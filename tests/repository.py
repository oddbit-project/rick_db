import pytest
from rick_db import fieldmapper, Repository, RepositoryError
from rick_db.conn.pg import PgConnection
from rick_db.conn.sqlite import Sqlite3Connection


@fieldmapper(tablename='users', pk='id_user')
class User:
    id = 'id_user'
    name = 'name'
    email = 'email'
    login = 'login'
    active = 'active'


@fieldmapper
class UserName:
    name = 'name'


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


class RepositoryTest:

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
            assert r.active is not None
            if isinstance(conn, PgConnection):
                assert type(r.active) is bool
            elif isinstance(conn, Sqlite3Connection):
                assert type(r.active) is int

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
        names = []
        for u in users:
            ids.append(u.id)
            names.append(u.name)

        users = repo.fetch(repo.select().where(User.id, '>', -1))
        assert users is not None
        assert len(users) == len(ids)
        for u in users:
            assert u.id in ids

        # test empty result query
        users = repo.fetch(repo.select().where(User.id, '=', -1))
        assert type(users) is list
        assert len(users) == 0

        # test different record class
        users = repo.fetch(repo.select().where(User.id, '>', -1), cls=UserName)
        assert users is not None
        assert len(users) == len(ids)
        for u in users:
            assert isinstance(u, UserName)
            assert u.name in names

    def test_fetch_raw(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_raw(repo.select().where(User.id, '>', 0))
        assert len(users) == len(rows_users)
        for u in users:
            assert len(u['name']) > 0

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
        records = repo.fetch_where([(User.name, '=', 'gandalf'), (User.id, 'is not null', None)])
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
        assert isinstance(result, int)
        assert result > 0
        record = repo.fetch_pk(result)
        assert record.name == "Sarah"

    def test_delete_pk(self, conn):
        repo = Repository(conn, User)
        result = repo.insert_pk(User(name="Sarah", email="sarah.connor@skynet"))
        assert isinstance(result, int)
        assert result > 0
        record = repo.fetch_pk(result)
        assert record.name == "Sarah"

        repo.delete_pk(result)
        record = repo.fetch_pk(result)
        assert record is None

    def test_delete_where(self, conn):
        repo = Repository(conn, User)
        result = repo.insert_pk(User(name="Sarah", email="sarah.connor@skynet"))
        assert isinstance(result, int)
        assert result > 0
        record = repo.fetch_pk(result)
        assert record.name == "Sarah"

        # failed delete, as where doesn't match
        repo.delete_where([(User.id, '=', result), (User.name, '=', 'John')])
        record = repo.fetch_pk(result)
        assert record is not None
        assert record.id == result

        # proper delete
        repo.delete_where([(User.id, '=', result), (User.name, '=', 'Sarah')])
        record = repo.fetch_pk(result)
        assert record is None

    def test_map_result_id(self, conn):
        repo = Repository(conn, User)
        users = repo.map_result_id(repo.fetch_all())
        assert len(users) == len(rows_users)
        for id, record in users.items():
            assert id == record.id

    def test_valid_pk(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert type(users) is list
        assert len(users) == len(rows_users)
        for r in users:
            assert repo.valid_pk(r.id) is True
        assert repo.valid_pk(-1) is False

    def test_exists(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        first = None
        for r in users:
            # existing name with different id is False
            assert repo.exists(User.name, r.name, r.id) is False
            if first is None:
                first = r.name
            else:
                # existing name with another id is True
                assert repo.exists(User.name, first, r.id) is True

    def test_update(self, conn):
        repo = Repository(conn, User)

        record = User(name='John', email='john.connor@skynet')
        record = repo.insert(record, cols=[User.id])
        assert isinstance(record, User) is True
        id = record.id

        # read inserted record
        record = repo.fetch_pk(id)
        # simple update - pk is in the record
        record.name = 'Sarah'
        repo.update(record)
        record = repo.fetch_pk(id)
        assert record.name == 'Sarah'
        assert record.email == 'john.connor@skynet'

        # try to update without pk
        with pytest.raises(RepositoryError):
            repo.update(User(name='John'))
        # correct update procedure
        repo.update(User(name='John'), pk_value=id)
        record = repo.fetch_pk(id)
        assert record.name == 'John'
        assert record.email == 'john.connor@skynet'

    def test_update_where(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        u = users.pop()  # lets just use the last entry

        # test exception on empty where clauses
        with pytest.raises(RepositoryError):
            repo.update_where(User(name='Pocoyo'), [])
        with pytest.raises(RepositoryError):
            repo.update_where(User(name='Pocoyo'), [()])

        repo.update_where(User(name='Pocoyo'), [(User.login, '=', u.login)])
        record = repo.fetch_pk(u.id)
        assert record.name == 'Pocoyo'
        assert record.login == u.login

    def test_count(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == repo.count()

    def test_count_where(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == repo.count_where([(User.id, '>', 0)])

        assert repo.count_where([(User.name, 'bilbo')]) == 1
        assert repo.count_where([(User.name, 'John')]) == 0

    def test_list(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()

        qry = repo.select().order(User.id)
        total, rows = repo.list(qry, 1)
        assert total == len(users)
        assert len(rows) == 1
        assert rows[0].name == 'aragorn'

        total, rows = repo.list(qry, 1, 1)
        assert total == len(users)
        assert len(rows) == 1
        assert rows[0].name == 'bilbo'

        qry = repo.select().order(User.id)
        total, rows = repo.list(qry, 2, 2)
        assert total == len(users)
        assert len(rows) == 2
        assert rows[0].name == 'samwise'
        assert rows[1].name == 'gandalf'
