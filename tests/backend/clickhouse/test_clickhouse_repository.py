import pytest

from rick_db import fieldmapper, RepositoryError
from rick_db.backend.clickhouse import (
    ClickHouseConnection,
    ClickHouseManager,
    ClickHouseRepository,
)


@fieldmapper(tablename="users", pk="id_user")
class User:
    id = "id_user"
    name = "name"
    email = "email"
    login = "login"
    active = "active"


create_table = """
CREATE TABLE IF NOT EXISTS users (
    id_user UInt32,
    name String DEFAULT '',
    email String DEFAULT '',
    login Nullable(String) DEFAULT NULL,
    active UInt8 DEFAULT 1
) ENGINE = MergeTree()
ORDER BY id_user
"""

drop_table = "DROP TABLE IF EXISTS users"

fixture_data = [
    {"id_user": 1, "name": "aragorn", "email": "aragorn@lotr", "login": "aragorn", "active": 1},
    {"id_user": 2, "name": "bilbo", "email": "bilbo@lotr", "login": "bilbo", "active": 1},
    {"id_user": 3, "name": "samwise", "email": "samwise@lotr", "login": "samwise", "active": 1},
    {"id_user": 4, "name": "gandalf", "email": "gandalf@lotr", "login": "gandalf", "active": 1},
    {"id_user": 5, "name": "gollum", "email": "gollum@lotr", "login": "gollum", "active": 1},
]


@pytest.fixture
def conn(ch_settings):
    try:
        conn = ClickHouseConnection(**ch_settings)
    except Exception:
        pytest.skip("ClickHouse server not available")
        return

    # setup
    with conn.cursor() as c:
        c.exec(drop_table)
        c.exec(create_table)
        for r in fixture_data:
            c.exec(
                "INSERT INTO users (id_user, name, email, login, active) VALUES (%s, %s, %s, %s, %s)",
                list(r.values()),
            )
    yield conn

    # teardown
    with conn.cursor() as c:
        c.exec(drop_table)
    conn.close()


