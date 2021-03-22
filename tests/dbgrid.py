import pytest

from rick_db import Repository, fieldmapper, DbGrid


@fieldmapper(tablename='grid', pk='id_grid')
class GridRecord:
    id = 'id_grid'
    label = 'label'
    odd = 'odd'


class DbGridTest:
    label = "this is label %s"

    def test_grid_exceptions(self, conn):
        repo = Repository(conn, GridRecord)
        with pytest.raises(ValueError):
            DbGrid(repo, search_type=9)

        with pytest.raises(ValueError):
            DbGrid(repo, search_fields=['_nolabel'])

        grid = DbGrid(repo)
        with pytest.raises(RuntimeError):
            grid.run(search_text='abc')

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
        total, rows = grid.run(search_text='99')
        assert total == 1
        assert len(rows) == 1

        total, rows = grid.run(search_text='9')
        assert total == 19
        assert len(rows) == 19

        total, rows = grid.run(search_text='abel')
        assert total == 99
        assert len(rows) == 99

        total, rows = grid.run(search_text='that')
        assert total == 0
        assert len(rows) == 0

        # SEARCH_START
        grid = DbGrid(repo, [GridRecord.label], DbGrid.SEARCH_START)
        total, rows = grid.run(search_text='thi')
        assert total == 99
        assert len(rows) == 99

        total, rows = grid.run(search_text='is')
        assert total == 0
        assert len(rows) == 0

        # SEARCH_END
        grid = DbGrid(repo, [GridRecord.label], DbGrid.SEARCH_END)
        total, rows = grid.run(search_text='13')
        assert total == 1
        assert len(rows) == 1

        total, rows = grid.run(search_text='3')
        assert total == 10
        assert len(rows) == 10

        # SEARCH_NONE
        grid = DbGrid(repo, [GridRecord.label], search_type=DbGrid.SEARCH_NONE)
        with pytest.raises(RuntimeError):
            total, rows = grid.run(search_text='13')

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
        total, rows = grid.run(limit=10, sort_fields={GridRecord.label: 'desc'})
        assert total == 99
        assert rows[0].label == self.label % 99
        assert rows[-1].label == self.label % 90

        total, rows = grid.run(limit=10, offset=5, sort_fields={GridRecord.label: 'desc'})
        assert total == 99
        assert len(rows) == 10
        assert rows[0].label == self.label % 94
        assert rows[-1].label == self.label % 86

    def test_dbgrid_match(self, conn):
        repo = Repository(conn, GridRecord)
        # SEARCH_ANY
        grid = DbGrid(repo, [GridRecord.label])
        total, rows = grid.run(search_text='98', match_fields={GridRecord.odd: True})
        assert total == 1
        assert len(rows) == 1
        total, rows = grid.run(search_text='99', match_fields={GridRecord.odd: False})
        assert total == 1
        assert len(rows) == 1
        total, rows = grid.run(search_text='99', match_fields={GridRecord.odd: True})
        assert total == 0
        assert len(rows) == 0
        total, rows = grid.run(match_fields={GridRecord.id: 46, GridRecord.odd: True})
        assert total == 1
        assert len(rows) == 1
        total, rows = grid.run(match_fields={GridRecord.id: 46, GridRecord.odd: False})
        assert total == 0
        assert len(rows) == 0
