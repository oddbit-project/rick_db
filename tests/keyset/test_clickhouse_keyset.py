import pytest

from rick_db.backend.clickhouse import ClickHouseConnection, ClickHouseRepository

from tests.keyset.common import BaseKeysetIntegrationTest, KeysetRecord

CREATE_TABLE = """
CREATE TABLE keyset_grid (
    id_keyset_grid UInt32,
    label String,
    content String,
    odd UInt8
) ENGINE = MergeTree()
ORDER BY (content, id_keyset_grid)
"""


class TestClickHouseKeyset(BaseKeysetIntegrationTest):
    odd_value = 1

    def _repo(self, conn):
        return ClickHouseRepository(conn, KeysetRecord)

    @pytest.fixture
    def conn(self, ch_settings):
        conn = ClickHouseConnection(**ch_settings)
        with conn.cursor() as cursor:
            cursor.exec("DROP TABLE IF EXISTS keyset_grid")
            cursor.exec(CREATE_TABLE)
            for index in range(1, 100):
                cursor.exec(
                    "INSERT INTO keyset_grid(id_keyset_grid, label, content, odd) VALUES (%s, %s, %s, %s)",
                    [index, "row %d" % index, "tied", int(index % 2 == 0)],
                )
        yield conn
        with conn.cursor() as cursor:
            cursor.exec("DROP TABLE IF EXISTS keyset_grid")
        conn.close()
