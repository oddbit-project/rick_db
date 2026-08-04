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
        ks = Keyset("id_grid", unique=True)
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
            Keyset(["a", "a"], unique=True)

    def test_rejects_an_empty_field_list(self):
        with pytest.raises(KeysetError):
            Keyset([], unique=True)

    def test_rejects_a_non_string_field(self):
        with pytest.raises(KeysetError):
            Keyset([1], unique=True)

    def test_rejects_an_invalid_order(self):
        with pytest.raises(KeysetError):
            Keyset("id_grid", "SIDEWAYS", unique=True)

    def test_a_mixed_direction_keyset_cannot_be_expressed(self):
        # there is no per-field direction to pass: the seek predicate is only
        # valid when every field sorts the same way, so the API does not offer
        # the option rather than validating it after the fact
        ks = Keyset(["a", "b"], Keyset.DESC, unique=True)
        assert ks.order == Keyset.DESC
        sql, _ = ks.apply(qry(), None).assemble()
        assert 'ORDER BY "a" DESC,"b" DESC' in sql


class TestSeekPredicate:

    def test_no_cursor_orders_but_does_not_filter(self):
        sql, values = Keyset("id_grid", unique=True).apply(qry(), None).assemble()
        assert "WHERE" not in sql
        assert 'ORDER BY "id_grid" ASC' in sql
        assert values == []

    def test_single_field_ascending(self):
        ks = Keyset("id_grid", unique=True)
        sql, values = ks.apply(qry(), ks.encode({"id_grid": 10})).assemble()
        assert '("id_grid" > %s)' in sql
        assert values == [10]

    def test_single_field_descending(self):
        ks = Keyset("id_grid", Keyset.DESC, unique=True)
        sql, values = ks.apply(qry(), ks.encode({"id_grid": 10})).assemble()
        assert '("id_grid" < %s)' in sql
        assert values == [10]

    def test_composite_expands_to_an_or_of_and_chain(self):
        ks = Keyset(["content", "id_grid"], unique=True)
        cursor = ks.encode({"content": "x", "id_grid": 7})
        sql, values = ks.apply(qry(), cursor).assemble()
        # (content > x) OR (content = x AND id_grid > 7)
        assert '("content" > %s)' in sql
        assert '("content" = %s)' in sql
        assert '("id_grid" > %s)' in sql
        assert values == ["x", "x", 7]

    def test_three_fields_produce_two_tie_terms(self):
        ks = Keyset(["a", "b", "c"], unique=True)
        cursor = ks.encode({"a": 1, "b": 2, "c": 3})
        sql, values = ks.apply(qry(), cursor).assemble()
        # count on the WHERE clause only — "ORDER BY" contains an OR
        assert sql.split("ORDER BY")[0].count(" OR ") == 2
        assert values == [1, 1, 2, 1, 2, 3]

    def test_accepts_raw_values_instead_of_a_cursor(self):
        ks = Keyset(["a", "b"], unique=True)
        sql, values = ks.apply(qry(), [1, 2]).assemble()
        assert values == [1, 1, 2]

    def test_rejects_a_cursor_of_the_wrong_arity(self):
        with pytest.raises(KeysetError):
            Keyset(["a", "b"], unique=True).apply(qry(), [1])


class TestCursorRoundTrip:

    def test_values_survive_with_their_types(self):
        ks = Keyset(["a", "b", "c", "d", "e"], unique=True)
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
        ks = Keyset(["a", "b"], unique=True)
        row = {"a": datetime.date(2024, 5, 6), "b": datetime.time(7, 8, 9)}
        assert ks.decode(ks.encode(row)) == [row["a"], row["b"]]

    def test_reads_a_record_as_well_as_a_dict(self):
        ks = Keyset(["label", "id_grid"], unique=True)
        record = KeysetRecord(label="abc", id=5)
        assert ks.values_for(record) == ["abc", 5]

    def test_a_cursor_from_another_ordering_is_refused(self):
        issued = Keyset(["a", "b"], unique=True).encode({"a": 1, "b": 2})
        with pytest.raises(KeysetError, match="does not belong to this ordering"):
            Keyset(["a", "c"], unique=True).decode(issued)

    def test_a_cursor_from_the_other_direction_is_refused(self):
        issued = Keyset(["a"], Keyset.ASC, unique=True).encode({"a": 1})
        with pytest.raises(KeysetError, match="does not belong to this ordering"):
            Keyset(["a"], Keyset.DESC, unique=True).decode(issued)

    def test_a_malformed_cursor_is_refused(self):
        for bad in ("", "!!!!", "YWJj", "x" * 12):
            with pytest.raises(KeysetError):
                Keyset(["a"], unique=True).decode(bad)

    def test_a_null_key_is_refused(self):
        with pytest.raises(KeysetError, match="NULL"):
            Keyset(["a"], unique=True).encode({"a": None})

    def test_a_missing_key_is_refused(self):
        with pytest.raises(KeysetError, match="not present in the row"):
            Keyset(["a"], unique=True).encode({"b": 1})

    def test_an_unorderable_value_is_refused(self):
        with pytest.raises(KeysetError, match="orderable scalars"):
            Keyset(["a"], unique=True).encode({"a": {"nested": "dict"}})

    def test_a_row_of_the_wrong_shape_is_refused(self):
        with pytest.raises(KeysetError, match="Record or a Mapping"):
            Keyset(["a"], unique=True).values_for(object())


