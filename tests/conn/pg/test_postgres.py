import pytest

from rick_db.conn.pg import PgConnection, PgThreadedConnectionPool, PgConnectionPool
from rick_db.sql import PgSqlDialect
from tests.config import postgres_db, connectSimple
from rick_db import fieldmapper
from rick_db.profiler import NullProfiler


@fieldmapper
class Animal:
    legs = 'legs'
    name = 'name'


def connectPool() -> PgConnectionPool:
    cfg_pool = postgres_db.copy()
    cfg_pool['minconn'] = 4
    return PgConnectionPool(**postgres_db)


def connectThreadedPool() -> PgThreadedConnectionPool:
    cfg_pool = postgres_db.copy()
    cfg_pool['minconn'] = 4
    return PgThreadedConnectionPool(**postgres_db)


class TestPGConnection:
    createTable = "create table if not exists animals(legs int, name varchar);"
    dropTable = "drop table if exists animals"
    insertTable = "insert into animals(legs, name) values(%s, %s)"
    selectByLeg = "select * from animals where legs = %s"

    rows = [(1, 'pirate'), (2, 'canary'), (3, 'maimed dog'), (4, 'cat'), (5, 'pirate ant')]

    def setup_method(self, test_method):
        conn = connectSimple()
        with conn.cursor() as qry:
            qry.exec(self.createTable)
            for r in self.rows:
                qry.exec(self.insertTable, r)

    def teardown_method(self, test_method):
        conn = connectSimple()
        with conn.cursor() as c:
            c.exec(self.dropTable)

    @pytest.fixture()
    def conn(self):
        return connectSimple()

    def test_connection(self, conn):
        assert isinstance(conn.profiler, NullProfiler) is True

    def test_transaction_commit(self, conn):
        conn.begin()
        assert conn.transaction_status() is True
        assert conn.autocommit is False
        with conn.cursor() as c:
            assert c._in_transaction is True
            c.exec(self.insertTable, (7, 'squid'))

        # still in transaction, now lets rollback
        assert conn.transaction_status() is True
        conn.commit()
        assert conn.transaction_status() is False

        # transaction commit, animal should be found
        with conn.cursor() as c:
            animal = c.fetchone(self.selectByLeg, [7])
            assert len(animal) == 2
            assert animal['legs'] == 7
            assert animal['name'] == 'squid'

    def test_transaction_rollback(self, conn):
        # transaction control
        conn.begin()
        assert conn.transaction_status() is True
        assert conn.autocommit is False
        with conn.cursor() as c:
            assert c._in_transaction is True
            c.exec(self.insertTable, (8, 'octopus'))

        # still in transaction, now lets rollback
        assert conn.transaction_status() is True
        conn.rollback()
        assert conn.transaction_status() is False

        # transaction rollback, no animal should be found
        with conn.cursor() as c:
            animal = c.fetchone(self.selectByLeg, [8])
            assert animal is None

    def test_transaction_rollback_multi(self, conn):
        # test rollback of multiple cursors
        conn.begin()
        assert conn.transaction_status() is True
        assert conn.autocommit is False
        with conn.cursor() as c:
            assert c._in_transaction is True
            c.exec(self.insertTable, (8, 'octopus'))

        with conn.cursor() as c:
            assert c._in_transaction is True
            c.exec(self.insertTable, (7, 'squid'))

        # still in transaction, now lets rollback
        assert conn.transaction_status() is True
        conn.rollback()
        assert conn.transaction_status() is False

        # transaction rollback, no animal should be found
        with conn.cursor() as c:
            animal = c.fetchone(self.selectByLeg, [8])
            assert animal is None
            animal = c.fetchone(self.selectByLeg, [7])
            assert animal is None

    def test_fetchone(self, conn):
        c = conn.cursor()

        # non-existing record
        animal = c.fetchone(self.selectByLeg, [16])
        assert animal is None

        # non-existing record with class
        animal = c.fetchone(self.selectByLeg, [16], cls=Animal)
        assert animal is None

        # simple record
        animal = c.fetchone(self.selectByLeg, [4])
        assert len(animal) == 2
        assert animal['legs'] == 4
        assert animal['name'] == 'cat'

        # simple record as Class
        animal = c.fetchone(self.selectByLeg, [4], Animal)
        assert len(animal.asdict()) == 2
        assert animal.legs == 4
        assert animal.name == 'cat'

    def test_fetchall(self, conn):
        c = conn.cursor()

        # non-existing record
        animal = c.fetchall(self.selectByLeg, [16])
        assert type(animal) is list
        assert len(animal) == 0

        # non-existing record with class
        animal = c.fetchall(self.selectByLeg, [16], cls=Animal)
        assert type(animal) is list
        assert len(animal) == 0

        # simple record
        animal = c.fetchall(self.selectByLeg, [4])
        assert type(animal) is list
        assert len(animal) == 1
        assert animal[0]['legs'] == 4
        assert animal[0]['name'] == 'cat'

        # simple record as Class
        animal = c.fetchall(self.selectByLeg, [4], cls=Animal)
        assert type(animal) is list
        assert len(animal) == 1
        animal = animal.pop()
        assert len(animal.asdict()) == 2
        assert animal.legs == 4
        assert animal.name == 'cat'

    def test_sqldialect(self, conn):
        assert isinstance(conn.dialect(), PgSqlDialect)


class TestPGConnectionPool(TestPGConnection):

    @pytest.fixture()
    def conn(self):
        return connectPool().getconn()


class TestPGThreadedConnectionPool(TestPGConnection):

    @pytest.fixture()
    def conn(self):
        return connectThreadedPool().getconn()
