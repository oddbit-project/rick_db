import pytest
from unittest.mock import MagicMock

from rick_db import fieldmapper
from rick_db.sql import ClickHouseSqlDialect, Select, Insert, SqlError
from rick_db.sql.common import Literal
from rick_db.backend.clickhouse.sql import ClickHouseUpdate, ClickHouseDelete
from rick_db.backend.clickhouse.connection import (
    ClickHouseCursorWrapper,
    ClickHouseClientWrapper,
)


# -- Test record for SQL builder tests --

@fieldmapper(tablename="users", pk="id_user")
class UserRecord:
    id = "id_user"
    name = "name"
    email = "email"


# ==========================================
# ClickHouseSqlDialect Tests
# ==========================================

class TestClickHouseSqlDialect:
    def test_placeholder(self):
        d = ClickHouseSqlDialect()
        assert d.placeholder == "%s"

    def test_insert_returning(self):
        d = ClickHouseSqlDialect()
        assert d.insert_returning is False

    def test_ilike(self):
        d = ClickHouseSqlDialect()
        assert d.ilike is True

    def test_json_support(self):
        d = ClickHouseSqlDialect()
        assert d.json_support is True

    def test_table_quoting(self):
        d = ClickHouseSqlDialect()
        assert d.table("mytable") == '"mytable"'
        assert d.table("mytable", "alias") == '"mytable" AS "alias"'
        assert d.table("mytable", schema="mydb") == '"mydb"."mytable"'

    def test_identifier_injection_escape(self):
        d = ClickHouseSqlDialect()
        # embedded double-quotes must be escaped by doubling
        assert d.table('t"; DROP TABLE x; --') == '"t""; DROP TABLE x; --"'
        assert d.field('f"; DROP TABLE x; --') == '"f""; DROP TABLE x; --"'
        assert d.database('d"; DROP TABLE x; --') == '"d""; DROP TABLE x; --"'

    def test_field_quoting(self):
        d = ClickHouseSqlDialect()
        assert d.field("myfield") == '"myfield"'
        assert d.field("myfield", "alias") == '"myfield" AS "alias"'
        assert d.field("myfield", table="mytable") == '"mytable"."myfield"'

    def test_field_cast(self):
        d = ClickHouseSqlDialect()
        assert d.field("myfield", ["String"]) == 'CAST("myfield" AS String)'
        assert (
            d.field("myfield", ["String", "alias"])
            == 'CAST("myfield" AS String) AS "alias"'
        )

    def test_json_extract(self):
        d = ClickHouseSqlDialect()
        result = d.json_extract("data", "name")
        assert result == "JSONExtractString(\"data\", 'name')"

    def test_json_extract_with_jsonpath(self):
        d = ClickHouseSqlDialect()
        result = d.json_extract("data", "$.name")
        assert result == "JSONExtractString(\"data\", 'name')"

    def test_json_extract_with_alias(self):
        d = ClickHouseSqlDialect()
        result = d.json_extract("data", "name", "username")
        assert result == "JSONExtractString(\"data\", 'name') AS \"username\""

    def test_json_extract_text(self):
        d = ClickHouseSqlDialect()
        result = d.json_extract_text("data", "name")
        assert result == "JSONExtractString(\"data\", 'name')"

    def test_json_extract_text_with_alias(self):
        d = ClickHouseSqlDialect()
        result = d.json_extract_text("data", "$.name", "val")
        assert result == "JSONExtractString(\"data\", 'name') AS \"val\""

    def test_json_contains(self):
        d = ClickHouseSqlDialect()
        result = d.json_contains("data", "value")
        assert result == "JSONHas(\"data\", %s)"

    def test_json_contains_path(self):
        d = ClickHouseSqlDialect()
        result = d.json_contains_path("data", "name")
        assert result == "JSON_EXISTS(\"data\", 'name')"


# ==========================================
# ClickHouseUpdate Tests
# ==========================================

