import os

import pytest

from rick_db.backend.clickhouse import ClickHouseConnection, ClickHouseRepository
from tests.dbgrid.base_dbgrid import GridRecord
from tests.dbgrid.base_keyset import BaseKeysetTest

# MergeTree, ordered by the pk: ClickHouse has no autoincrement, so the ids the
# keyset walks are supplied explicitly. `content` is identical on every row on
# purpose — the tiebreaker test depends on it.
create_table = """
CREATE TABLE IF NOT EXISTS grid (
    id_grid UInt32,
    label String DEFAULT '',
    content String DEFAULT '',
    odd UInt8 DEFAULT 0
) ENGINE = MergeTree()
ORDER BY id_grid
"""
drop_table = "DROP TABLE IF EXISTS grid"


class TestClickHouseKeyset(BaseKeysetTest):
    """
    The seek path on ClickHouse.

    ClickHouseRepository inherits seek() unchanged, and until this existed
    nothing exercised it — the keyset walk was proven on SQLite and PostgreSQL
    only, while the CHANGELOG's portability argument for the expanded OR-chain
    predicate (rather than row-value comparison) rests on exactly this backend.
    """

    @pytest.fixture
    def conn(self, ch_settings):
        try:
            conn = ClickHouseConnection(**ch_settings)
        except Exception as e:  # pragma: no cover - environment guard
            # Skipping is a convenience for a developer without Docker. In CI it
            # would be a green build proving nothing, so there it is a failure:
            # coverage that silently disappears is worse than none, because
            # nobody goes looking for it.
            if os.environ.get("CI"):
                raise
            pytest.skip("ClickHouse not available: %s" % e)

        with conn.cursor() as c:
            c.exec(drop_table)
            c.exec(create_table)
            rows = [
                {
                    "id_grid": i,
                    "label": self.label % i,
                    "content": "mickey mouse",
                    "odd": 1 if (i % 2) == 0 else 0,
                }
                for i in range(1, 100)
            ]
            conn.client.insert(
                "grid",
                [[r[k] for k in ("id_grid", "label", "content", "odd")] for r in rows],
                column_names=["id_grid", "label", "content", "odd"],
            )

        yield conn

        with conn.cursor() as c:
            c.exec(drop_table)
        conn.close()

    def _repo(self, conn):
        return ClickHouseRepository(conn, GridRecord)
