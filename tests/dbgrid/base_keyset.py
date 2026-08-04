import pytest
from rick_db import (
    Repository,
    RepositoryError,
    DbGrid,
    Keyset,
    KeysetError,
)
from tests.dbgrid.base_dbgrid import GridRecord


class BaseKeysetTest:
    """
    Keyset pagination, exercised against every backend that ships a Repository.

    Split out of BaseDbGridTest so ClickHouse can run it: the search half of the
    grid suite leans on LIKE/ILIKE semantics and an autoincrement pk that a
    MergeTree table does not have, but the seek path is backend-agnostic and is
    precisely the part that must be proven on each one — ClickHouseRepository
    inherits seek() and nothing was covering it.
    """

    label = "this is label %s"

    # A self-join is the cheapest way to guarantee the keyset column name also
    # exists on the other side of the join, which is the ambiguity being tested.
    # ClickHouse rejects `SELECT grid.* FROM grid JOIN grid AS grid_2` outright
    # with AMBIGUOUS_IDENTIFIER — a limitation of the self-join, not of the
    # keyset — so that backend opts out rather than the assertion being weakened.
    supports_self_join = True

    def _repo(self, conn):
        """Repository for this backend; ClickHouse overrides it."""
        return Repository(conn, GridRecord)

    def _walk(self, grid, limit, **kwargs):
        """Page through the whole result set, returning (rows, page_count)."""
        rows = []
        cursor = None
        pages = 0
        while True:
            page, cursor = grid.run_seek(limit=limit, cursor=cursor, **kwargs)
            rows.extend(page)
            pages += 1
            if cursor is None:
                break
            assert pages < 500, "run_seek() did not terminate"
        return rows, pages

    def test_seek_walks_every_row_exactly_once(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo)
        rows, pages = self._walk(grid, 10)
        assert len(rows) == 99
        assert pages == 10
        ids = [r.id for r in rows]
        assert ids == sorted(ids)
        assert len(set(ids)) == 99

    def test_seek_descending_walks_every_row_exactly_once(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo)
        ks = Keyset(GridRecord.id, Keyset.DESC, unique=True)
        rows, _ = self._walk(grid, 7, keyset=ks)
        ids = [r.id for r in rows]
        assert ids == sorted(ids, reverse=True)
        assert len(set(ids)) == 99

    def test_seek_on_a_non_unique_column_needs_the_tiebreaker(self, conn):
        # `content` is identical on all 99 rows, so the entire walk rests on the
        # pk tiebreaker; without it a page boundary would repeat or skip rows
        repo = self._repo(conn)
        grid = DbGrid(repo)
        ks = Keyset([GridRecord.content], pk=GridRecord.id)
        assert ks.fields == [GridRecord.content, GridRecord.id]
        rows, _ = self._walk(grid, 10, keyset=ks)
        ids = [r.id for r in rows]
        assert len(ids) == 99
        assert len(set(ids)) == 99
        assert ids == sorted(ids)

    def test_seek_last_page_returns_a_null_cursor(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo)
        rows, cursor = grid.run_seek(limit=99)
        assert len(rows) == 99
        assert cursor is None

    def test_seek_page_smaller_than_limit_returns_a_null_cursor(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo)
        rows, cursor = grid.run_seek(limit=200)
        assert len(rows) == 99
        assert cursor is None

    def test_seek_respects_search_and_match(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo, [GridRecord.label])
        rows, _ = self._walk(grid, 5, search_text="9")
        assert len(rows) == 19
        rows, _ = self._walk(grid, 5, match_fields={GridRecord.odd: True})
        assert len(rows) == 49
        for r in rows:
            assert r.odd in (True, 1)

    def test_seek_does_not_lose_rows_across_a_page_boundary(self, conn):
        # walk in every page size that divides awkwardly into 99
        repo = self._repo(conn)
        grid = DbGrid(repo)
        for limit in (1, 2, 3, 7, 98, 99, 100):
            rows, _ = self._walk(grid, limit)
            assert len(rows) == 99, "lost rows at limit=%d" % limit
            assert len(set(r.id for r in rows)) == 99

    def test_seek_pages_match_a_plain_ordered_read(self, conn):
        # the traversal order must be exactly what ORDER BY would have produced
        repo = self._repo(conn)
        grid = DbGrid(repo)
        expected = [r.id for r in repo.fetch(repo.select().order(GridRecord.id, "ASC"))]
        rows, _ = self._walk(grid, 6)
        assert [r.id for r in rows] == expected

    def test_seek_rejects_a_bad_limit(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo)
        for bad in (0, -1, None, "10", True):
            with pytest.raises(ValueError):
                grid.run_seek(limit=bad)

    def test_seek_rejects_an_unknown_keyset_field(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo)
        with pytest.raises(ValueError):
            grid.run_seek(limit=10, keyset=Keyset("_nofield", unique=True))

    def test_seek_rejects_a_cursor_from_another_ordering(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo)
        _, cursor = grid.run_seek(
            limit=10, keyset=Keyset(GridRecord.id, Keyset.ASC, unique=True)
        )
        assert cursor is not None
        with pytest.raises(KeysetError):
            grid.run_seek(
                limit=10,
                cursor=cursor,
                keyset=Keyset(GridRecord.id, Keyset.DESC, unique=True),
            )

    def test_seek_ignores_the_default_sort(self, conn):
        # default_sort() is pk ASC; a DESC keyset must not be contradicted by it
        repo = self._repo(conn)
        grid = DbGrid(repo)
        rows, _ = grid.run_seek(
            limit=5, keyset=Keyset(GridRecord.id, Keyset.DESC, unique=True)
        )
        assert [r.id for r in rows] == [99, 98, 97, 96, 95]

    def test_seek_refuses_a_pre_ordered_query(self, conn):
        # the keyset owns the ordering; a sort ahead of it would leave the seek
        # predicate advancing on a trailing term and silently lose rows
        repo = self._repo(conn)
        grid = DbGrid(repo)
        with pytest.raises(KeysetError):
            grid.run_seek(limit=5, qry=repo.select().order(GridRecord.label, "ASC"))

    def test_seek_does_not_accumulate_clauses_when_a_query_is_reused(self, conn):
        # paging is a loop; a caller-held query must not grow a WHERE group and
        # an ORDER BY term per page
        repo = self._repo(conn)
        grid = DbGrid(repo)
        qry = repo.select()
        cursor = None
        for _ in range(4):
            _, cursor = grid.run_seek(limit=10, cursor=cursor, qry=qry)
        sql, values = qry.assemble()
        assert "WHERE" not in sql
        assert sql.count("ORDER BY") == 0
        assert values == []

    def test_seek_refuses_a_query_that_already_has_a_limit(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo)
        with pytest.raises(RepositoryError):
            grid.run_seek(limit=5, qry=repo.select().limit(3, 10))

    def test_repository_seek_reports_has_more(self, conn):
        repo = self._repo(conn)
        qry = repo.select().order(GridRecord.id, "ASC")
        rows, has_more = repo.seek(qry, 10)
        assert len(rows) == 10
        assert has_more is True
        rows, has_more = repo.seek(qry, 99)
        assert len(rows) == 99
        assert has_more is False
        rows, has_more = repo.seek(qry, 150)
        assert len(rows) == 99
        assert has_more is False

    def test_repository_seek_issues_no_count(self, conn):
        # the whole point of seek(): list() runs a COUNT(*) per call, seek() must not.
        # Spy at the CURSOR, not at fetch() — list() issues its count through
        # self.cursor().fetchone(), so a fetch()-level spy would never see one.
        repo = self._repo(conn)
        executed = []
        original_cursor = repo.cursor

        class _Spy:
            def __init__(self, inner):
                self._inner = inner

            def __enter__(self):
                self._c = self._inner.__enter__()
                outer = self

                class _Wrap:
                    def __getattr__(self, name):
                        attr = getattr(outer._c, name)
                        if not callable(attr):
                            return attr

                        def call(*args, **kwargs):
                            if args and isinstance(args[0], str):
                                executed.append(args[0])
                            return attr(*args, **kwargs)

                        return call

                return _Wrap()

            def __exit__(self, *a):
                return self._inner.__exit__(*a)

        repo.cursor = lambda *a, **kw: _Spy(original_cursor(*a, **kw))
        try:
            rows, has_more = repo.seek(repo.select().order(GridRecord.id, "ASC"), 10)
            seek_sql = list(executed)
            executed.clear()
            repo.list(repo.select().order(GridRecord.id, "ASC"), limit=10)
            list_sql = list(executed)
        finally:
            repo.cursor = original_cursor

        assert len(rows) == 10
        assert has_more is True
        # the control: list() DOES count, so the spy is proven to observe counts
        assert any("COUNT(*)" in sql.upper() for sql in list_sql)
        assert not any("COUNT(*)" in sql.upper() for sql in seek_sql)

    def test_seek_does_not_mutate_a_cached_default_query(self, conn):
        # default_query() is a documented override point and may return a shared
        # Select; mutating it would corrupt both the next page and run()
        repo = self._repo(conn)

        class Cached(DbGrid):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._cached = self._repo.select()

            def default_query(self):
                return self._cached

        grid = Cached(repo)
        rows, cursor = grid.run_seek(limit=5)
        assert [r.id for r in rows] == [1, 2, 3, 4, 5]
        rows, _ = grid.run_seek(limit=5, cursor=cursor)
        assert [r.id for r in rows] == [6, 7, 8, 9, 10]
        assert grid._cached.has_order() is False
        # run() must not poison the shared query either: it mutated it in place
        # before, leaving an ORDER BY that made every later run_seek() refuse it
        total, _ = grid.run(limit=5)
        assert total == 99
        grid.run(limit=5)
        assert grid._cached.has_order() is False
        rows, _ = grid.run_seek(limit=5)
        assert [r.id for r in rows] == [1, 2, 3, 4, 5]

    def test_seek_pages_a_joined_query(self, conn):
        if not self.supports_self_join:
            pytest.skip("backend cannot express a self-join over SELECT t.*")

        # keyset fields are table-qualified from the Record, so a join whose
        # other side carries the same column name is not ambiguous. Unqualified,
        # this passed on page 1 and failed on page 2 — ORDER BY resolves against
        # the output columns and WHERE does not.
        repo = self._repo(conn)
        grid = DbGrid(repo)

        def joined():
            return repo.select().join("grid", "id_grid", "grid", "id_grid")

        rows, cursor = grid.run_seek(limit=10, qry=joined())
        assert [r.id for r in rows] == list(range(1, 11))
        assert cursor is not None
        # page 2 is the one that used to raise
        rows, _ = grid.run_seek(limit=10, cursor=cursor, qry=joined())
        assert [r.id for r in rows] == list(range(11, 21))

    def test_seek_qualifies_its_fields(self, conn):
        repo = self._repo(conn)
        grid = DbGrid(repo)
        keyset = grid.default_keyset()
        assert keyset.table == "grid"
        sql, _ = keyset.apply(repo.select(), [1]).assemble()
        assert "grid" in sql and "id_grid" in sql

    def test_seek_refuses_a_non_select(self, conn):
        repo = self._repo(conn)
        with pytest.raises(RepositoryError, match="must be a Select"):
            repo.seek("not a select", 10)
