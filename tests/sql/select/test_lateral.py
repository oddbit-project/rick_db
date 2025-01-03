import pytest

from rick_db.sql import Select, PgSqlDialect, Sql, Literal


def join_lateral():
    return [
        [
            {"t_wishlist": "w"},
            Select(PgSqlDialect())
            .from_({"t_product": "p"})
            .where("price", "<", "desired_price")
            .order("price", Sql.SQL_DESC)
            .limit(3),
            "x",
            Literal("true"),
            'SELECT "w".* FROM "t_wishlist" AS "w" LEFT JOIN LATERAL (SELECT "p".* FROM "t_product" AS "p" WHERE ("price" < %s) ORDER BY "price" DESC LIMIT 3) AS "x" ON (true)',
        ],
    ]


def from_lateral():
    return [
        [
            {"t_wishlist": "w"},
            Select(PgSqlDialect())
            .from_({"t_product": "p"})
            .where("price", "<", "desired_price")
            .order("price", Sql.SQL_DESC)
            .limit(3),
            "x",
            'SELECT "w".*,"x".* FROM "t_wishlist" AS "w", LATERAL (SELECT "p".* FROM "t_product" AS "p" WHERE ("price" < %s) ORDER BY "price" DESC LIMIT 3) AS "x"',
        ]
    ]


class TestLateral:

    @pytest.mark.parametrize("table, subquery, alias, join_expr,result", join_lateral())
    def test_join_left_lateral(
        self,
        table,
        subquery,
        alias,
        join_expr,
        result,
    ):
        sql, _ = (
            Select()
            .from_(table)
            .join_left_lateral(subquery, alias, join_expr)
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize("table, subquery, alias, join_expr,result", join_lateral())
    def test_join_inner_lateral(
        self,
        table,
        subquery,
        alias,
        join_expr,
        result,
    ):
        result = result.replace("LEFT", "INNER")
        sql, _ = (
            Select()
            .from_(table)
            .join_inner_lateral(subquery, alias, join_expr)
            .assemble()
        )
        assert sql == result

    @pytest.mark.parametrize("table, subquery, alias, result", from_lateral())
    def test_from_lateral(
        self,
        table,
        subquery,
        alias,
        result,
    ):
        sql, _ = Select().from_(table).lateral(subquery, alias).assemble()
        assert sql == result
