import datetime as dt
import decimal
import uuid

import pytest

from rick_db import Keyset, KeysetError, fieldmapper
from rick_db.sql import ClickHouseSqlDialect, PgSqlDialect, Select, SqlError


@fieldmapper(tablename="events", pk="id_event", json_exclude=["created_at"])
class Event:
    id = "id_event"
    created = "created_at"
    amount = "amount"
    request_id = "request_id"


class CapturingRepository:
    """Minimal repository double used to inspect Keyset's generated Select."""

    def __init__(self, dialect=None):
        self.dialect = dialect or PgSqlDialect()
        self.sql = None
        self.values = None

    @staticmethod
    def record_class():
        return Event

    def select(self):
        return Select(self.dialect).from_("events")

    def seek(self, qry, limit):
        self.sql, self.values = qry.assemble()
        return [], False


class TestKeyset:
    def test_run_uses_a_single_row_value_predicate(self):
        repo = CapturingRepository()
        keyset = Keyset(repo, ["created_at", "id_event"])
        cursor = keyset._encode({"created_at": 10, "id_event": 7})

        rows, next_cursor = keyset.run(10, cursor)

        assert rows == []
        assert next_cursor is None
        assert '(("events"."created_at", "events"."id_event") > (%s, %s))' in repo.sql
        assert " OR " not in repo.sql
        assert repo.values == [10, 7]

    def test_run_descending_uses_less_than(self):
        repo = CapturingRepository()
        keyset = Keyset(repo, "id_event", Keyset.DESC)
        cursor = keyset._encode({"id_event": 7})

        keyset.run(10, cursor)

        assert '("events"."id_event") < (%s)' in repo.sql
        assert 'ORDER BY "events"."id_event" DESC' in repo.sql
        assert repo.values == [7]

    def test_run_uses_clickhouse_placeholders(self):
        repo = CapturingRepository(ClickHouseSqlDialect())
        keyset = Keyset(repo, ["created_at", "id_event"])
        cursor = keyset._encode({"created_at": 10, "id_event": 7})

        keyset.run(10, cursor)

        assert '(("events"."created_at", "events"."id_event") > (%s, %s))' in repo.sql
        assert repo.values == [10, 7]

    def test_run_accepts_a_one_off_base_query(self):
        repo = CapturingRepository()
        keyset = Keyset(repo, "id_event")
        qry = repo.select().where("id_event", ">", 3)

        keyset.run(10, qry=qry)

        assert '("id_event" > %s)' in repo.sql
        assert 'ORDER BY "events"."id_event" ASC' in repo.sql
        assert repo.values == [3]

    def test_subclass_can_supply_a_reusable_base_query(self):
        repo = CapturingRepository()

        class ActiveEvents(Keyset):
            def __init__(self, repository):
                super().__init__(repository, "id_event")
                self._query = repository.select().where("id_event", ">", 3)

            def default_query(self):
                return self._query

        keyset = ActiveEvents(repo)
        keyset.run(10)
        keyset.run(10)

        assert '("id_event" > %s)' in repo.sql
        sql, values = keyset._query.assemble()
        assert "ORDER BY" not in sql
        assert values == [3]

    def test_cursor_preserves_database_value_types(self):
        keyset = Keyset(CapturingRepository(), ["created_at", "amount", "request_id"])
        row = {
            "created_at": dt.datetime(2026, 8, 4, 12, 30, 1),
            "amount": decimal.Decimal("14.20"),
            "request_id": uuid.UUID("12345678-1234-5678-1234-567812345678"),
        }

        assert keyset._decode(keyset._encode(row)) == list(row.values())

    def test_cursor_rejects_another_keyset(self):
        repo = CapturingRepository()
        cursor = Keyset(repo, "id_event")._encode({"id_event": 7})

        with pytest.raises(KeysetError, match="another keyset"):
            Keyset(repo, "created_at")._decode(cursor)

    def test_cursor_reads_json_excluded_database_fields(self):
        event = Event(id=7, created=dt.datetime(2026, 8, 4, 12, 30, 1))

        assert Keyset(CapturingRepository(), "created_at")._values_for(event) == [
            event.created
        ]

    def test_keyset_rejects_invalid_definition_or_ordered_query(self):
        repo = CapturingRepository()
        with pytest.raises(KeysetError):
            Keyset(repo, [])
        with pytest.raises(KeysetError):
            Keyset(repo, ["id_event", "id_event"])
        with pytest.raises(KeysetError):
            Keyset(repo, "unknown")
        with pytest.raises(KeysetError):
            Keyset(repo, "id_event", "sideways")
        with pytest.raises(KeysetError, match="ORDER BY"):
            Keyset(repo).run(10, qry=repo.select().order("id_event"))


class TestWhereRow:
    def test_where_row_validates_shape_and_operator(self):
        query = Select(PgSqlDialect()).from_("events")
        with pytest.raises(SqlError):
            query.where_row([], ">", [])
        with pytest.raises(SqlError):
            query.where_row(["id_event"], "=", [7])
        with pytest.raises(SqlError):
            query.where_row(["id_event"], ">", [7, 8])