class TestClickHouseUpdate:
    def test_simple_update(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseUpdate(d)
            .table("users")
            .values({"name": "Alice"})
            .where("id_user", "=", 1)
            .assemble()
        )
        assert sql == 'ALTER TABLE "users" UPDATE "name"=%s WHERE "id_user" = %s'
        assert values == ["Alice", 1]

    def test_multi_field_update(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseUpdate(d)
            .table("users")
            .values({"name": "Alice", "email": "alice@test.com"})
            .where("id_user", "=", 1)
            .assemble()
        )
        assert sql == (
            'ALTER TABLE "users" UPDATE "name"=%s, "email"=%s WHERE "id_user" = %s'
        )
        assert values == ["Alice", "alice@test.com", 1]

    def test_update_with_schema(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseUpdate(d)
            .table("users", "mydb")
            .values({"name": "Alice"})
            .where("id_user", "=", 1)
            .assemble()
        )
        assert sql == (
            'ALTER TABLE "mydb"."users" UPDATE "name"=%s WHERE "id_user" = %s'
        )
        assert values == ["Alice", 1]

    def test_update_multiple_where(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseUpdate(d)
            .table("users")
            .values({"name": "Alice"})
            .where("id_user", "=", 1)
            .where("email", "=", "old@test.com")
            .assemble()
        )
        assert sql == (
            'ALTER TABLE "users" UPDATE "name"=%s '
            'WHERE "id_user" = %s AND "email" = %s'
        )
        assert values == ["Alice", 1, "old@test.com"]

    def test_update_with_literal_value(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseUpdate(d)
            .table("users")
            .values({"name": Literal("'test'")})
            .where("id_user", "=", 1)
            .assemble()
        )
        assert sql == (
            "ALTER TABLE \"users\" UPDATE \"name\"='test' WHERE \"id_user\" = %s"
        )
        assert values == [1]

    def test_update_empty_fields_raises(self):
        d = ClickHouseSqlDialect()
        with pytest.raises(SqlError, match="field list is empty"):
            ClickHouseUpdate(d).table("users").assemble()

    def test_update_field_value_mismatch_raises(self):
        d = ClickHouseSqlDialect()
        u = ClickHouseUpdate(d).table("users")
        u._fields = ["name", "email"]
        u._values = ["Alice"]
        with pytest.raises(SqlError, match="field and value count mismatch"):
            u.assemble()

    def test_update_with_subquery_value(self):
        d = ClickHouseSqlDialect()
        subquery = Select(d).from_("defaults", ["value"]).where("key", "=", "name")
        sql, values = (
            ClickHouseUpdate(d)
            .table("users")
            .values({"name": subquery})
            .where("id_user", "=", 1)
            .assemble()
        )
        assert "ALTER TABLE" in sql
        assert "UPDATE" in sql
        assert values == ["name", 1]

    def test_update_no_where(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseUpdate(d)
            .table("users")
            .values({"name": "Alice"})
            .assemble()
        )
        assert sql == 'ALTER TABLE "users" UPDATE "name"=%s'
        assert values == ["Alice"]

    def test_delete_no_where(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseDelete(d)
            .from_("users")
            .assemble()
        )
        assert sql == 'ALTER TABLE "users" DELETE'
        assert values == []


# ==========================================
# ClickHouseDelete Tests
# ==========================================

