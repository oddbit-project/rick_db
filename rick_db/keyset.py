import base64
import binascii
import datetime
import decimal
import hashlib
import json
import uuid
from collections.abc import Mapping

from rick_db.sql import Select

# tags used to round-trip non-JSON-native values through a cursor without
# losing their type; a cursor value is compared against a real column, so
# handing the driver a string where the column is an int is not an option
_TAG = "__t"
_VALUE = "v"
_TAG_DATETIME = "dt"
_TAG_DATE = "d"
_TAG_TIME = "t"
_TAG_DECIMAL = "n"
_TAG_UUID = "u"


class KeysetError(ValueError):
    pass


class Keyset:
    """
    Ordering and seek predicate for keyset (cursor) pagination.

    Keyset pagination answers "the next N rows after this row" rather than
    "N rows starting at position M". The database seeks straight to the cursor
    position on the index and reads forward, so page 10000 costs what page 1
    costs, and a concurrent insert cannot shift rows across a page boundary the
    way it does with OFFSET.

    The trade is that it walks forward in one ordering: there is no jumping to
    an arbitrary page, and no total row count (see DbGrid.run_seek()).

    All fields sort in the SAME direction, by construction. A keyset ordered
    (a ASC, b DESC) cannot be expressed as a seek predicate at all, so the
    direction is a single parameter rather than a per-field one — the shape of
    the API refuses what the algorithm cannot do.

    The ordering must also be unique, and that is required at construction:
    pass `pk=` to have a tiebreaker appended, or `unique=True` to assert the
    fields already are. Seeking on a non-unique ordering silently skips or
    repeats rows whenever two of them share a value at a page boundary, and the
    walk still ends cleanly — so the caller believes it saw everything.
    """

    ASC = "ASC"
    DESC = "DESC"

    def __init__(self, fields, order: str = ASC, pk: str = None, unique: bool = False):
        """
        :param fields: field name or list of field names, most significant first
        :param order: Keyset.ASC or Keyset.DESC, applied to every field
        :param pk: unique field appended as a tiebreaker if absent
        :param unique: assert that `fields` is already unique, in place of `pk`
        """
        if isinstance(fields, str):
            fields = [fields]
        if not isinstance(fields, (list, tuple)):
            raise KeysetError("Keyset(): fields must be a string or a list of strings")

        fields = list(fields)
        for name in fields:
            if not isinstance(name, str):
                raise KeysetError("Keyset(): field names must be strings")
        if len(fields) != len(set(fields)):
            raise KeysetError("Keyset(): duplicate field in keyset")
        if len(fields) == 0:
            raise KeysetError("Keyset(): at least one field is required")

        order = str(order).upper()
        if order not in (self.ASC, self.DESC):
            raise KeysetError("Keyset(): order must be either ASC or DESC")

        # A keyset whose ordering is not unique silently skips or repeats rows
        # at any page boundary where the last value repeats, and the walk still
        # terminates cleanly — so the caller believes it saw everything. There
        # is no way to detect that at runtime, so uniqueness has to be stated:
        # either name the tiebreaker with pk=, or assert the fields are already
        # unique with unique=True.
        if pk is not None:
            if not isinstance(pk, str):
                raise KeysetError("Keyset(): pk must be a string")
            if pk not in fields:
                fields.append(pk)
        elif not unique:
            raise KeysetError(
                "Keyset(): a keyset must be unique or it will silently skip rows "
                "at page boundaries. Pass pk='<unique field>' to append a "
                "tiebreaker, or unique=True if these fields are already unique."
            )

        self._fields = fields
        self._order = order
        self._operator = "<" if order == self.DESC else ">"
        # binds a cursor to the ordering that produced it, so a client that
        # changes sort while holding a cursor is refused instead of silently
        # served a page from the middle of a different ordering
        self._signature = hashlib.sha256(
            ("|".join(fields) + ":" + order).encode("utf-8")
        ).hexdigest()[:12]

    @property
    def fields(self) -> list:
        return list(self._fields)

    @property
    def order(self) -> str:
        return self._order

    @property
    def signature(self) -> str:
        return self._signature

    def apply(self, qry: Select, cursor=None) -> Select:
        """
        Apply the ordering, and the seek predicate when a cursor is given.

        The predicate is emitted as an expanded OR-of-AND chain:

            (a < ?) OR (a = ? AND b < ?)

        rather than the row-value form `(a, b) < (?, ?)`. Both are correct on
        PostgreSQL, but row-value comparison is not portable across every
        backend rick_db targets, and the expanded form needs nothing from the
        query builder that is not already public.

        :param qry: query to extend; must not already carry an ORDER BY
        :param cursor: opaque cursor string, or a sequence of raw key values
        :return: qry
        :raises KeysetError: if the query is already ordered
        """
        # A pre-existing ORDER BY would lead the sort, leaving the keyset's
        # fields as trailing terms while the seek predicate still advances on
        # them — the walk then skips and repeats rows instead of failing. That
        # is the worst possible outcome for a pagination primitive, so it is
        # refused rather than merged or silently discarded: the ordering is the
        # keyset's to own.
        if not hasattr(qry, "has_order"):
            raise KeysetError("Keyset.apply(): qry must be a Select")
        if qry.has_order():
            raise KeysetError(
                "Keyset.apply(): the query already has an ORDER BY. The keyset "
                "defines the ordering, and a sort applied ahead of it silently "
                "breaks the seek. Remove the order() call, or fold those fields "
                "into the keyset — note the sort may come from a DbGrid subclass "
                "overriding default_query(), not from the caller."
            )

        for name in self._fields:
            qry.order(name, self._order)

        if cursor is None:
            return qry

        values = self.decode(cursor) if isinstance(cursor, str) else list(cursor)
        if len(values) != len(self._fields):
            raise KeysetError(
                "Keyset.apply(): cursor has %d values, keyset has %d fields"
                % (len(values), len(self._fields))
            )

        qry.where_and()
        for i, name in enumerate(self._fields):
            if i == 0:
                qry.where(name, self._operator, values[0])
                continue
            # each subsequent term ties the preceding keys and advances on this one
            qry.where_or()
            for j in range(i):
                qry.where(self._fields[j], "=", values[j])
            qry.where(name, self._operator, values[i])
            qry.where_end()
        qry.where_end()
        return qry

    def values_for(self, row) -> list:
        """
        Extract this keyset's values from a row (Record or Mapping).

        :param row: result row
        :return: list of key values, in field order
        """
        if isinstance(row, Mapping):
            data = row
        elif hasattr(row, "asrecord"):
            # asrecord(), not asdict(): a keyset is declared in db field names,
            # and asdict() is the SERIALIZATION view — keyed by attribute name
            # and filtered by json_exclude, so a keyset on an excluded column
            # would look like a missing field. asrecord() is keyed by db field
            # and excludes nothing.
            data = row.asrecord()
        else:
            raise KeysetError(
                "Keyset.values_for(): row must be a Record or a Mapping, got %s"
                % type(row).__name__
            )

        result = []
        for name in self._fields:
            if name not in data:
                raise KeysetError(
                    "Keyset.values_for(): field '%s' is not present in the row; a "
                    "keyset field must be selected by the query" % name
                )
            value = data[name]
            if value is None:
                # a NULL key cannot be seeked past: every comparison against it
                # is NULL, so the following page would come back empty
                raise KeysetError(
                    "Keyset.values_for(): field '%s' is NULL; keyset fields must "
                    "be non-nullable" % name
                )
            result.append(value)
        return result

    def assert_no_nulls(self, rows) -> None:
        """
        Raise if any row carries a NULL in a keyset field.

        Nullability cannot be refused at construction — a Record does not carry
        it — and a NULL key is not merely an encoding problem: it is excluded by
        the seek predicate on every page after the first, so the walk ends short
        with no error at all. Where a NULL does surface in a returned page, that
        is proof the precondition is broken, and failing loudly beats handing
        back rows from a traversal that is already dropping them.

        Note this catches the detectable cases only. Under an ordering that
        sorts NULLs after the cursor's position they may never be returned, and
        nothing here can see them — which is why the fields must be NOT NULL.

        :param rows: rows to check
        :return: None
        """
        for row in rows:
            self.values_for(row)

    def encode(self, row) -> str:
        """
        Build an opaque cursor from the last row of a page.

        :param row: result row
        :return: cursor string
        """
        payload = {
            "k": self._signature,
            _VALUE: [_encode_value(v) for v in self.values_for(row)],
        }
        try:
            # allow_nan=False: json.dumps would otherwise emit bare NaN /
            # Infinity, which is not valid JSON and breaks any non-Python
            # consumer of a cursor that is designed to cross the wire
            raw = json.dumps(
                payload, separators=(",", ":"), sort_keys=True, allow_nan=False
            )
        except ValueError as e:
            raise KeysetError(
                "Keyset.encode(): value cannot be encoded in a cursor"
            ) from e
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")

    def decode(self, cursor: str) -> list:
        """
        Read the key values back out of a cursor, verifying it belongs to this
        keyset.

        :param cursor: cursor string
        :return: list of key values
        """
        if not isinstance(cursor, str) or len(cursor) == 0:
            raise KeysetError("Keyset.decode(): cursor must be a non-empty string")
        try:
            padding = "=" * (-len(cursor) % 4)
            raw = base64.urlsafe_b64decode(cursor + padding).decode("utf-8")
            payload = json.loads(raw)
        except (binascii.Error, ValueError, UnicodeDecodeError) as e:
            raise KeysetError("Keyset.decode(): malformed cursor") from e

        if not isinstance(payload, dict) or _VALUE not in payload:
            raise KeysetError("Keyset.decode(): malformed cursor")
        if "k" not in payload:
            raise KeysetError("Keyset.decode(): malformed cursor")
        if payload["k"] != self._signature:
            raise KeysetError(
                "Keyset.decode(): cursor does not belong to this ordering; it was "
                "issued for a different set of fields or a different direction"
            )
        values = payload[_VALUE]
        if not isinstance(values, list) or len(values) != len(self._fields):
            raise KeysetError("Keyset.decode(): malformed cursor")
        return [_decode_value(v) for v in values]


