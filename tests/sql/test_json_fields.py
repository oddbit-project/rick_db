import pytest

from rick_db.sql import (
    Select,
    Literal,
    PgSqlDialect,
    DefaultSqlDialect,
    JsonField,
    PgJsonField,
    SqlError,
)
from rick_db.sql.dialect import SqlDialect, Sqlite3SqlDialect


class TestBaseSqlDialectJson:
    """Test base SqlDialect JSON methods with json_support enabled.

    These tests exercise the base class code paths (lines 179-192, 211-224,
    248, 280) that are normally skipped because PgSqlDialect overrides
    json_extract/json_extract_text.
    """

    def setup_method(self):
        self.dialect = SqlDialect()
        self.dialect.json_support = True

    def test_json_extract(self):
        result = self.dialect.json_extract("data", "$.name")
        assert result == "JSON_EXTRACT(\"data\", '$.name')"

    def test_json_extract_with_alias(self):
        result = self.dialect.json_extract("data", "$.name", "username")
        assert result == 'JSON_EXTRACT("data", \'$.name\') AS "username"'

    def test_json_extract_pre_quoted_path(self):
        result = self.dialect.json_extract("data", "'$.name'")
        assert result == "JSON_EXTRACT(\"data\", '$.name')"

    def test_json_extract_table_qualified(self):
        result = self.dialect.json_extract("t.data", "$.name")
        assert result == "JSON_EXTRACT(\"t\".\"data\", '$.name')"

    def test_json_extract_literal(self):
        result = self.dialect.json_extract(Literal("my_func()"), "$.name")
        assert result == "JSON_EXTRACT(my_func(), '$.name')"

    def test_json_extract_text(self):
        result = self.dialect.json_extract_text("data", "$.name")
        assert result == "JSON_EXTRACT(\"data\", '$.name')"

    def test_json_extract_text_with_alias(self):
        result = self.dialect.json_extract_text("data", "$.name", "username")
        assert result == 'JSON_EXTRACT("data", \'$.name\') AS "username"'

    def test_json_extract_text_pre_quoted_path(self):
        result = self.dialect.json_extract_text("data", "'$.name'")
        assert result == "JSON_EXTRACT(\"data\", '$.name')"

    def test_json_contains_with_alias(self):
        result = self.dialect.json_contains("data", "val", "has_val")
        assert result == 'JSON_CONTAINS("data", ?) AS "has_val"'

    def test_json_contains_path_with_alias(self):
        result = self.dialect.json_contains_path("data", "$.name", "has_name")
        assert result == "JSON_CONTAINS_PATH(\"data\", 'one', '$.name') AS \"has_name\""

    def test_json_contains_path_pre_quoted(self):
        result = self.dialect.json_contains_path("data", "'$.name'")
        assert result == "JSON_CONTAINS_PATH(\"data\", 'one', '$.name')"


class TestSqlDialectFieldErrors:
    """Test SqlDialect.field() and database() error/edge branches"""

    def test_field_empty_alias_list_raises(self):
        dialect = SqlDialect()
        with pytest.raises(SqlError):
            dialect.field("col", [])

    def test_field_invalid_alias_type_raises(self):
        dialect = SqlDialect()
        with pytest.raises(SqlError):
            dialect.field("col", 123)

    def test_database_literal(self):
        dialect = SqlDialect()
        result = dialect.database(Literal("db_func()"))
        assert result == "(db_func())"

    def test_database_literal_with_alias(self):
        dialect = SqlDialect()
        result = dialect.database(Literal("db_func()"), "mydb")
        assert result == '(db_func()) AS "mydb"'


class TestPgSqlDialectFieldErrors:
    """Test PgSqlDialect.field() error branches"""

    def test_field_empty_alias_list_raises(self):
        dialect = PgSqlDialect()
        with pytest.raises(SqlError):
            dialect.field("col", [])

    def test_field_invalid_alias_type_raises(self):
        dialect = PgSqlDialect()
        with pytest.raises(SqlError):
            dialect.field("col", 123)


class TestJsonFieldDefault:
    """Test JsonField with default (non-JSON) dialect"""

    def test_extract_no_dialect(self):
        jf = JsonField("data")
        result = jf.extract("$.name")
        assert str(result) == "JSON_EXTRACT(data, '$.name')"

    def test_extract_text_no_dialect(self):
        jf = JsonField("data")
        result = jf.extract_text("$.name")
        assert str(result) == "JSON_EXTRACT(data, '$.name')"

    def test_contains_no_dialect(self):
        jf = JsonField("data")
        result = jf.contains('"value"')
        assert str(result) == "JSON_CONTAINS(data, ?)"

    def test_has_path_no_dialect(self):
        jf = JsonField("data")
        result = jf.has_path("$.name")
        assert str(result) == "JSON_CONTAINS_PATH(data, 'one', '$.name')"

    def test_getitem_no_dialect(self):
        jf = JsonField("data")
        result = jf["name"]
        assert isinstance(result, JsonField)
        assert not isinstance(result, PgJsonField)
        assert result.field_name == "JSON_EXTRACT(data, '$.name')"

    def test_str(self):
        jf = JsonField("data")
        assert str(jf) == "data"

    def test_with_non_json_dialect(self):
        """JsonField with a dialect that has json_support=False falls back to generic SQL"""
        dialect = DefaultSqlDialect()
        jf = JsonField("data", dialect)
        result = jf.extract("$.name")
        assert str(result) == "JSON_EXTRACT(data, '$.name')"

    def test_with_sqlite_dialect(self):
        """Sqlite3SqlDialect has json_support=False, so falls back to generic SQL"""
        dialect = Sqlite3SqlDialect()
        jf = JsonField("data", dialect)
        result = jf.extract("$.name")
        assert str(result) == "JSON_EXTRACT(data, '$.name')"