class TestClickHouseDelete:
    def test_simple_delete(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseDelete(d)
            .from_("users")
            .where("id_user", "=", 1)
            .assemble()
        )
        assert sql == 'ALTER TABLE "users" DELETE WHERE "id_user" = %s'
        assert values == [1]

    def test_delete_with_schema(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseDelete(d)
            .from_("users", "mydb")
            .where("id_user", "=", 1)
            .assemble()
        )
        assert sql == 'ALTER TABLE "mydb"."users" DELETE WHERE "id_user" = %s'
        assert values == [1]

    def test_delete_multiple_where(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseDelete(d)
            .from_("users")
            .where("id_user", ">", 0)
            .where("name", "=", "test")
            .assemble()
        )
        assert sql == (
            'ALTER TABLE "users" DELETE WHERE "id_user" > %s AND "name" = %s'
        )
        assert values == [0, "test"]

    def test_delete_or_where(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseDelete(d)
            .from_("users")
            .where("id_user", "=", 1)
            .orwhere("id_user", "=", 2)
            .assemble()
        )
        assert sql == (
            'ALTER TABLE "users" DELETE WHERE "id_user" = %s OR "id_user" = %s'
        )
        assert values == [1, 2]

    def test_delete_from_record(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            ClickHouseDelete(d)
            .from_(UserRecord)
            .where(UserRecord.id, "=", 1)
            .assemble()
        )
        assert sql == 'ALTER TABLE "users" DELETE WHERE "id_user" = %s'
        assert values == [1]


# ==========================================
# Select/Insert with ClickHouse dialect
# ==========================================

class TestClickHouseSelectInsert:
    def test_select(self):
        d = ClickHouseSqlDialect()
        sql, values = Select(d).from_("users", ["id_user", "name"]).assemble()
        assert sql == 'SELECT "id_user","name" FROM "users"'
        assert values == []

    def test_select_where(self):
        d = ClickHouseSqlDialect()
        sql, values = (
            Select(d).from_("users").where("name", "=", "Alice").assemble()
        )
        assert 'FROM "users"' in sql
        assert '"name" = %s' in sql
        assert values == ["Alice"]

    def test_insert(self):
        d = ClickHouseSqlDialect()
        record = UserRecord(name="Alice", email="alice@test.com")
        sql, values = Insert(d).into(record).assemble()
        assert '"users"' in sql
        assert "INSERT INTO" in sql
        assert "RETURNING" not in sql
        assert "Alice" in values
        assert "alice@test.com" in values


# ==========================================
# CursorWrapper Tests
# ==========================================

class TestClickHouseCursorWrapper:
    def _make_query_result(self, column_names, rows):
        result = MagicMock()
        result.column_names = column_names
        result.result_rows = rows
        return result

    def test_select_routes_to_query(self):
        client = MagicMock()
        client.query.return_value = self._make_query_result(
            ["id", "name"], [(1, "Alice"), (2, "Bob")]
        )
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("SELECT * FROM users")
        client.query.assert_called_once()
        client.command.assert_not_called()

    def test_select_returns_dicts(self):
        client = MagicMock()
        client.query.return_value = self._make_query_result(
            ["id", "name"], [(1, "Alice")]
        )
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0] == {"id": 1, "name": "Alice"}

    def test_fetchone_returns_first(self):
        client = MagicMock()
        client.query.return_value = self._make_query_result(
            ["id"], [(1,), (2,)]
        )
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("SELECT id FROM users")
        row = cursor.fetchone()
        assert row == {"id": 1}

    def test_fetchone_returns_none_on_empty(self):
        client = MagicMock()
        client.query.return_value = self._make_query_result([], [])
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("SELECT id FROM users")
        assert cursor.fetchone() is None

    def test_insert_routes_to_command(self):
        client = MagicMock()
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("INSERT INTO users VALUES (%s, %s)", ("Alice", "a@b.com"))
        client.command.assert_called_once()
        client.query.assert_not_called()

    def test_create_routes_to_command(self):
        client = MagicMock()
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("CREATE TABLE test (id UInt32) ENGINE = MergeTree()")
        client.command.assert_called_once()

    def test_alter_routes_to_command(self):
        client = MagicMock()
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("ALTER TABLE users DELETE WHERE id = %s", (1,))
        client.command.assert_called_once()

    def test_show_routes_to_query(self):
        client = MagicMock()
        client.query.return_value = self._make_query_result(["name"], [("db1",)])
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("SHOW DATABASES")
        client.query.assert_called_once()

    def test_describe_routes_to_query(self):
        client = MagicMock()
        client.query.return_value = self._make_query_result(
            ["name", "type"], [("id", "UInt32")]
        )
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("DESCRIBE TABLE users")
        client.query.assert_called_once()

    def test_with_routes_to_query(self):
        client = MagicMock()
        client.query.return_value = self._make_query_result(["x"], [(1,)])
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("WITH 1 AS x SELECT x")
        client.query.assert_called_once()

    def test_description_for_select(self):
        client = MagicMock()
        client.query.return_value = self._make_query_result(
            ["id", "name"], [(1, "Alice")]
        )
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("SELECT * FROM users")
        assert cursor.description == [("id",), ("name",)]

    def test_description_for_insert(self):
        client = MagicMock()
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("INSERT INTO users VALUES (%s)", ("test",))
        assert cursor.description is None

    def test_close_clears_state(self):
        client = MagicMock()
        client.query.return_value = self._make_query_result(
            ["id"], [(1,)]
        )
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("SELECT 1")
        cursor.close()
        assert cursor.fetchall() == []
        assert cursor.description is None

    def test_params_as_list(self):
        client = MagicMock()
        cursor = ClickHouseCursorWrapper(client)
        cursor.execute("INSERT INTO users VALUES (%s)", ["Alice"])
        # Verify params were converted to tuple
        call_args = client.command.call_args
        assert call_args[1]["parameters"] == ("Alice",)


