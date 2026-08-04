import pytest

from rick_db import Keyset, KeysetError, Repository, fieldmapper


@fieldmapper(tablename="keyset_grid", pk="id_keyset_grid")
class KeysetRecord:
    id = "id_keyset_grid"
    label = "label"
    content = "content"
    odd = "odd"


class BaseKeysetIntegrationTest:
    """Integration contract executed by every supported database backend."""

    odd_value = True

    def _repo(self, conn):
        return Repository(conn, KeysetRecord)

    def _walk(self, keyset, limit, qry=None):
        rows = []
        cursor = None
        while True:
            page, cursor = keyset.run(limit, cursor=cursor, qry=qry)
            rows.extend(page)
            if cursor is None:
                return rows

    def test_walks_every_row_once(self, conn):
        rows = self._walk(Keyset(self._repo(conn)), 7)

        assert [row.id for row in rows] == list(range(1, 100))

    def test_uses_all_keyset_fields_at_tie_boundaries(self, conn):
        repo = self._repo(conn)
        rows = self._walk(Keyset(repo, [KeysetRecord.content, KeysetRecord.id]), 7)

        assert len(rows) == 99
        assert len({row.id for row in rows}) == 99

    def test_supports_descending_order(self, conn):
        rows = self._walk(Keyset(self._repo(conn), KeysetRecord.id, Keyset.DESC), 10)

        assert [row.id for row in rows] == list(range(99, 0, -1))

    def test_accepts_an_explicit_base_query(self, conn):
        repo = self._repo(conn)
        qry = repo.select().where(KeysetRecord.odd, "=", self.odd_value)

        rows = self._walk(Keyset(repo), 5, qry=qry)

        assert [row.id for row in rows] == list(range(2, 100, 2))

    def test_subclass_can_override_default_query_without_mutation(self, conn):
        repo = self._repo(conn)
        odd_value = self.odd_value

        class OddRows(Keyset):
            def __init__(self, repository):
                super().__init__(repository)
                self._query = repository.select().where(
                    KeysetRecord.odd, "=", odd_value
                )

            def default_query(self):
                return self._query

        keyset = OddRows(repo)
        rows = self._walk(keyset, 5)

        assert [row.id for row in rows] == list(range(2, 100, 2))
        sql, values = keyset._query.assemble()
        assert "ORDER BY" not in sql
        assert values == [self.odd_value]

    def test_rejects_invalid_limit(self, conn):
        with pytest.raises(KeysetError):
            Keyset(self._repo(conn)).run(0)
