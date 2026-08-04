import pytest
from rick_db import (
    Repository,
    RepositoryError,
    fieldmapper,
    DbGrid,
    Keyset,
    KeysetError,
)


@fieldmapper(tablename="grid", pk="id_grid")
class GridRecord:
    id = "id_grid"
    label = "label"
    content = "content"
    odd = "odd"


class BaseDbGridTest:
    label = "this is label %s"

    def test_grid_exceptions(self, conn):
        repo = Repository(conn, GridRecord)
        with pytest.raises(ValueError):
            DbGrid(repo, search_type=9)

        with pytest.raises(ValueError):
            DbGrid(repo, search_fields=["_nolabel"])

        grid = DbGrid(repo)
        with pytest.raises(RuntimeError):
            grid.run(search_text="abc")

    def test_grid_noparams(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        total, rows = grid.run()
        assert total == 99
        assert len(rows) == 99
        i = 1
        for r in rows:
            assert r.label == (self.label % i)
            i += 1

    def test_grid_search(self, conn):
        repo = Repository(conn, GridRecord)
        # SEARCH_ANY
        grid = DbGrid(repo, [GridRecord.label])
        total, rows = grid.run(search_text="99")
        assert total == 1
        assert len(rows) == 1

        total, rows = grid.run(search_text="9")
        assert total == 19
        assert len(rows) == 19

        total, rows = grid.run(search_text="abel")
        assert total == 99
        assert len(rows) == 99

        total, rows = grid.run(search_text="that")
        assert total == 0
        assert len(rows) == 0

        # SEARCH_START
        grid = DbGrid(repo, [GridRecord.label], DbGrid.SEARCH_START)
        total, rows = grid.run(search_text="thi")
        assert total == 99
        assert len(rows) == 99

        total, rows = grid.run(search_text="is")
        assert total == 0
        assert len(rows) == 0

        # SEARCH_END
        grid = DbGrid(repo, [GridRecord.label], DbGrid.SEARCH_END)
        total, rows = grid.run(search_text="13")
        assert total == 1
        assert len(rows) == 1

        total, rows = grid.run(search_text="3")
        assert total == 10
        assert len(rows) == 10

        # SEARCH_NONE
        grid = DbGrid(repo, [GridRecord.label], search_type=DbGrid.SEARCH_NONE)
        with pytest.raises(RuntimeError):
            total, rows = grid.run(search_text="13")

    def test_grid_limit(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo, [GridRecord.label])
        total, rows = grid.run(limit=10)
        assert total == 99
        assert rows[0].label == self.label % 1
        assert rows[-1].label == self.label % 10

        total, rows = grid.run(limit=10, offset=5)
        assert total == 99
        assert len(rows) == 10
        assert rows[0].label == self.label % 6
        assert rows[-1].label == self.label % 15

    def test_grid_sort(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo, [GridRecord.label])
        total, rows = grid.run(limit=10, sort_fields={GridRecord.label: "desc"})
        assert total == 99
        assert rows[0].label == self.label % 99
        assert rows[-1].label == self.label % 90

        total, rows = grid.run(
            limit=10, offset=5, sort_fields={GridRecord.label: "desc"}
        )
        assert total == 99
        assert len(rows) == 10
        assert rows[0].label == self.label % 94
        assert rows[-1].label == self.label % 86

    def test_dbgrid_match(self, conn):
        repo = Repository(conn, GridRecord)
        # SEARCH_ANY
        grid = DbGrid(repo, [GridRecord.label])
        total, rows = grid.run(search_text="98", match_fields={GridRecord.odd: True})
        assert total == 1
        assert len(rows) == 1
        total, rows = grid.run(search_text="99", match_fields={GridRecord.odd: False})
        assert total == 1
        assert len(rows) == 1
        total, rows = grid.run(search_text="99", match_fields={GridRecord.odd: True})
        assert total == 0
        assert len(rows) == 0
        total, rows = grid.run(match_fields={GridRecord.id: 46, GridRecord.odd: True})
        assert total == 1
        assert len(rows) == 1
        total, rows = grid.run(match_fields={GridRecord.id: 46, GridRecord.odd: False})
        assert total == 0
        assert len(rows) == 0

    # ------------------------------------------------------------------ #
    # keyset (cursor) pagination                                          #
    # ------------------------------------------------------------------ #

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
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        rows, pages = self._walk(grid, 10)
        assert len(rows) == 99
        assert pages == 10
        ids = [r.id for r in rows]
        assert ids == sorted(ids)
        assert len(set(ids)) == 99

    def test_seek_descending_walks_every_row_exactly_once(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        ks = Keyset(GridRecord.id, Keyset.DESC, unique=True)
        rows, _ = self._walk(grid, 7, keyset=ks)
        ids = [r.id for r in rows]
        assert ids == sorted(ids, reverse=True)
        assert len(set(ids)) == 99

    def test_seek_on_a_non_unique_column_needs_the_tiebreaker(self, conn):
        # `content` is identical on all 99 rows, so the entire walk rests on the
        # pk tiebreaker; without it a page boundary would repeat or skip rows
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        ks = Keyset([GridRecord.content], pk=GridRecord.id)
        assert ks.fields == [GridRecord.content, GridRecord.id]
        rows, _ = self._walk(grid, 10, keyset=ks)
        ids = [r.id for r in rows]
        assert len(ids) == 99
        assert len(set(ids)) == 99
        assert ids == sorted(ids)

    def test_seek_last_page_returns_a_null_cursor(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        rows, cursor = grid.run_seek(limit=99)
        assert len(rows) == 99
        assert cursor is None

    def test_seek_page_smaller_than_limit_returns_a_null_cursor(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        rows, cursor = grid.run_seek(limit=200)
        assert len(rows) == 99
        assert cursor is None

    def test_seek_respects_search_and_match(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo, [GridRecord.label])
        rows, _ = self._walk(grid, 5, search_text="9")
        assert len(rows) == 19
        rows, _ = self._walk(grid, 5, match_fields={GridRecord.odd: True})
        assert len(rows) == 49
        for r in rows:
            assert r.odd in (True, 1)

    def test_seek_does_not_lose_rows_across_a_page_boundary(self, conn):
        # walk in every page size that divides awkwardly into 99
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        for limit in (1, 2, 3, 7, 98, 99, 100):
            rows, _ = self._walk(grid, limit)
            assert len(rows) == 99, "lost rows at limit=%d" % limit
            assert len(set(r.id for r in rows)) == 99

    def test_seek_pages_match_a_plain_ordered_read(self, conn):
        # the traversal order must be exactly what ORDER BY would have produced
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        expected = [r.id for r in repo.fetch(repo.select().order(GridRecord.id, "ASC"))]
        rows, _ = self._walk(grid, 6)
        assert [r.id for r in rows] == expected

    def test_seek_rejects_a_bad_limit(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        for bad in (0, -1, None, "10", True):
            with pytest.raises(ValueError):
                grid.run_seek(limit=bad)

    def test_seek_rejects_an_unknown_keyset_field(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        with pytest.raises(ValueError):
            grid.run_seek(limit=10, keyset=Keyset("_nofield", unique=True))

    def test_seek_rejects_a_cursor_from_another_ordering(self, conn):
        repo = Repository(conn, GridRecord)
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
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        rows, _ = grid.run_seek(
            limit=5, keyset=Keyset(GridRecord.id, Keyset.DESC, unique=True)
        )
        assert [r.id for r in rows] == [99, 98, 97, 96, 95]

    def test_seek_refuses_a_pre_ordered_query(self, conn):
        # the keyset owns the ordering; a sort ahead of it would leave the seek
        # predicate advancing on a trailing term and silently lose rows
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        with pytest.raises(KeysetError):
            grid.run_seek(limit=5, qry=repo.select().order(GridRecord.label, "ASC"))

    def test_seek_does_not_accumulate_clauses_when_a_query_is_reused(self, conn):
        # paging is a loop; a caller-held query must not grow a WHERE group and
        # an ORDER BY term per page
        repo = Repository(conn, GridRecord)
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
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo)
        with pytest.raises(RepositoryError):
            grid.run_seek(limit=5, qry=repo.select().limit(3, 10))

    def test_repository_seek_reports_has_more(self, conn):
        repo = Repository(conn, GridRecord)
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
        repo = Repository(conn, GridRecord)
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

    def test_seek_refuses_a_null_keyset_value(self, conn):
        # A NULL key is excluded by the seek predicate on every page after the
        # first, so the walk would otherwise end short with no error at all.
        # The page size is the whole table on purpose: where a backend sorts
        # NULLs (last on PostgreSQL ASC, first on SQLite) decides whether the
        # row is ever returned, and this asserts the detection, not the
        # ordering. That is also the limitation — under an ordering that sorts
        # them past the cursor, nothing can see them.
        repo = Repository(conn, GridRecord)
        with repo.cursor() as c:
            c.exec("update grid set content = null where id_grid = 3")
        try:
            grid = DbGrid(repo)
            ks = Keyset([GridRecord.content], pk=GridRecord.id)
            with pytest.raises(KeysetError, match="NULL"):
                grid.run_seek(limit=200, keyset=ks)
        finally:
            with repo.cursor() as c:
                c.exec("update grid set content = 'mickey mouse' where id_grid = 3")

    def test_seek_does_not_mutate_a_cached_default_query(self, conn):
        # default_query() is a documented override point and may return a shared
        # Select; mutating it would corrupt both the next page and run()
        repo = Repository(conn, GridRecord)

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
        total, _ = grid.run(limit=5)
        assert total == 99
