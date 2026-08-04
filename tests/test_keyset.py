import datetime
import decimal
import uuid

import pytest

from rick_db import Keyset, KeysetError, fieldmapper
from rick_db.sql import Select, PgSqlDialect


@fieldmapper(tablename="grid", pk="id_grid")
class KeysetRecord:
    id = "id_grid"
    label = "label"
    content = "content"


def qry() -> Select:
    return Select(PgSqlDialect()).from_("grid")


class TestKeysetConstruction:

    def test_accepts_a_single_field_as_a_string(self):
        ks = Keyset("id_grid")
        assert ks.fields == ["id_grid"]
        assert ks.order == Keyset.ASC

    def test_appends_the_pk_as_a_tiebreaker(self):
        ks = Keyset(["content"], pk="id_grid")
        assert ks.fields == ["content", "id_grid"]

    def test_does_not_duplicate_a_pk_already_present(self):
        ks = Keyset(["content", "id_grid"], pk="id_grid")
        assert ks.fields == ["content", "id_grid"]

    def test_rejects_duplicate_fields(self):
        with pytest.raises(KeysetError):
            Keyset(["a", "a"])

    def test_rejects_an_empty_field_list(self):
        with pytest.raises(KeysetError):
            Keyset([])

    def test_rejects_a_non_string_field(self):
        with pytest.raises(KeysetError):
            Keyset([1])

    def test_rejects_an_invalid_order(self):
        with pytest.raises(KeysetError):
            Keyset("id_grid", "SIDEWAYS")

    def test_a_mixed_direction_keyset_cannot_be_expressed(self):
        # there is no per-field direction to pass: the seek predicate is only
        # valid when every field sorts the same way, so the API does not offer
        # the option rather than validating it after the fact
        ks = Keyset(["a", "b"], Keyset.DESC)
        assert ks.order == Keyset.DESC
        sql, _ = ks.apply(qry(), None).assemble()
        assert 'ORDER BY "a" DESC,"b" DESC' in sql


class TestSeekPredicate:

    def test_no_cursor_orders_but_does_not_filter(self):
        sql, values = Keyset("id_grid").apply(qry(), None).assemble()
        assert "WHERE" not in sql
        assert 'ORDER BY "id_grid" ASC' in sql
        assert values == []

    def test_single_field_ascending(self):
        ks = Keyset("id_grid")
        sql, values = ks.apply(qry(), ks.encode({"id_grid": 10})).assemble()
        assert '("id_grid" > %s)' in sql
        assert values == [10]

    def test_single_field_descending(self):
        ks = Keyset("id_grid", Keyset.DESC)
        sql, values = ks.apply(qry(), ks.encode({"id_grid": 10})).assemble()
        assert '("id_grid" < %s)' in sql
        assert values == [10]

    def test_composite_expands_to_an_or_of_and_chain(self):
        ks = Keyset(["content", "id_grid"])
        cursor = ks.encode({"content": "x", "id_grid": 7})
        sql, values = ks.apply(qry(), cursor).assemble()
        # (content > x) OR (content = x AND id_grid > 7)
        assert '("content" > %s)' in sql
        assert '("content" = %s)' in sql
        assert '("id_grid" > %s)' in sql
        assert values == ["x", "x", 7]

    def test_three_fields_produce_two_tie_terms(self):
        ks = Keyset(["a", "b", "c"])
        cursor = ks.encode({"a": 1, "b": 2, "c": 3})
        sql, values = ks.apply(qry(), cursor).assemble()
        # count on the WHERE clause only — "ORDER BY" contains an OR
        assert sql.split("ORDER BY")[0].count(" OR ") == 2
        assert values == [1, 1, 2, 1, 2, 3]

    def test_accepts_raw_values_instead_of_a_cursor(self):
        ks = Keyset(["a", "b"])
        sql, values = ks.apply(qry(), [1, 2]).assemble()
        assert values == [1, 1, 2]

    def test_rejects_a_cursor_of_the_wrong_arity(self):
        with pytest.raises(KeysetError):
            Keyset(["a", "b"]).apply(qry(), [1])


class TestCursorRoundTrip:

    def test_values_survive_with_their_types(self):
        ks = Keyset(["a", "b", "c", "d", "e"])
        row = {
            "a": 42,
            "b": "text",
            "c": datetime.datetime(2024, 1, 2, 3, 4, 5),
            "d": decimal.Decimal("10.25"),
            "e": uuid.UUID("12345678-1234-5678-1234-567812345678"),
        }
        decoded = ks.decode(ks.encode(row))
        assert decoded == [row[k] for k in ("a", "b", "c", "d", "e")]
        assert isinstance(decoded[2], datetime.datetime)
        assert isinstance(decoded[3], decimal.Decimal)
        assert isinstance(decoded[4], uuid.UUID)

    def test_date_and_time_survive(self):
        ks = Keyset(["a", "b"])
        row = {"a": datetime.date(2024, 5, 6), "b": datetime.time(7, 8, 9)}
        assert ks.decode(ks.encode(row)) == [row["a"], row["b"]]

    def test_reads_a_record_as_well_as_a_dict(self):
        ks = Keyset(["label", "id_grid"])
        record = KeysetRecord(label="abc", id=5)
        assert ks.values_for(record) == ["abc", 5]

    def test_a_cursor_from_another_ordering_is_refused(self):
        issued = Keyset(["a", "b"]).encode({"a": 1, "b": 2})
        with pytest.raises(KeysetError, match="does not belong to this ordering"):
            Keyset(["a", "c"]).decode(issued)

    def test_a_cursor_from_the_other_direction_is_refused(self):
        issued = Keyset(["a"], Keyset.ASC).encode({"a": 1})
        with pytest.raises(KeysetError, match="does not belong to this ordering"):
            Keyset(["a"], Keyset.DESC).decode(issued)

    def test_a_malformed_cursor_is_refused(self):
        for bad in ("", "!!!!", "YWJj", "x" * 12):
            with pytest.raises(KeysetError):
                Keyset(["a"]).decode(bad)

    def test_a_null_key_is_refused(self):
        with pytest.raises(KeysetError, match="NULL"):
            Keyset(["a"]).encode({"a": None})

    def test_a_missing_key_is_refused(self):
        with pytest.raises(KeysetError, match="not present in the row"):
            Keyset(["a"]).encode({"b": 1})

    def test_an_unorderable_value_is_refused(self):
        with pytest.raises(KeysetError, match="orderable scalars"):
            Keyset(["a"]).encode({"a": {"nested": "dict"}})

    def test_a_row_of_the_wrong_shape_is_refused(self):
        with pytest.raises(KeysetError, match="Record or a Mapping"):
            Keyset(["a"]).values_for(object())
