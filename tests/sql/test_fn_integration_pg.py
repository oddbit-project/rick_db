import pytest
from rick_db import fieldmapper, Repository
from rick_db.backend.pg import PgConnection
from rick_db.sql import Fn


@fieldmapper(tablename="test_products", pk="id")
class Product:
    id = "id"
    category = "category"
    name = "name"
    price = "price"
    quantity = "quantity"


create_table = """
    create table if not exists test_products(
    id serial primary key,
    category text not null,
    name text not null,
    price numeric(10,2) not null,
    quantity integer not null
    );
"""

insert_row = (
    "insert into test_products(category, name, price, quantity) values(%s,%s,%s,%s)"
)
drop_table = "drop table if exists test_products"

PRODUCTS = [
    ("electronics", "keyboard", 49.99, 10),
    ("electronics", "mouse", 29.50, 25),
    ("electronics", "monitor", 299.99, 5),
    ("furniture", "desk", 199.00, 8),
    ("furniture", "chair", 149.50, 12),
    ("furniture", "lamp", -15.75, 0),
]


@pytest.fixture
def conn(pg_settings):
    conn = PgConnection(**pg_settings)
    with conn.cursor() as c:
        c.exec(drop_table)
        c.exec(create_table)
        for row in PRODUCTS:
            c.exec(insert_row, list(row))
    yield conn
    with conn.cursor() as c:
        c.exec(drop_table)
    conn.close()


class TestFnIntegrationPg:

    def test_count(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.count(): "total"})
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
        assert abs(float(rows[0]["avg_price"]) - expected) < 0.01

    def test_min(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.min(Product.price): "min_price"})
        rows = repo.fetch_raw(qry)
        assert float(rows[0]["min_price"]) == min(p[2] for p in PRODUCTS)

    def test_max(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.max(Product.price): "max_price"})
        rows = repo.fetch_raw(qry)
        assert float(rows[0]["max_price"]) == max(p[2] for p in PRODUCTS)

    def test_abs(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.abs(Product.price): "abs_price"}).where(
            Product.price, "<", 0
        )
        rows = repo.fetch_raw(qry)
        assert len(rows) == 1
        assert float(rows[0]["abs_price"]) == 15.75

    def test_ceil(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.ceil(Product.price): "ceiled"}).where(
            Product.name, "=", "keyboard"
        )
        rows = repo.fetch_raw(qry)
        assert float(rows[0]["ceiled"]) == 50

    def test_floor(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.floor(Product.price): "floored"}).where(
            Product.name, "=", "keyboard"
        )
        rows = repo.fetch_raw(qry)
        assert float(rows[0]["floored"]) == 49

    def test_round(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.round(Fn.avg(Product.price), 1): "rounded"})
        rows = repo.fetch_raw(qry)
        expected = round(sum(p[2] for p in PRODUCTS) / len(PRODUCTS), 1)
        assert float(rows[0]["rounded"]) == expected

    def test_power(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.power(Product.quantity, 2): "squared"}).where(
            Product.name, "=", "mouse"
        )
        rows = repo.fetch_raw(qry)
        assert float(rows[0]["squared"]) == 625  # 25^2

    def test_sqrt(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.sqrt(Product.quantity): "root"}).where(
            Product.name, "=", "mouse"
        )
        rows = repo.fetch_raw(qry)
        assert float(rows[0]["root"]) == 5.0  # sqrt(25)

    def test_mod(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.mod(Product.quantity, 3): "remainder"}).where(
            Product.name, "=", "mouse"
        )
        rows = repo.fetch_raw(qry)
        assert rows[0]["remainder"] == 1  # 25 % 3

    def test_sign(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Product.name: None, Fn.sign(Product.price): "sgn"}).where(
            Product.name, "in", ["keyboard", "lamp"]
        ).order(Product.id)
        rows = repo.fetch_raw(qry)
        assert rows[0]["sgn"] == 1
        assert rows[1]["sgn"] == -1

    def test_trunc(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.trunc(Product.price, 1): "truncated"}).where(
            Product.name, "=", "keyboard"
        )
        rows = repo.fetch_raw(qry)
        assert float(rows[0]["truncated"]) == 49.9

    def test_trunc_no_decimals(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.trunc(Product.price): "truncated"}).where(
            Product.name, "=", "keyboard"
        )
        rows = repo.fetch_raw(qry)
        assert float(rows[0]["truncated"]) == 49

    def test_coalesce(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.coalesce(Product.category, "'unknown'"): "cat"}).limit(1)
        rows = repo.fetch_raw(qry)
        assert rows[0]["cat"] is not None

    def test_cast(self, conn):
        repo = Repository(conn, Product)
        qry = repo.select({Fn.cast(Product.price, "integer"): "int_price"}).where(
            Product.name, "=", "keyboard"
        )
        rows = repo.fetch_raw(qry)
        assert rows[0]["int_price"] == 50

    def test_group_by_with_aggregates(self, conn):
        repo = Repository(conn, Product)
        qry = (
            repo.select(
                {
                    Product.category: None,
                    Fn.count(): "cnt",
                    Fn.sum(Product.quantity): "total_qty",
                    Fn.round(Fn.avg(Product.price), 2): "avg_price",
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
