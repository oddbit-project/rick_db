import pytest

from rick_db.backend.sqlite import Sqlite3Connection

from tests.keyset.common import BaseKeysetIntegrationTest

CREATE_TABLE = """
CREATE TABLE keyset_grid (
    id_keyset_grid INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    content TEXT NOT NULL,
    odd BOOLEAN NOT NULL
)
"""


class TestSqliteKeyset(BaseKeysetIntegrationTest):
    @pytest.fixture
    def conn(self):
        conn = Sqlite3Connection(":memory:")
        with conn.cursor() as cursor:
            cursor.exec(CREATE_TABLE)
            for index in range(1, 100):
                cursor.exec(
                    "INSERT INTO keyset_grid(label, content, odd) VALUES(?, ?, ?)",
                    ["row %d" % index, "tied", index % 2 == 0],
                )
        yield conn
        conn.close()
