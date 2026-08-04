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


class KeysetError(Exception):
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

    A unique tiebreaker is required, and appended automatically when `pk` is
    given: seeking on a non-unique column alone silently skips or repeats rows
    whenever two of them share a value at a page boundary.
    """

    ASC = "ASC"
    DESC = "DESC"

    def __init__(self, fields, order: str = ASC, pk: str = None):
        """
        :param fields: field name or list of field names, most significant first
        :param order: Keyset.ASC or Keyset.DESC, applied to every field
        :param pk: optional unique field appended as a tiebreaker if absent
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

        order = str(order).upper()
        if order not in (self.ASC, self.DESC):
            raise KeysetError("Keyset(): order must be either ASC or DESC")

        if pk is not None:
            if not isinstance(pk, str):
                raise KeysetError("Keyset(): pk must be a string")
            if pk not in fields:
                fields.append(pk)

        if len(fields) == 0:
            raise KeysetError("Keyset(): at least one field is required")

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

        :param qry: query to extend
        :param cursor: opaque cursor string, or a sequence of raw key values
        :return: qry
        """
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
        elif hasattr(row, "asdict") and hasattr(row, "fieldmap"):
            # a Record's asdict() is keyed by ATTRIBUTE name, while a keyset is
            # declared in db field names (the same names DbGrid matches, sorts
            # and searches on), so translate rather than assume they coincide
            fieldmap = row.fieldmap()
            data = {
                fieldmap[attr]: value
                for attr, value in row.asdict().items()
                if attr in fieldmap
            }
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
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
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
        if payload.get("k") != self._signature:
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
