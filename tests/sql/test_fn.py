from rick_db.sql import Fn, Literal, Select, PgSqlDialect


class TestFn:

    def test_count(self):
        result = Fn.count()
        assert isinstance(result, Literal)
        assert str(result) == "COUNT(*)"

    def test_count_field(self):
        assert str(Fn.count("id")) == "COUNT(id)"

    def test_sum(self):
        assert str(Fn.sum("amount")) == "SUM(amount)"

    def test_avg(self):
        assert str(Fn.avg("price")) == "AVG(price)"

    def test_min(self):
        assert str(Fn.min("price")) == "MIN(price)"

    def test_max(self):
        assert str(Fn.max("price")) == "MAX(price)"

    def test_abs(self):
        assert str(Fn.abs("value")) == "ABS(value)"

    def test_ceil(self):
        assert str(Fn.ceil("value")) == "CEIL(value)"

    def test_floor(self):
        assert str(Fn.floor("value")) == "FLOOR(value)"

    def test_round(self):
        assert str(Fn.round("value")) == "ROUND(value)"

    def test_round_decimals(self):
        assert str(Fn.round("value", 2)) == "ROUND(value, 2)"

    def test_power(self):
        assert str(Fn.power("value", 3)) == "POWER(value, 3)"

    def test_sqrt(self):
        assert str(Fn.sqrt("value")) == "SQRT(value)"

    def test_mod(self):
        assert str(Fn.mod("value", 3)) == "MOD(value, 3)"

    def test_sign(self):
        assert str(Fn.sign("value")) == "SIGN(value)"

    def test_trunc(self):
        assert str(Fn.trunc("value")) == "TRUNC(value)"

    def test_trunc_decimals(self):
        assert str(Fn.trunc("value", 2)) == "TRUNC(value, 2)"

    def test_coalesce(self):
        assert str(Fn.coalesce("a", "b", "c")) == "COALESCE(a, b, c)"

    def test_cast(self):
        assert str(Fn.cast("field", "int")) == "CAST(field AS int)"

    def test_select_with_fn(self):
        dialect = PgSqlDialect()
        qry, _ = Select(dialect).from_("users", {Fn.count(): "total"}).assemble()
        assert 'COUNT(*)' in qry
        assert '"total"' in qry

    def test_select_mixed_columns(self):
        dialect = PgSqlDialect()
        qry, _ = (
            Select(dialect)
            .from_("orders", {"name": None, Fn.sum("amount"): "total"})
            .group("name")
            .assemble()
        )
        assert '"name"' in qry
        assert 'SUM(amount)' in qry
        assert '"total"' in qry

    def test_nested_fn(self):
        result = Fn.round(Fn.avg("price"), 2)
        assert str(result) == "ROUND(AVG(price), 2)"
