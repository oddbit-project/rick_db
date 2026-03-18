import pytest
from rick_db import fieldmapper, Repository
from rick_db.backend.sqlite import Sqlite3Connection
from rick_db.sql import Fn, Select, Sqlite3SqlDialect


@fieldmapper(tablename="products", pk="id")
class Product:
    id = "id"
    category = "category"
    name = "name"
    price = "price"
    quantity = "quantity"


create_table = """
    create table if not exists products(
    id integer primary key autoincrement,
    category text not null,
    name text not null,
    price real not null,
    quantity integer not null
    );
"""

insert_row = "insert into products(category, name, price, quantity) values(?,?,?,?)"

PRODUCTS = [
    ("electronics", "keyboard", 49.99, 10),
    ("electronics", "mouse", 29.50, 25),
    ("electronics", "monitor", 299.99, 5),
    ("furniture", "desk", 199.00, 8),
    ("furniture", "chair", 149.50, 12),
    ("furniture", "lamp", -15.75, 0),  # negative price for abs/sign tests
]


@pytest.fixture
def conn():
    conn = Sqlite3Connection(":memory:")
    with conn.cursor() as c:
        c.exec(create_table)
        for row in PRODUCTS:
            c.exec(insert_row, list(row))
    yield conn
    conn.close()


class TestFnIntegration:

    def test_count(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.count(): "total"})
        rows = repo.fetch_raw(qry)
        assert rows[0]["total"] == len(PRODUCTS)

    def test_count_field(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.count(Product.name): "total"})
        rows = repo.fetch_raw(qry)
        assert rows[0]["total"] == len(PRODUCTS)

    def test_sum(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.sum(Product.quantity): "total_qty"})
        rows = repo.fetch_raw(qry)
        expected = sum(p[3] for p in PRODUCTS)
        assert rows[0]["total_qty"] == expected

    def test_avg(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.avg(Product.price): "avg_price"})
        rows = repo.fetch_raw(qry)
        expected = sum(p[2] for p in PRODUCTS) / len(PRODUCTS)
        assert abs(rows[0]["avg_price"] - expected) < 0.01

    def test_min(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.min(Product.price): "min_price"})
        rows = repo.fetch_raw(qry)
        assert rows[0]["min_price"] == min(p[2] for p in PRODUCTS)

    def test_max(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.max(Product.price): "max_price"})
        rows = repo.fetch_raw(qry)
        assert rows[0]["max_price"] == max(p[2] for p in PRODUCTS)

    def test_abs(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.abs(Product.price): "abs_price"}).where(
            Product.price, "<", 0
        )
        rows = repo.fetch_raw(qry)
        assert len(rows) == 1
        assert rows[0]["abs_price"] == 15.75

    def test_round(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select(
            {Fn.round(Fn.avg(Product.price), 1): "rounded"}
        )
        rows = repo.fetch_raw(qry)
        expected = round(sum(p[2] for p in PRODUCTS) / len(PRODUCTS), 1)
        assert rows[0]["rounded"] == expected

    def test_round_no_decimals(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.round(Product.price): "rounded"}).where(
            Product.name, "=", "keyboard"
        )
        rows = repo.fetch_raw(qry)
        assert rows[0]["rounded"] == round(49.99)

    def test_sign(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Product.name: None, Fn.sign(Product.price): "sgn"}).order(
            Product.id
        )
        rows = repo.fetch_raw(qry)
        for row in rows:
            if row["name"] == "lamp":
                assert row["sgn"] == -1
            else:
                assert row["sgn"] == 1

    def test_coalesce(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.coalesce(Product.category, "'unknown'"): "cat"}).limit(1)
        rows = repo.fetch_raw(qry)
        assert rows[0]["cat"] is not None

    def test_group_by_with_aggregates(self, conn):
        repo = Repository(conn, Product)
        qry = (
            repo.select(
                {
                    Product.category: None,
                    Fn.count(): "cnt",
                    Fn.sum(Product.quantity): "total_qty",
                    Fn.avg(Product.price): "avg_price",
                }
            )
            .group(Product.category)
            .order(Product.category)
        )
        rows = repo.fetch_raw(qry)
        assert len(rows) == 2

        electronics = rows[0]
        assert electronics["category"] == "electronics"
        assert electronics["cnt"] == 3
        assert electronics["total_qty"] == 40

        furniture = rows[1]
        assert furniture["category"] == "furniture"
        assert furniture["cnt"] == 3
        assert furniture["total_qty"] == 20

    def test_nested_functions(self, conn):
        repo = Repository(conn, Product)
        # ROUND(AVG(price), 2) grouped by category
        qry = (
            repo.select(
                {
                    Product.category: None,
                    Fn.round(Fn.avg(Product.price), 2): "avg_price",
                }
            )
            .group(Product.category)
            .order(Product.category)
        )
        rows = repo.fetch_raw(qry)
        assert len(rows) == 2

        elec_prices = [p[2] for p in PRODUCTS if p[0] == "electronics"]
        expected = round(sum(elec_prices) / len(elec_prices), 2)
        assert rows[0]["avg_price"] == expected

    def test_having_with_fn(self, conn):
        repo = Repository(conn, Product)
        qry = (
            repo.select({Product.category: None, Fn.sum(Product.quantity): "total_qty"})
            .group(Product.category)
            .having(Fn.sum(Product.quantity), ">", 30)
        )
        rows = repo.fetch_raw(qry)
        assert len(rows) == 1
        assert rows[0]["category"] == "electronics"

    def test_mixed_columns_list_and_fn(self, conn):
        repo = Repository(conn, Product)
        # Use fn in a dict with regular columns
        qry = (
            repo.select(
                {
                    Product.category: None,
                    Fn.min(Product.price): "cheapest",
                    Fn.max(Product.price): "priciest",
                }
            )
            .group(Product.category)
            .order(Product.category)
        )
        rows = repo.fetch_raw(qry)
        assert len(rows) == 2
        assert rows[0]["cheapest"] == 29.50
        assert rows[0]["priciest"] == 299.99