class TestUniquenessIsRequired:

    def test_a_keyset_with_no_uniqueness_claim_is_refused(self):
        # the failure it prevents is silent: a non-unique ordering drops rows at
        # page boundaries and the walk still ends cleanly
        with pytest.raises(KeysetError, match="must be unique"):
            Keyset(["content"])

    def test_pk_satisfies_it(self):
        assert Keyset(["content"], pk="id_grid").fields == ["content", "id_grid"]

    def test_unique_flag_satisfies_it(self):
        assert Keyset(["id_grid"], unique=True).fields == ["id_grid"]

    def test_an_empty_field_list_is_refused_even_with_a_pk(self):
        with pytest.raises(KeysetError, match="at least one field"):
            Keyset([], pk="id_grid")


class TestQueryOwnership:

    def test_a_pre_ordered_query_is_refused(self):
        q = qry().order("label", "ASC")
        with pytest.raises(KeysetError, match="already has an ORDER BY"):
            Keyset("id_grid", unique=True).apply(q, None)

    def test_apply_is_not_silently_repeatable(self):
        ks = Keyset("id_grid", unique=True)
        q = ks.apply(qry(), None)
        with pytest.raises(KeysetError, match="already has an ORDER BY"):
            ks.apply(q, None)


class TestCursorEncodingLimits:

    def test_nan_is_refused_rather_than_emitting_invalid_json(self):
        with pytest.raises(KeysetError):
            Keyset(["a"], unique=True).encode({"a": float("nan")})

    def test_infinity_is_refused(self):
        with pytest.raises(KeysetError):
            Keyset(["a"], unique=True).encode({"a": float("inf")})

    def test_a_cursor_missing_its_signature_reads_as_malformed(self):
        import base64 as _b64
        import json as _json

        raw = _json.dumps({"v": [1]})
        bad = _b64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
        with pytest.raises(KeysetError, match="malformed cursor"):
            Keyset(["a"], unique=True).decode(bad)

    def test_a_json_excluded_field_is_still_readable_as_a_key(self):
        # asrecord(), not asdict(): the serialization view would hide it
        @fieldmapper(tablename="grid", pk="id_grid", json_exclude=["content"])
        class Hidden:
            id = "id_grid"
            content = "content"

        row = Hidden(id=1, content="x")
        assert Keyset(["content"], pk="id_grid").values_for(row) == ["x", 1]


class TestSelectGuards:

    def test_has_order_and_has_limit_are_public(self):
        q = qry()
        assert q.has_order() is False
        assert q.has_limit() is False
        q.order("a", "ASC").limit(10, 5)
        assert q.has_order() is True
        assert q.has_limit() is True

    def test_apply_refuses_something_that_is_not_a_select(self):
        # the guard must fail closed rather than skip on a duck-typed object
        class NotASelect:
            def order(self, *a, **kw):
                return self

        with pytest.raises(KeysetError, match="must be a Select"):
            Keyset("a", unique=True).apply(NotASelect(), None)


class TestErrorTypes:

    def test_keyset_error_is_a_value_error(self):
        # one except clause for a bad cursor from a client
        assert issubclass(KeysetError, ValueError)
        with pytest.raises(ValueError):
            Keyset(["a"], unique=True).decode("!!!!")