class TestPgSqlDialectJson:
    """Test PgSqlDialect JSON helpers directly"""

    def setup_method(self):
        self.dialect = PgSqlDialect()

    def test_json_extract_simple_key(self):
        result = self.dialect.json_extract("data", "name")
        assert result == "\"data\"->>'name'"

    def test_json_extract_strips_jsonpath_prefix(self):
        result = self.dialect.json_extract("data", "$.name")
        assert result == "\"data\"->>'name'"

    def test_json_extract_numeric_index(self):
        result = self.dialect.json_extract("data", 0)
        assert result == '"data"->>0'

    def test_json_extract_numeric_string_index(self):
        result = self.dialect.json_extract("data", "0")
        assert result == '"data"->>0'

    def test_json_extract_with_alias(self):
        result = self.dialect.json_extract("data", "name", "username")
        assert result == '"data"->>\'name\' AS "username"'

    def test_json_extract_table_qualified(self):
        result = self.dialect.json_extract("t.data", "name")
        assert result == '"t"."data"->>\'name\''

    def test_json_extract_literal(self):
        result = self.dialect.json_extract(Literal("my_func()"), "name")
        assert result == "my_func()->>'name'"

    def test_json_extract_text(self):
        result = self.dialect.json_extract_text("data", "name")
        assert result == "\"data\"->>'name'"

    def test_json_extract_text_strips_jsonpath(self):
        result = self.dialect.json_extract_text("data", "$.email")
        assert result == "\"data\"->>'email'"

    def test_json_extract_object(self):
        result = self.dialect.json_extract_object("data", "name")
        assert result == "\"data\"->'name'"

    def test_json_extract_object_numeric(self):
        result = self.dialect.json_extract_object("data", 0)
        assert result == '"data"->0'

    def test_json_extract_object_with_alias(self):
        result = self.dialect.json_extract_object("data", "name", "user_obj")
        assert result == '"data"->\'name\' AS "user_obj"'

    def test_json_contains(self):
        result = self.dialect.json_contains("data", '{"key": "val"}')
        assert result == '"data" @> %s::jsonb'

    def test_json_contains_table_qualified(self):
        result = self.dialect.json_contains("t.data", '{"key": "val"}')
        assert result == '"t"."data" @> %s::jsonb'

    def test_json_contains_path(self):
        result = self.dialect.json_contains_path("data", "name")
        assert result == "\"data\" ?? 'name'"

    def test_json_path_query(self):
        result = self.dialect.json_path_query("data", "$.name")
        assert result == "\"data\"::jsonb @? '$.name'"

    def test_json_path_query_with_alias(self):
        result = self.dialect.json_path_query("data", "$.name", "has_name")
        assert result == '"data"::jsonb @? \'$.name\' AS "has_name"'

    def test_json_not_supported_extract_raises(self):
        dialect = DefaultSqlDialect()
        with pytest.raises(SqlError):
            dialect.json_extract("data", "name")

    def test_json_not_supported_extract_text_raises(self):
        dialect = DefaultSqlDialect()
        with pytest.raises(SqlError):
            dialect.json_extract_text("data", "name")

    def test_json_not_supported_contains_raises(self):
        dialect = DefaultSqlDialect()
        with pytest.raises(SqlError):
            dialect.json_contains("data", '{"key": "val"}')

    def test_json_not_supported_contains_path_raises(self):
        dialect = DefaultSqlDialect()
        with pytest.raises(SqlError):
            dialect.json_contains_path("data", "name")

    def test_sqlite_json_not_supported_raises(self):
        dialect = Sqlite3SqlDialect()
        with pytest.raises(SqlError):
            dialect.json_extract("data", "name")

    def test_field_expr_literal(self):
        result = self.dialect.json_extract(Literal("some_expr"), "key")
        assert result == "some_expr->>'key'"

    def test_field_expr_non_string(self):
        """Non-string, non-Literal values are passed through via str()"""
        result = self.dialect._json_field_expr(42)
        assert result == "42"

    def test_json_extract_text_with_alias(self):
        result = self.dialect.json_extract_text("data", "name", "username")
        assert result == '"data"->>\'name\' AS "username"'

    def test_json_contains_with_alias(self):
        result = self.dialect.json_contains("data", '{"key": "val"}', "has_val")
        assert result == '"data" @> %s::jsonb AS "has_val"'

    def test_json_contains_path_with_alias(self):
        result = self.dialect.json_contains_path("data", "name", "has_name")
        assert result == "\"data\" ?? 'name' AS \"has_name\""

    def test_pg_path_expr_non_string_non_int(self):
        """Non-string, non-int path values fall through via str()"""
        result = self.dialect._pg_path_expr(3.14)
        assert result == "3.14"

    def test_json_path_query_pre_quoted(self):
        result = self.dialect.json_path_query("data", "'$.name'")
        assert result == "\"data\"::jsonb @? '$.name'"