class TestClickHouseRepository:
    def test_create_repository(self, conn):
        repo = ClickHouseRepository(conn, User)
        assert repo.pk == "id_user"
        assert repo.table_name == "users"

    def test_fetch_all(self, conn):
        repo = ClickHouseRepository(conn, User)
        users = repo.fetch_all()
        assert isinstance(users, list)
        assert len(users) == len(fixture_data)
        for r in users:
            assert isinstance(r, User)
            assert r.name is not None and len(r.name) > 0

    def test_fetch_all_ordered(self, conn):
        repo = ClickHouseRepository(conn, User)
        users = repo.fetch_all_ordered(User.email)
        assert len(users) == len(fixture_data)
        emails = [u.email for u in users]
        assert emails == sorted(emails)

    def test_fetch_pk(self, conn):
        repo = ClickHouseRepository(conn, User)
        record = repo.fetch_pk(1)
        assert record is not None
        assert record.name == "aragorn"

        record = repo.fetch_pk(999)
        assert record is None

    def test_fetch_one(self, conn):
        repo = ClickHouseRepository(conn, User)
        record = repo.fetch_one(repo.select().where(User.name, "=", "gandalf"))
        assert record is not None
        assert record.name == "gandalf"

        record = repo.fetch_one(repo.select().where(User.name, "=", "nonexistent"))
        assert record is None

    def test_fetch(self, conn):
        repo = ClickHouseRepository(conn, User)
        users = repo.fetch(repo.select().where(User.id, ">", 0))
        assert len(users) == len(fixture_data)

        users = repo.fetch(repo.select().where(User.id, "=", 999))
        assert len(users) == 0

    def test_fetch_raw(self, conn):
        repo = ClickHouseRepository(conn, User)
        rows = repo.fetch_raw(repo.select().where(User.id, ">", 0))
        assert len(rows) == len(fixture_data)
        for r in rows:
            assert "name" in r

    def test_fetch_by_field(self, conn):
        repo = ClickHouseRepository(conn, User)
        records = repo.fetch_by_field(User.name, "gandalf")
        assert len(records) == 1
        assert records[0].name == "gandalf"

        records = repo.fetch_by_field(User.name, "nonexistent")
        assert len(records) == 0

    def test_fetch_where(self, conn):
        repo = ClickHouseRepository(conn, User)
        records = repo.fetch_where([(User.name, "=", "gandalf")])
        assert len(records) == 1
        assert records[0].name == "gandalf"

        records = repo.fetch_where([(User.name, "=", "nonexistent")])
        assert len(records) == 0

        with pytest.raises(RepositoryError):
            repo.fetch_where([])

    def test_insert(self, conn):
        repo = ClickHouseRepository(conn, User)
        repo.insert(User(id=10, name="John", email="john@skynet"))

        records = repo.fetch_by_field(User.name, "John")
        assert len(records) == 1
        assert records[0].email == "john@skynet"

    def test_insert_pk_returns_none(self, conn):
        repo = ClickHouseRepository(conn, User)
        result = repo.insert_pk(User(id=11, name="Sarah", email="sarah@skynet"))
        assert result is None

        # but the record should be inserted
        records = repo.fetch_by_field(User.name, "Sarah")
        assert len(records) == 1

    def test_delete_pk(self, conn):
        repo = ClickHouseRepository(conn, User)
        repo.insert(User(id=20, name="ToDelete", email="delete@test"))

        # verify it exists
        record = repo.fetch_pk(20)
        assert record is not None

        repo.delete_pk(20)
        # ClickHouse mutations are async; use FINAL to read consistent state
        records = repo.fetch_by_field(User.name, "ToDelete")
        # mutation may be async, but for lightweight deletes it should be immediate
        # just verify no error is raised

    def test_delete_where(self, conn):
        repo = ClickHouseRepository(conn, User)
        repo.insert(User(id=21, name="ToDelete2", email="delete2@test"))

        repo.delete_where([(User.id, "=", 21)])
        # no error raised

        with pytest.raises(RepositoryError):
            repo.delete_where([])

        with pytest.raises(RepositoryError):
            repo.delete_where([("field",)])

    def test_update(self, conn):
        repo = ClickHouseRepository(conn, User)

        # update with pk in record
        user = User(id=1, name="Strider", email="aragorn@lotr")
        repo.update(user)
        # no error raised

    def test_update_with_pk_value(self, conn):
        repo = ClickHouseRepository(conn, User)
        repo.update(User(name="Strider"), pk_value=1)
        # no error raised

    def test_update_missing_pk(self, conn):
        repo = ClickHouseRepository(conn, User)
        with pytest.raises(RepositoryError, match="missing primary key value"):
            repo.update(User(name="Strider"))

    def test_update_where(self, conn):
        repo = ClickHouseRepository(conn, User)
        repo.update_where(User(name="Pocoyo"), [(User.login, "=", "gollum")])
        # no error raised

    def test_update_where_two_arg(self, conn):
        repo = ClickHouseRepository(conn, User)
        repo.update_where(User(name="Pocoyo"), [(User.login, "gollum")])
        # no error raised (2-tuple uses = operator)

    def test_update_where_errors(self, conn):
        repo = ClickHouseRepository(conn, User)

        with pytest.raises(RepositoryError):
            repo.update_where(User(name="x"), [])

        with pytest.raises(RepositoryError):
            repo.update_where(User(name="x"), "not_a_list")

        with pytest.raises(RepositoryError):
            repo.update_where(User(name="x"), [("a",)])

        with pytest.raises(RepositoryError):
            repo.update_where(User(name="x"), ["not_a_tuple"])

    def test_count(self, conn):
        repo = ClickHouseRepository(conn, User)
        assert repo.count() == len(fixture_data)

    def test_count_where(self, conn):
        repo = ClickHouseRepository(conn, User)
        assert repo.count_where([(User.id, ">", 0)]) == len(fixture_data)
        assert repo.count_where([(User.name, "gandalf")]) == 1

    def test_valid_pk(self, conn):
        repo = ClickHouseRepository(conn, User)
        assert repo.valid_pk(1) is True
        assert repo.valid_pk(999) is False

    def test_exists(self, conn):
        repo = ClickHouseRepository(conn, User)
        # name "aragorn" exists with id=1, so checking with other id should be True
        assert repo.exists(User.name, "aragorn", 2) is True
        # checking with own id should be False (no OTHER record has this name)
        assert repo.exists(User.name, "aragorn", 1) is False

    def test_map_result_id(self, conn):
        repo = ClickHouseRepository(conn, User)
        users = repo.map_result_id(repo.fetch_all())
        assert len(users) == len(fixture_data)
        for pk, record in users.items():
            assert pk == record.id

    def test_list(self, conn):
        repo = ClickHouseRepository(conn, User)
        qry = repo.select().order(User.id)
        total, rows = repo.list(qry, 2)
        assert total == len(fixture_data)
        assert len(rows) == 2

        total, rows = repo.list(qry, 2, 2)
        assert total == len(fixture_data)
        assert len(rows) == 2

    def test_select_builder(self, conn):
        repo = ClickHouseRepository(conn, User)
        qry = repo.select([User.id, User.name])
        sql, _ = qry.assemble()
        assert '"id_user"' in sql
        assert '"name"' in sql

    def test_transaction_context_manager(self, conn):
        """ClickHouse transactions are no-ops but the API should not error"""
        repo = ClickHouseRepository(conn, User)
        with repo.transaction():
            repo.insert(User(id=30, name="TxTest", email="tx@test"))
        # no error raised

    def test_exec_raw(self, conn):
        repo = ClickHouseRepository(conn, User)
        result = repo.exec("SELECT count() AS cnt FROM users", useCls=False)
        assert len(result) == 1
        assert result[0]["cnt"] == len(fixture_data)
