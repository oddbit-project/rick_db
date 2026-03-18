# Welcome to RickDb

[![Tests](https://github.com/oddbit-project/rick_db/workflows/Tests/badge.svg)](https://github.com/oddbit-project/rick_db/actions)
[![pypi](https://img.shields.io/pypi/v/rick_db.svg)](https://pypi.org/project/rick_db/)
[![license](https://img.shields.io/pypi/l/rick-db.svg)](https://git.oddbit.org/OddBit/rick_db/src/branch/master/LICENSE)

RickDb is a SQL database layer for Python3. It includes connection management, Object Mapper, Query Builder,
and a Repository pattern implementation.

## Features

- **[Object Mapper](object_mapper.md)** — map database rows to Python objects using the `@fieldmapper` decorator. Attributes
  are independent of column names, making records portable across architectural boundaries and easy to serialize.

- **[Fluent Query Builder](building_queries.md)** — build SELECT, INSERT, UPDATE, DELETE, and CTE queries
  programmatically with a chainable API. Supports column aliases, type casting, JOINs (inner, left, right, full, cross,
  natural, lateral), grouped WHERE logic with parentheses, subqueries, UNION, and pagination. All values are parameterized.

- **[SQL Functions (Fn)](classes/fn.md)** — helper class for common SQL aggregate (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`),
  math (`ROUND`, `ABS`, `CEIL`, `FLOOR`, `SQRT`, etc.), and general (`COALESCE`, `CAST`) functions. Functions are nestable
  and work anywhere a column expression is accepted.

- **[JSON Operations](json_operations.md)** — query and extract JSON/JSONB data with `JsonField` and `PgJsonField`
  classes. Supports PostgreSQL operators (`->`, `->>`, `@>`, `@?`), bracket notation for nested access, and
  dialect-aware extraction for SQLite and ClickHouse.

- **[Repository Pattern](repository.md)** — provides CRUD operations (`insert`, `fetch_all`, `fetch_pk`, `fetch_where`,
  `update`, `delete`), transactions with automatic commit/rollback, built-in query caching, and pagination helpers.
  Extend with custom methods for domain-specific queries.

- **[DbGrid](grid.md)** — searchable, filterable, paginated data listings. Supports text search (`LIKE`/`ILIKE` with
  configurable patterns), exact-match filtering, multi-field sorting, and returns both total count and paginated results.

- **[Connections](connection.md)** — high-level connectors for **PostgreSQL** (psycopg2, with thread-safe
  connection pooling), **SQLite3** (stdlib), and **ClickHouse** (clickhouse-connect). All connectors share a common
  interface with cursor management, transaction support, and pluggable query profiling.

- **[SQL Dialects](classes/sqldialect.md)** — dialect objects handle database-specific differences (placeholder syntax,
  identifier quoting, type casting, JSON operators). Available for PostgreSQL, SQLite, ClickHouse, and
  [MySQL](classes/mysql_dialect.md) (SQL generation only, no connection backend).

- **[Database Introspection](classes/managerinterface.md)** — Manager classes for each backend expose schema metadata:
  list tables/views, inspect columns and primary keys, manage databases and schemas. PostgreSQL additionally provides
  [PgInfo](classes/pgmanager.md#pginfo) for detailed introspection of foreign keys, sequences, indexes, roles, and
  server settings.

- **[Migrations](migrations.md)** — forward-only migration manager with CLI (`rickdb`) and
  [Python API](migrations.md#python-api). Supports PostgreSQL, SQLite, and ClickHouse. Includes migration tracking,
  idempotent re-runs, history flattening, and DTO code generation from existing tables.

- **[Query Profiler](connection.md#using-a-profiler)** — pluggable profiler interface for logging queries, parameters,
  and execution times. Attach a `DefaultProfiler` to any connection or pool to capture events.

> **Note:** SQLite may have different behaviour based on Python versions; notably, DDL statements in a transaction
> may not be affected by rollback on Python <3.12. Also, there are limitations on text search when using the Grid helper.

## Purpose

RickDb was designed to be used in **schema-first** scenarios: the database structure is built and managed directly
with SQL DDL, and there is a clear segregation of concerns — the application layer has no responsibility for the
structure of the database.

This approach is the direct opposite of most available ORMs, but allows complete control over how the database
is queried and how results are processed within the application, favoring cache-friendly multi-tier and
service-oriented implementations.

It can also be used to consume information from existing databases, implement lightweight middleware services, or
perform quick application prototyping.

RickDb does not implement any async functionality, and there are no plans to support it in the near future.

## Quick Start

### 1. Install

```shell
pip install rick-db
```

### 2. Define a Record

```python
from rick_db import fieldmapper

@fieldmapper(tablename='users', pk='id_user')
class User:
    id = 'id_user'
    name = 'name'
    email = 'email'
```

### 3. Connect and Use

```python
from rick_db import Repository
from rick_db.backend.sqlite import Sqlite3Connection

conn = Sqlite3Connection(":memory:")

# create table (schema-first — you manage the DDL)
with conn.cursor() as c:
    c.exec("CREATE TABLE users (id_user INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    c.close()

repo = Repository(conn, User)

# insert
user_id = repo.insert_pk(User(name="Alice", email="alice@example.com"))

# fetch
user = repo.fetch_pk(user_id)
print(user.name, user.email)

# query builder
from rick_db.sql import Select, Fn

qry = repo.select(cols=[User.name, User.email]).where(User.name, "LIKE", "A%")
users = repo.fetch(qry)
```

See the [Examples](examples.md) page for more complete, runnable examples.

## Bookstore Example

A more realistic example showing a custom repository with JOINs and aggregate queries:

```python
from rick_db import fieldmapper, Repository
from rick_db.backend.pg import PgConnectionPool
from rick_db.sql import Select, Fn


@fieldmapper(tablename='publisher', pk='id_publisher')
class Publisher:
    id = 'id_publisher'
    name = 'name'


@fieldmapper(tablename='book', pk='id_book')
class Book:
    id = 'id_book'
    title = 'title'
    total_pages = 'total_pages'
    rating = 'rating'
    isbn = 'isbn'
    published = 'published_date'
    fk_publisher = 'fk_publisher'


@fieldmapper(tablename='author', pk='id_author')
class Author:
    id = 'id_author'
    first_name = 'first_name'
    middle_name = 'middle_name'
    last_name = 'last_name'


@fieldmapper(tablename='book_author', pk='id_book_author')
class BookAuthor:
    id = 'id_book_author'
    fk_book = 'fk_book'
    fk_author = 'fk_author'


class AuthorRepository(Repository):

    def __init__(self, db):
        super().__init__(db, Author)

    def calc_avg_rating(self, id_author: int):
        qry = Select(self.dialect). \
            from_(Book, {Fn.avg(Book.rating): 'rating'}). \
            join(BookAuthor, BookAuthor.fk_book, Book, Book.id). \
            where(BookAuthor.fk_author, '=', id_author)

        rset = self.fetch(qry, cls=Book)
        if len(rset) > 0:
            return rset.pop(0).rating
        return 0

    def books(self, id_author: int) -> list[Book]:
        qry = Select(self.dialect). \
            from_(Book). \
            join(BookAuthor, BookAuthor.fk_book, Book, Book.id). \
            where(BookAuthor.fk_author, '=', id_author)

        return self.fetch(qry, cls=Book)


if __name__ == '__main__':
    pool = PgConnectionPool(
        dbname="rickdb-bookstore", user="rickdb_user",
        password="rickdb_pass", host="localhost", port=5432, sslmode='require'
    )
    repo = AuthorRepository(pool)

    for author in repo.fetch_all():
        rating = repo.calc_avg_rating(author.id)
        print("Books by {} {}:".format(author.first_name, author.last_name))
        for book in repo.books(author.id):
            print("  ", book.title)
        print("Average rating:", rating)
```

## Migrating from previous versions (<2.0.0)

rick_db version 2.0.0 or later is incompatible with previous 1.x.x version, and migration will almost certainly require
code changes; The major changes to take into account are:

- Some files changed places and classes were renamed, including connectors, database management and migration management;
- Some properties (notably *_dialect*) were either made public (no underscore) or removed;
- PostgreSQL now only has 2 connectors, and the only available pool connector is thread-safe;
- PgConnectionPool pings by default each connection, and retries connecting if is stale;
- All connection-dependant classes now support both pooled and non-pooled connectors;
- Cache query is now per-repository object, not globally shared;
- Connections are no longer stored as attributes; instead, connections should be handled via context managers:
```python
pool = PgConnectionPool(**connection_params)

with pool.connection() as conn:
    with conn.cursor() as c:
        pass # do stuff
```