class TestPgJsonField:
    """Test PgJsonField with PgSqlDialect"""

    def setup_method(self):
        self.dialect = PgSqlDialect()

    def test_extract(self):
        jf = PgJsonField("data", self.dialect)
        result = jf.extract("name")
        assert str(result) == "\"data\"->>'name'"

    def test_extract_strips_jsonpath(self):
        jf = PgJsonField("data", self.dialect)
        result = jf.extract("$.name")
        assert str(result) == "\"data\"->>'name'"

    def test_extract_text(self):
        jf = PgJsonField("data", self.dialect)
        result = jf.extract_text("email")
        assert str(result) == "\"data\"->>'email'"

    def test_extract_object(self):
        jf = PgJsonField("data", self.dialect)
        result = jf.extract_object("settings")
        assert str(result) == "\"data\"->'settings'"

    def test_contains(self):
        jf = PgJsonField("data", self.dialect)
        result = jf.contains('{"key": "val"}')
        assert str(result) == '"data" @> %s::jsonb'

    def test_has_path(self):
        jf = PgJsonField("data", self.dialect)
        result = jf.has_path("name")
        assert str(result) == "\"data\" ?? 'name'"

    def test_path_query(self):
        jf = PgJsonField("data", self.dialect)
        result = jf.path_query("$.items[*].name")
        assert str(result) == "\"data\"::jsonb @? '$.items[*].name'"

    def test_getitem(self):
        jf = PgJsonField("data", self.dialect)
        result = jf["name"]
        assert isinstance(result, PgJsonField)
        assert result.field_name == 'data->"name"'

    def test_str_jsonb(self):
        jf = PgJsonField("data", self.dialect, is_jsonb=True)
        assert str(jf) == "data::jsonb"

    def test_str_json(self):
        jf = PgJsonField("data", self.dialect, is_jsonb=False)
        assert str(jf) == "data::json"

    def test_as_jsonb(self):
        jf = PgJsonField("data", self.dialect, is_jsonb=False)
        assert str(jf) == "data::json"
        result = jf.as_jsonb()
        assert result is jf
        assert str(jf) == "data::jsonb"

    def test_as_json(self):
        jf = PgJsonField("data", self.dialect, is_jsonb=True)
        assert str(jf) == "data::jsonb"
        result = jf.as_json()
        assert result is jf
        assert str(jf) == "data::json"

    def test_getitem_preserves_is_jsonb(self):
        jf = PgJsonField("data", self.dialect, is_jsonb=False)
        result = jf["name"]
        assert isinstance(result, PgJsonField)
        assert result.is_jsonb is False

    def test_extract_object_fallback_without_dialect(self):
        """extract_object falls back to extract when dialect lacks json_extract_object"""
        jf = PgJsonField("data")
        result = jf.extract_object("name")
        assert str(result) == "JSON_EXTRACT(data, '$.name')" or str(result) == "JSON_EXTRACT(data, 'name')"

    def test_path_query_fallback_without_dialect(self):
        """path_query falls back to has_path when dialect lacks json_path_query"""
        jf = PgJsonField("data")
        result = jf.path_query("$.name")
        assert str(result) == "JSON_CONTAINS_PATH(data, 'one', '$.name')"


class TestSelectJsonIntegration:
    """Test Select builder JSON integration methods"""

    def test_json_field_returns_pg_for_pg_dialect(self):
        select = Select(PgSqlDialect()).from_("users")
        jf = select.json_field("data")
        assert isinstance(jf, PgJsonField)

    def test_json_field_returns_base_for_default_dialect(self):
        select = Select(DefaultSqlDialect()).from_("users")
        jf = select.json_field("data")
        assert isinstance(jf, JsonField)
        assert not isinstance(jf, PgJsonField)

    def test_json_field_with_table(self):
        select = Select(PgSqlDialect()).from_("users")
        jf = select.json_field("data", "u")
        assert jf.field_name == "u.data"

    def test_json_where(self):
        select = Select(PgSqlDialect()).from_("users")
        sql, values = select.json_where("data", "name", "=", "Alice").assemble()
        assert "->>" in sql
        assert "WHERE" in sql
        assert values == ["Alice"]

    def test_json_where_with_json_field_object(self):
        select = Select(PgSqlDialect()).from_("users")
        jf = select.json_field("data")
        sql, values = select.json_where(jf, "age", ">", 18).assemble()
        assert "->>" in sql
        assert "WHERE" in sql
        assert values == [18]

    def test_json_field_returns_base_for_sqlite_dialect(self):
        select = Select(Sqlite3SqlDialect()).from_("users")
        jf = select.json_field("data")
        assert isinstance(jf, JsonField)
        assert not isinstance(jf, PgJsonField)
