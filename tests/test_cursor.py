from rick_db import Cursor
from rick_db.backend.pg import PgConnectionPool
from rick_db.mapper import fieldmapper


@fieldmapper
class NumberRecord:
    id = "id"


class TestCursor:

    def test_init(self, pg_pool: PgConnectionPool):
        with pg_pool.connection() as conn:
            with conn.cursor() as cur:
                assert isinstance(cur, Cursor)

    def test_execute(self, pg_pool: PgConnectionPool):
        with pg_pool.connection() as conn:
            with conn.cursor() as cur:
                # simple select
                result = cur.exec("select 1")
                assert len(result) == 1

                # object mapper hydration
                cur.exec("drop table if exists counter")
                cur.exec("create table counter (id int)")
                cur.exec("insert into counter select * from generate_series(1,4)")
                result = cur.exec("select * from counter", cls=NumberRecord)
                assert len(result) == 4
                for r in result:
                    assert isinstance(r, NumberRecord)

                # parameters
                result = cur.exec(
                    "select * from counter where id=%s", (2,), cls=NumberRecord
                )
                assert len(result) == 1
                assert isinstance(result[0], NumberRecord)
                assert result[0].id == 2

                # cleanup
                cur.exec("drop table if exists counter")

    def test_fetchone(self, pg_pool: PgConnectionPool):
        with pg_pool.connection() as conn:
            with conn.cursor() as cur:
                # simple select
                result = cur.fetchone("select 1")
                assert len(result) == 1
                assert result == [
                    1,
                ]

                # object mapper hydration
                cur.exec("drop table if exists counter")
                cur.exec("create table counter (id int)")
                cur.exec("insert into counter select * from generate_series(1,4)")
                result = cur.fetchone("select * from counter", cls=NumberRecord)
                assert isinstance(result, NumberRecord)

                # parameters
                result = cur.fetchone(
                    "select * from counter where id=%s", (2,), cls=NumberRecord
                )
                assert isinstance(result, NumberRecord)
                assert result.id == 2

                # cleanup
                cur.exec("drop table if exists counter")

    def test_fetchall(self, pg_pool: PgConnectionPool):
        with pg_pool.connection() as conn:
            with conn.cursor() as cur:
                # simple select
                result = cur.fetchall("select 1")
                assert len(result) == 1

                # object mapper hydration
                cur.exec("drop table if exists counter")
                cur.exec("create table counter (id int)")
                cur.exec("insert into counter select * from generate_series(1,4)")
                result = cur.fetchall("select * from counter", cls=NumberRecord)
                assert len(result) == 4
                for r in result:
                    assert isinstance(r, NumberRecord)

                # parameters
                result = cur.fetchall(
                    "select * from counter where id=%s", (2,), cls=NumberRecord
                )
                assert len(result) == 1
                assert isinstance(result[0], NumberRecord)
                assert result[0].id == 2

                # cleanup
                cur.exec("drop table if exists counter")
