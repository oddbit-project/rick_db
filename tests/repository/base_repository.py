from dataclasses import dataclass

import pytest
from rick_db import fieldmapper, Repository, RepositoryError


@fieldmapper(tablename="users", pk="id_user")
class User:
    id = "id_user"
    name = "name"
    email = "email"
    login = "login"
    active = "active"


@fieldmapper
class UserName:
    name = "name"


@dataclass
class UserDataclass:
    name: str
    email: str


class BaseRepositoryTest:

    @pytest.fixture
    def conn(self):
        return None

    def test_create_repository(self, conn):
        repo = Repository(conn, User)
        assert repo.pk == "id_user"
        assert repo.table_name == "users"

    def test_fetchall(self, conn, fixture_users):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert type(users) is list
        assert len(users) == len(fixture_users)
        for r in users:
            assert isinstance(r, User)
            assert r.id is not None and type(r.id) is int
            assert r.name is not None and type(r.name) is str and len(r.name) > 0
            assert r.email is not None and type(r.email) is str and len(r.email) > 0
            assert r.active is not None
            assert type(r.active) in (bool, int)

    def test_fetchall_ordered(self, conn, fixture_users):
        repo = Repository(conn, User)
        users = repo.fetch_all_ordered(User.email)
        assert type(users) is list
        assert len(users) == len(fixture_users)
        expected_list = []
        for e in fixture_users:
            expected_list.append(e["email"])
        expected_list.sort()

        i = 0
        for r in users:
            assert isinstance(r, User)
            assert r.id is not None and type(r.id) is int
            assert r.name is not None and type(r.name) is str and len(r.name) > 0
            assert r.email is not None and type(r.email) is str and len(r.email) > 0
            assert r.email == expected_list[i]
            i = i + 1
            assert r.active is not None
            assert type(r.active) in (bool, int)

    def test_fetch_pk(self, conn, fixture_users):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == len(fixture_users)
        for u in users:
            record = repo.fetch_pk(u.id)
            assert record is not None
            assert record.asdict() == u.asdict()

        record = repo.fetch_pk(-1)
        assert record is None

    def test_fetch_one(self, conn, fixture_users):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == len(fixture_users)
        for u in users:
            record = repo.fetch_one(repo.select().where(User.id, "=", u.id))
            assert record is not None
            assert record.asdict() == u.asdict()

        # if not found, returns None
        record = repo.fetch_one(repo.select().where(User.id, "=", -1))
        assert record is None

    def test_fetch(self, conn, fixture_users):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == len(fixture_users)
        ids = []
        names = []
        for u in users:
            ids.append(u.id)
            names.append(u.name)

        users = repo.fetch(repo.select().where(User.id, ">", -1))
        assert users is not None
        assert len(users) == len(ids)
        for u in users:
            assert u.id in ids

        # test empty result query
        users = repo.fetch(repo.select().where(User.id, "=", -1))
        assert type(users) is list
        assert len(users) == 0

        # test different record class
        users = repo.fetch(repo.select().where(User.id, ">", -1), cls=UserName)
        assert users is not None
        assert len(users) == len(ids)
        for u in users:
            assert isinstance(u, UserName)
            assert u.name in names

    def test_fetch_raw(self, conn, fixture_users):
        repo = Repository(conn, User)
        users = repo.fetch_raw(repo.select().where(User.id, ">", 0))
        assert len(users) == len(fixture_users)
        for u in users:
            assert len(u["name"]) > 0

    def test_fetch_by_field(self, conn, fixture_users):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == len(fixture_users)
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
            assert record["name"] == u.name

        # fetch non-existing record
        records = repo.fetch_by_field(User.id, -1)
        assert len(records) == 0

    def test_fetch_where(self, conn):
        repo = Repository(conn, User)
        # fetch with one condition
        records = repo.fetch_where([(User.name, "=", "gandalf")])
        assert len(records) == 1
        record = records.pop()
        assert record.name == "gandalf"

        # fetch with 2 conditions
        records = repo.fetch_where(
            [(User.name, "=", "gandalf"), (User.id, "is not null", None)]
        )
        assert len(records) == 1
        record = records.pop()
        assert record.name == "gandalf"

        # fetch only some columns
        records = repo.fetch_where(
            [(User.name, "=", "gandalf")], cols=[User.id, User.name]
        )
        record = records.pop()
        assert record.name == "gandalf"
        assert record.id > 0
        assert len(record.asdict()) == 2

        # fetch non-existing record
        records = repo.fetch_where([(User.name, "like", "%john%")])
        assert len(records) == 0

        # incomplete
        with pytest.raises(RepositoryError):
            repo.fetch_where([(User.name, "like")])

        # wrong type
        with pytest.raises(RepositoryError):
            repo.fetch_where([({}, "like")])

        # empty where_list
        with pytest.raises(RepositoryError):
            repo.fetch_where([])

    def test_fetch_where_in(self, conn):
        repo = Repository(conn, User)
        # fetch with IN clause
        records = repo.fetch_where([(User.name, "in", ["gandalf", "bilbo"])])
        assert len(records) == 2
        names = {r.name for r in records}
        assert names == {"gandalf", "bilbo"}

        # fetch with NOT IN clause
        records = repo.fetch_where(
            [(User.name, "not in", ["gandalf", "bilbo", "gollum"])]
        )
        assert len(records) == 2
        names = {r.name for r in records}
        assert names == {"aragorn", "samwise"}

        # IN with single value
        records = repo.fetch_where([(User.name, "in", ["aragorn"])])
        assert len(records) == 1
        assert records[0].name == "aragorn"

        # IN combined with other conditions
        records = repo.fetch_where(
            [(User.name, "in", ["gandalf", "bilbo", "aragorn"]), (User.login, "=", "gandalf")]
        )
        assert len(records) == 1
        assert records[0].name == "gandalf"

    def test_fetch_one_cls(self, conn, fixture_users):
        repo = Repository(conn, User)
        # with fieldmapper class
        record = repo.fetch_one(
            repo.select(cols=[User.name, User.email]).where(User.name, "=", "gandalf"),
            cls=UserName,
        )
        assert isinstance(record, UserName)
        assert record.name == "gandalf"

        # with dataclass
        record = repo.fetch_one(
            repo.select(cols=[User.name, User.email]).where(User.name, "=", "gandalf"),
            cls=UserDataclass,
        )
        assert isinstance(record, UserDataclass)
        assert record.name == "gandalf"
        assert record.email is not None

    def test_fetch_by_field_cls(self, conn, fixture_users):
        repo = Repository(conn, User)
        # with fieldmapper class
        records = repo.fetch_by_field(User.name, "gandalf", cols=[User.name], cls=UserName)
        assert len(records) == 1
        assert isinstance(records[0], UserName)
        assert records[0].name == "gandalf"

        # with dataclass
        records = repo.fetch_by_field(
            User.name, "gandalf", cols=[User.name, User.email], cls=UserDataclass
        )
        assert len(records) == 1
        assert isinstance(records[0], UserDataclass)
        assert records[0].name == "gandalf"

    def test_fetch_where_cls(self, conn, fixture_users):
        repo = Repository(conn, User)
        # with fieldmapper class
        records = repo.fetch_where(
            [(User.name, "=", "gandalf")], cols=[User.name], cls=UserName
        )
        assert len(records) == 1
        assert isinstance(records[0], UserName)
        assert records[0].name == "gandalf"

        # with dataclass
        records = repo.fetch_where(
            [(User.name, "=", "gandalf")], cols=[User.name, User.email], cls=UserDataclass
        )
        assert len(records) == 1
        assert isinstance(records[0], UserDataclass)
        assert records[0].name == "gandalf"

    def test_fetch_all_cls(self, conn, fixture_users):
        repo = Repository(conn, User)
        # with fieldmapper class
        records = repo.fetch_all(cls=UserName)
        assert len(records) == len(fixture_users)
        for r in records:
            assert isinstance(r, UserName)
            assert r.name is not None

        # with dataclass - need to select only matching columns
        # fetch_all uses cached query (SELECT *), so dataclass must accept all columns
        # Instead, use fetch() which is more flexible
        # This test verifies fetch_all works with fieldmapper cls

    def test_fetch_all_ordered_cls(self, conn, fixture_users):
        repo = Repository(conn, User)
        # with fieldmapper class
        records = repo.fetch_all_ordered(User.name, cls=UserName)
        assert len(records) == len(fixture_users)
        for r in records:
            assert isinstance(r, UserName)
        # verify ordering
        names = [r.name for r in records]
        assert names == sorted(names)

    def test_insert(self, conn):
        repo = Repository(conn, User)
        result = repo.insert(User(name="John", email="john.connor@skynet"))
        assert result is None

        # try to read inserted record
        records = repo.fetch_by_field(User.name, "John")
        assert len(records) == 1
        record = records.pop()
        assert record.name == "John"
        assert record.email == "john.connor@skynet"
        assert record.login is None

        # note: sqlite does not support returning multiple columns
        # it will always return a record with the inserted primary key
        result = repo.insert(
            User(name="Sarah", email="sarah.connor@skynet"), cols=[User.id]
        )
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
        repo.delete_where([(User.id, "=", result), (User.name, "=", "John")])
        record = repo.fetch_pk(result)
        assert record is not None
        assert record.id == result

        # proper delete
        repo.delete_where([(User.id, "=", result), (User.name, "=", "Sarah")])
        record = repo.fetch_pk(result)
        assert record is None

    def test_map_result_id(self, conn, fixture_users):
        repo = Repository(conn, User)
        users = repo.map_result_id(repo.fetch_all())
        assert len(users) == len(fixture_users)
        for id, record in users.items():
            assert id == record.id

    def test_valid_pk(self, conn, fixture_users):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert type(users) is list
        assert len(users) == len(fixture_users)
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

        record = User(name="John", email="john.connor@skynet")
        record = repo.insert(record, cols=[User.id])
        assert isinstance(record, User) is True
        id = record.id

        # read inserted record
        record = repo.fetch_pk(id)
        # simple update - pk is in the record
        record.name = "Sarah"
        repo.update(record)
        record = repo.fetch_pk(id)
        assert record.name == "Sarah"
        assert record.email == "john.connor@skynet"

        # try to update without pk
        with pytest.raises(RepositoryError):
            repo.update(User(name="John"))
        # correct update procedure
        repo.update(User(name="John"), pk_value=id)
        record = repo.fetch_pk(id)
        assert record.name == "John"
        assert record.email == "john.connor@skynet"

    def test_update_where(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        u = users.pop()  # lets just use the last entry

        # test exception on empty where clauses
        with pytest.raises(RepositoryError):
            repo.update_where(User(name="Pocoyo"), [])
        with pytest.raises(RepositoryError):
            repo.update_where(User(name="Pocoyo"), [()])

        repo.update_where(User(name="Pocoyo"), [(User.login, "=", u.login)])
        record = repo.fetch_pk(u.id)
        assert record.name == "Pocoyo"
        assert record.login == u.login

    def test_count(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == repo.count()

    def test_count_where(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()
        assert len(users) == repo.count_where([(User.id, ">", 0)])

        assert repo.count_where([(User.name, "bilbo")]) == 1
        assert repo.count_where([(User.name, "John")]) == 0

    def test_list(self, conn):
        repo = Repository(conn, User)
        users = repo.fetch_all()

        qry = repo.select().order(User.id)
        total, rows = repo.list(qry, 1)
        assert total == len(users)
        assert len(rows) == 1
        assert rows[0].name == "aragorn"

        total, rows = repo.list(qry, 1, 1)
        assert total == len(users)
        assert len(rows) == 1
        assert rows[0].name == "bilbo"

        qry = repo.select().order(User.id)
        total, rows = repo.list(qry, 2, 2)
        assert total == len(users)
        assert len(rows) == 2
        assert rows[0].name == "samwise"
        assert rows[1].name == "gandalf"

    def test_transaction(self, conn):
        repo = Repository(conn, User)

        # start transaction
        repo.begin()
        with pytest.raises(RepositoryError):
            repo.begin()
        result = repo.insert_pk(User(name="Sarah", email="sarah.connor@skynet"))
        assert isinstance(result, int)
        assert result > 0
        record = repo.fetch_pk(result)
        assert record.name == "Sarah"
        # rollback
        repo.rollback()

        with pytest.raises(RepositoryError):
            repo.commit()
        with pytest.raises(RepositoryError):
            repo.rollback()

        # start other transaction
        # this should commit successfully
        with repo.transaction():
            result = repo.insert_pk(User(name="Sarah", email="sarah.connor@skynet"))
            assert isinstance(result, int)
            assert result > 0
            record = repo.fetch_pk(result)
            assert record.name == "Sarah"

    def test_transaction_context_manager(self, conn):
        repo = Repository(conn, User)

        # Insert a user using transaction context manager
        with repo.transaction():
            result = repo.insert_pk(User(name="John", email="john.connor@skynet"))
            assert isinstance(result, int)
            assert result > 0
            record = repo.fetch_pk(result)
            assert record.name == "John"

        # Record should still exist after transaction completes successfully
        record = repo.fetch_pk(result)
        assert record is not None
        assert record.name == "John"

        # Test that changes are rolled back on exception
        with pytest.raises(ValueError):
            with repo.transaction():
                result2 = repo.insert_pk(User(name="Kyle", email="kyle.reese@skynet"))
                assert isinstance(result2, int)
                assert result2 > 0
                record2 = repo.fetch_pk(result2)
                assert record2.name == "Kyle"
                raise ValueError("Intentional error to trigger rollback")

        # Record should not exist after transaction rolls back
        record2 = repo.fetch_pk(result2)
        assert record2 is None

    def test_nested_transaction_context_manager(self, conn):
        """Test that nested transaction context managers work correctly"""
        repo = Repository(conn, User)

        # Test nested transactions with successful commit
        with repo.transaction():
            # Outer transaction
            result1 = repo.insert_pk(User(name="Alice", email="alice@example.com"))
            with repo.transaction():
                # Inner transaction
                result2 = repo.insert_pk(User(name="Bob", email="bob@example.com"))

        # Both records should exist after nested transactions complete
        record1 = repo.fetch_pk(result1)
        record2 = repo.fetch_pk(result2)
        assert record1 is not None
        assert record2 is not None
        assert record1.name == "Alice"
        assert record2.name == "Bob"

        # Test that error in inner transaction rolls back everything
        try:
            with repo.transaction():
                # Outer transaction
                result3 = repo.insert_pk(
                    User(name="Charlie", email="charlie@example.com")
                )
                try:
                    with repo.transaction():
                        # Inner transaction
                        result4 = repo.insert_pk(
                            User(name="Dave", email="dave@example.com")
                        )
                        raise ValueError("Inner transaction error")
                except ValueError:
                    pass
                # This should not execute (outer transaction should have rolled back)
                record4 = repo.fetch_pk(result4)
                assert record4 is None
        except Exception:
            pass

        # Neither record should exist - both transactions should have been rolled back
        record3 = repo.fetch_pk(result3)
        record4 = repo.fetch_pk(result4)
        assert record3 is None
        assert record4 is None

        with pytest.raises(RepositoryError):
            repo.commit()
        with pytest.raises(RepositoryError):
            repo.rollback()
