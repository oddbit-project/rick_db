"""Cursor-based pagination built on SQL row-value comparison."""

import base64
import binascii
import copy
import datetime as dt
import decimal
import json
import math
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from rick_db.sql import Literal, Select


class KeysetError(ValueError):
    """Raised when a keyset or cursor cannot produce a correct seek query."""


class Keyset:
    """Repository-backed cursor pagination using a stable row-value ordering.

    Subclasses can override :meth:`default_query` in the same way as
    :class:`DbGrid`; :meth:`run` also accepts a one-off ``Select`` through its
    ``qry`` argument. All fields use the same direction and must be selected,
    non-null, and collectively unique.
    """

    ASC = "ASC"
    DESC = "DESC"
    _CURSOR_VERSION = 1

    def __init__(
        self,
        repo: Any,
        fields: str | Sequence[str] | None = None,
        order: str = ASC,
    ) -> None:
        """Create a keyset.

        Args:
            repo: Repository used to build and execute queries.
            fields: Ordered database field names, most significant first. If
                omitted, the Record primary key is used.
            order: ``ASC`` or ``DESC`` for every field.

        Raises:
            KeysetError: If the keyset definition is invalid.
        """
        self._repo = repo
        record = repo.record_class()()
        self._record_fields = record.dbfields()
        self._table = getattr(record, "_tablename", None)
        self._schema = getattr(record, "_schema", None)

        if fields is None:
            fields = getattr(record, "_pk", None)
            if fields is None:
                raise KeysetError(
                    "Keyset(): fields are required when the Record has no primary key"
                )
        if isinstance(fields, str):
            fields = [fields]
        if not isinstance(fields, Sequence):
            raise KeysetError(
                "Keyset(): fields must be a string or sequence of strings"
            )

        self._fields = list(fields)
        if not self._fields or any(
            not isinstance(field, str) or not field for field in self._fields
        ):
            raise KeysetError("Keyset(): at least one non-empty field name is required")
        if len(self._fields) != len(set(self._fields)):
            raise KeysetError("Keyset(): duplicate field in keyset")
        unknown = set(self._fields) - set(self._record_fields)
        if unknown:
            raise KeysetError(
                "Keyset(): unknown Record field '%s'" % sorted(unknown)[0]
            )

        self._order = str(order).upper()
        if self._order not in (self.ASC, self.DESC):
            raise KeysetError("Keyset(): order must be ASC or DESC")

    @property
    def fields(self) -> list[str]:
        """Return the ordered database field names."""
        return list(self._fields)

    @property
    def order(self) -> str:
        """Return the common ordering direction."""
        return self._order

    def default_query(self) -> Select:
        """Build the base query used when :meth:`run` receives no query.

        Override this method to give a keyset a reusable filtered or joined
        base query.
        """
        return self._repo.select()

    def run(
        self,
        limit: int,
        cursor: str | None = None,
        qry: Select | None = None,
    ) -> tuple[list, str | None]:
        """Return one page and a cursor for the page after it.

        Args:
            limit: Maximum number of rows returned in the page.
            cursor: Cursor returned by the preceding call, or ``None`` for page one.
            qry: Optional one-off base query. It must not already have an order.

        Returns:
            The rows and a cursor for the next page. The cursor is ``None`` on
            the final page.

        Raises:
            KeysetError: If the keyset, query, or cursor is invalid.
        """
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise KeysetError("Keyset.run(): limit must be a positive integer")
        if qry is None:
            qry = self.default_query()
        if not isinstance(qry, Select):
            raise KeysetError("Keyset.run(): qry must be a Select")
        qry = copy.deepcopy(qry)
        if qry.has_order():
            raise KeysetError("Keyset.run(): qry must not already have an ORDER BY")

        dialect = qry.dialect()
        for field in self._fields:
            qry.order(
                Literal(dialect.field(field, None, self._table, self._schema)),
                self._order,
            )

        if cursor is not None:
            values = self._decode(cursor)
            operator = ">" if self._order == self.ASC else "<"
            qry.where_row(self._fields, operator, values, self._table, self._schema)
        rows, has_more = self._repo.seek(qry, limit)
        next_cursor = self._encode(rows[-1]) if has_more and rows else None
        return rows, next_cursor

    def _values_for(self, row: Mapping[str, Any] | object) -> list[Any]:
        """Extract non-null key values from a mapping or Record instance."""
        if isinstance(row, Mapping):
            values = row
        elif hasattr(row, "asrecord"):
            values = row.asrecord()
        else:
            raise KeysetError("Keyset: row must be a mapping or Record")

        result = []
        for field in self._fields:
            if field not in values:
                raise KeysetError("Keyset: keyset field '%s' is not selected" % field)
            if values[field] is None:
                raise KeysetError("Keyset: keyset field '%s' must not be NULL" % field)
            result.append(values[field])
        return result

    def _encode(self, row: Mapping[str, Any] | object) -> str:
        """Encode the last row of a page as a versioned URL-safe cursor."""
        payload = {
            "v": self._CURSOR_VERSION,
            "f": self._fields,
            "o": self._order,
            "k": [_encode_value(value) for value in self._values_for(row)],
        }
        try:
            raw = json.dumps(payload, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise KeysetError("Keyset.encode(): key value cannot be encoded") from exc
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")

    def _decode(self, cursor: str) -> list[Any]:
        """Decode and validate a cursor emitted for this keyset."""
        if not isinstance(cursor, str) or not cursor:
            raise KeysetError("Keyset.decode(): cursor must be a non-empty string")
        try:
            padding = "=" * (-len(cursor) % 4)
            raw = base64.b64decode(
                (cursor + padding).encode("ascii"), altchars=b"-_", validate=True
            ).decode("utf-8")
            payload = json.loads(raw)
        except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
            raise KeysetError("Keyset.decode(): malformed cursor") from exc

        if not isinstance(payload, dict):
            raise KeysetError("Keyset.decode(): malformed cursor")
        if payload.get("v") != self._CURSOR_VERSION:
            raise KeysetError("Keyset.decode(): unsupported cursor version")
        if payload.get("f") != self._fields or payload.get("o") != self._order:
            raise KeysetError("Keyset.decode(): cursor belongs to another keyset")
        values = payload.get("k")
        if not isinstance(values, list) or len(values) != len(self._fields):
            raise KeysetError("Keyset.decode(): malformed cursor")
        return [_decode_value(value) for value in values]


def _encode_value(value: Any) -> Any:
    """Return a JSON-safe cursor representation that preserves driver types."""
    if isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise KeysetError("Keyset.encode(): key values must be finite")
        return value
    if isinstance(value, dt.datetime):
        return {"t": "datetime", "v": value.isoformat()}
    if isinstance(value, dt.date):
        return {"t": "date", "v": value.isoformat()}
    if isinstance(value, dt.time):
        return {"t": "time", "v": value.isoformat()}
    if isinstance(value, decimal.Decimal):
        return {"t": "decimal", "v": str(value)}
    if isinstance(value, uuid.UUID):
        return {"t": "uuid", "v": str(value)}
    raise KeysetError("Keyset.encode(): unsupported key value type")


def _decode_value(value: Any) -> Any:
    """Restore a value produced by :func:`_encode_value`."""
    if value is None or isinstance(value, (list, tuple)):
        raise KeysetError("Keyset.decode(): key values must be scalar and non-null")
    if isinstance(value, (bool, int, float, str)):
        if isinstance(value, float) and not math.isfinite(value):
            raise KeysetError("Keyset.decode(): key values must be finite")
        return value
    if not isinstance(value, dict) or set(value) != {"t", "v"}:
        raise KeysetError("Keyset.decode(): malformed key value")
    try:
        if value["t"] == "datetime":
            return dt.datetime.fromisoformat(value["v"])
        if value["t"] == "date":
            return dt.date.fromisoformat(value["v"])
        if value["t"] == "time":
            return dt.time.fromisoformat(value["v"])
        if value["t"] == "decimal":
            return decimal.Decimal(value["v"])
        if value["t"] == "uuid":
            return uuid.UUID(value["v"])
    except (TypeError, ValueError, decimal.InvalidOperation) as exc:
        raise KeysetError("Keyset.decode(): malformed key value") from exc
    raise KeysetError("Keyset.decode(): malformed key value")
