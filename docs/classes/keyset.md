# Class rick_db.**Keyset**

`Keyset` performs repository-backed forward cursor pagination using SQL
row-value comparison. It is independent of `DbGrid`.

### **Keyset(repo, fields=None, order=Keyset.ASC)**

Create a keyset for *repo*. *fields* is a database field name or ordered list
of database field names; if omitted, the Record primary key is used. *order*
applies to every field and must be `Keyset.ASC` or `Keyset.DESC`.

The fields must be selected, non-null, and collectively unique. A
`KeysetError` is raised for invalid field definitions or directions.

### Keyset.**default_query()**

Returns the base [Select](select.md) used by `run()` when `qry` is omitted.
The default is `repo.select()`. Override this method in a subclass to define a
reusable filtered or joined query.

### Keyset.**run(limit, cursor=None, qry=None)**

Fetch one page and return `(rows, next_cursor)`. Pass `next_cursor` to the next
call; it is `None` for the final page. *limit* must be a positive integer.

*qry* optionally supplies a one-off base [Select](select.md). It must not have
an `ORDER BY`, `LIMIT`, or `OFFSET`, because Keyset owns those clauses. Invalid
inputs and cursors raise `KeysetError`; a base query with a limit or offset is
rejected by `Repository.seek()` with `RepositoryError`.

See the [Keyset pagination guide](../keyset.md) for complete examples and
constraints.

### Class rick_db.**KeysetError**

Subclass of `ValueError` raised for invalid keyset definitions, cursors, and
key values.
