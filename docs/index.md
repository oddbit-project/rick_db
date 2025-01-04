# Welcome to RickDb

[![Tests](https://github.com/oddbit-project/rick_db/workflows/Tests/badge.svg)](https://github.com/oddbit-project/rick_db/actions)
[![pypi](https://img.shields.io/pypi/v/rick_db.svg)](https://pypi.org/project/rick_db/)
[![license](https://img.shields.io/pypi/l/rick-db.svg)](https://git.oddbit.org/OddBit/rick_db/src/branch/master/LICENSE)

RickDb is a SQL database layer for Python3. It includes connection management, Object Mapper, Query Builder,
and a Repository pattern implementation.  

## Features
- Object Mapper
- Fluent SQL Query builder with schema support
- High level connectors for PostgreSQL, SQLite
- Pluggable SQL query profiler
- Grid helper
- Migration Manager

> Note: SQLite may have different behaviour based on Python versions; notably, DDL statements in a transaction 
> may not be affected by rollback on Python <3.12. Also, there are limitations on text search when using the Grid helper

## Purpose

RickDb was designed to be used in schema-first scenarios: Database schema is built and managed directly with SQL DDL commands,
and there is a clear segregation of concerns - the application layer has no responsibility on the structure of the database.

This approach is the direct opposite of most available ORMS, but allows complete control over how the database is queried
and how results are processed within the application, favoring cache-friendly multi-tier/service-oriented implementations.

However, it can also be used to consume information from existing databases, implement lightweight middleware services, or
to perform some quick application prototyping. 

Please note, RickDb does not implement any async functionality, and there are no plans to support it in the near future.


## TL;DR; example

A simple bookstore DTO and Repository example, with a custom query via QueryBuilder:
```python
from rick_db import fieldmapper, Repository
from rick_db.backend.pg import PgConnectionPool
from rick_db.sql import Select, Literal


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
        """
        Calculate average rating for a given author
        :param id_author:
        :return: average rating, if any
        """

        # generated query:
        # SELECT avg(rating) AS "rating" FROM "book" INNER JOIN "book_author" ON 
        # "book"."id_book"="book_author"."fk_book" WHERE ("fk_author" = %s)
        qry = Select(self.dialect). \
            from_(Book, {Literal("avg({})".format(Book.rating)): 'rating'}). \
            join(BookAuthor, BookAuthor.fk_book, Book, Book.id). \
            where(BookAuthor.fk_author, '=', id_author)

        # retrieve result as list of type Book (to get the rating field)
        rset = self.fetch(qry, cls=Book)
        if len(rset) > 0:
            return rset.pop(0).rating
        return 0

    def books(self, id_author: int) -> list[Book]:
        """
        Retrieve all books for the given author
        :return: list[Book]
        """

        qry = Select(self.dialect). \
            from_(Book). \
            join(BookAuthor, BookAuthor.fk_book, Book, Book.id). \
            where(BookAuthor.fk_author, '=', id_author)

        return self.fetch(qry, cls=Book)


def dump_author_rating(repo: AuthorRepository):
    for author in repo.fetch_all():

        # calculate average
        rating = repo.calc_avg_rating(author.id)

        # print book list
        print("Books by {firstname} {lastname}:".format(firstname=author.first_name, lastname=author.last_name))
        for book in repo.books(author.id):
            print(book.title)

        # print average rating           
        print("Average rating for {firstname} {lastname} is {rating}".
              format(firstname=author.first_name, lastname=author.last_name, rating=rating))


if __name__ == '__main__':
    db_cfg = {
        'dbname': "rickdb-bookstore",
        'user': "rickdb_user",
        'password': "rickdb_pass",
        'host': "localhost",
        'port': 5432,
        'sslmode': 'require'
    }

    pool = PgConnectionPool(**db_cfg)
    repo = AuthorRepository(pool)
    dump_author_rating(repo)
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
...
pool = PgConnectionPool(**connection_params)
...
with pool.connection() as conn: # fetch a connection
    with conn.cursor() as c: # fetch a cursor
        pass # do stuff
```

