"""
DbGrid usage for searchable, filterable, paginated listings.

Demonstrates:
 - DbGrid with text search
 - Filtering with match_fields
 - Sorting and pagination
 - Different search types (ANY, START, END)
"""
from rick_db import fieldmapper, Repository, DbGrid
from rick_db.backend.sqlite import Sqlite3Connection


@fieldmapper(tablename="products", pk="id_product")
class Product:
    id = "id_product"
    name = "name"
    category = "category"
    price = "price"
    active = "active"


def create_schema(conn):
    with conn.cursor() as c:
        c.exec(
            """
            CREATE TABLE products (
                id_product INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                active INTEGER DEFAULT 1
            )
            """
        )
        c.close()


def seed_data(repo):
    products = [
        Product(name="Python Cookbook", category="books", price=45.99, active=1),
        Product(name="SQL Fundamentals", category="books", price=39.99, active=1),
        Product(name="Python Sticker Pack", category="merch", price=9.99, active=1),
        Product(name="Database Design Guide", category="books", price=54.99, active=1),
        Product(name="SQL Cheat Sheet Poster", category="merch", price=14.99, active=0),
        Product(name="Advanced Python Patterns", category="books", price=49.99, active=1),
        Product(name="Python Mug", category="merch", price=12.99, active=1),
        Product(name="PostgreSQL Administration", category="books", price=59.99, active=1),
    ]
    for p in products:
        repo.insert_pk(p)


def print_results(total, rows):
    print("  Total matching: {}".format(total))
    for row in rows:
        print(
            "    [{}] {} - ${} ({})".format(
                row.category, row.name, row.price, "active" if row.active else "inactive"
            )
        )


def main():
    conn = Sqlite3Connection(":memory:")
    create_schema(conn)
    repo = Repository(conn, Product)
    seed_data(repo)

    # Search across name and category fields
    grid = DbGrid(repo, search_fields=[Product.name, Product.category])

    # Text search
    print('Search for "python":')
    total, rows = grid.run(search_text="python")
    print_results(total, rows)

    # Text search + filter by active
    print('\nSearch for "sql", active only:')
    total, rows = grid.run(
        search_text="sql",
        match_fields={Product.active: 1},
    )
    print_results(total, rows)

    # Filter by category, sorted by price descending
    print("\nAll books, sorted by price (desc):")
    total, rows = grid.run(
        match_fields={Product.category: "books"},
        sort_fields={Product.price: "DESC"},
    )
    print_results(total, rows)

    # Pagination: 3 items per page
    print("\nAll products, page 1 (3 per page):")
    total, rows = grid.run(
        limit=3,
        offset=0,
        sort_fields={Product.id: "ASC"},
    )
    print_results(total, rows)

    print("\nAll products, page 2 (3 per page):")
    total, rows = grid.run(
        limit=3,
        offset=3,
        sort_fields={Product.id: "ASC"},
    )
    print_results(total, rows)

    # Search type: starts with
    grid_start = DbGrid(
        repo,
        search_fields=[Product.name],
        search_type=DbGrid.SEARCH_START,
    )
    print('\nSearch starts with "python":')
    total, rows = grid_start.run(search_text="python")
    print_results(total, rows)

    conn.close()


if __name__ == "__main__":
    main()