# ==========================================
# ClientWrapper Tests
# ==========================================

class TestClickHouseClientWrapper:
    def test_commit_is_noop(self):
        client = MagicMock()
        wrapper = ClickHouseClientWrapper(client)
        wrapper.commit()  # should not raise

    def test_rollback_is_noop(self):
        client = MagicMock()
        wrapper = ClickHouseClientWrapper(client)
        wrapper.rollback()  # should not raise

    def test_cursor_returns_wrapper(self):
        client = MagicMock()
        wrapper = ClickHouseClientWrapper(client)
        cursor = wrapper.cursor()
        assert isinstance(cursor, ClickHouseCursorWrapper)

    def test_close_calls_client_close(self):
        client = MagicMock()
        wrapper = ClickHouseClientWrapper(client)
        wrapper.close()
        client.close.assert_called_once()

    def test_autocommit_attribute(self):
        client = MagicMock()
        wrapper = ClickHouseClientWrapper(client)
        assert wrapper.autocommit is False


# ==========================================
# ClickHouseConnection Tests (mocked)
# ==========================================

class TestClickHouseConnection:
    def _make_connection(self):
        """Create a ClickHouseConnection using the wrapper directly, bypassing import."""
        from rick_db.backend.clickhouse.connection import (
            ClickHouseConnection,
            ClickHouseClientWrapper,
        )
        from rick_db import Connection

        mock_client = MagicMock()
        wrapper = ClickHouseClientWrapper(mock_client)
        # Build connection directly, bypassing clickhouse_connect import
        conn = Connection.__new__(ClickHouseConnection)
        conn.autocommit = False
        Connection.__init__(conn, None, wrapper, ClickHouseSqlDialect())
        return conn, mock_client

    def test_creates_with_dialect(self):
        conn, _ = self._make_connection()
        assert isinstance(conn.dialect(), ClickHouseSqlDialect)

    def test_client_property(self):
        conn, mock_client = self._make_connection()
        assert conn.client is mock_client

    def test_autocommit_is_false(self):
        conn, _ = self._make_connection()
        assert conn.autocommit is False

    def test_commit_no_error(self):
        conn, _ = self._make_connection()
        conn.commit()  # should not raise

    def test_rollback_no_error(self):
        conn, _ = self._make_connection()
        conn.rollback()  # should not raise

    def test_begin_sets_transaction(self):
        conn, _ = self._make_connection()
        assert conn.in_transaction() is False
        conn.begin()
        assert conn.in_transaction() is True
        conn.commit()
        assert conn.in_transaction() is False