def _encode_value(value):
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, datetime.datetime):
        return {_TAG: _TAG_DATETIME, _VALUE: value.isoformat()}
    if isinstance(value, datetime.date):
        return {_TAG: _TAG_DATE, _VALUE: value.isoformat()}
    if isinstance(value, datetime.time):
        return {_TAG: _TAG_TIME, _VALUE: value.isoformat()}
    if isinstance(value, decimal.Decimal):
        return {_TAG: _TAG_DECIMAL, _VALUE: str(value)}
    if isinstance(value, uuid.UUID):
        return {_TAG: _TAG_UUID, _VALUE: str(value)}
    raise KeysetError(
        "Keyset: cannot encode a cursor value of type '%s'; keyset fields must be "
        "orderable scalars" % type(value).__name__
    )


def _decode_value(value):
    if not isinstance(value, dict):
        return value
    tag = value.get(_TAG)
    raw = value.get(_VALUE)
    try:
        if tag == _TAG_DATETIME:
            return datetime.datetime.fromisoformat(raw)
        if tag == _TAG_DATE:
            return datetime.date.fromisoformat(raw)
        if tag == _TAG_TIME:
            return datetime.time.fromisoformat(raw)
        if tag == _TAG_DECIMAL:
            return decimal.Decimal(raw)
        if tag == _TAG_UUID:
            return uuid.UUID(raw)
    except (TypeError, ValueError, decimal.InvalidOperation) as e:
        raise KeysetError("Keyset.decode(): malformed cursor value") from e
    raise KeysetError("Keyset.decode(): malformed cursor value")
