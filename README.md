rick_db - Simple SQL database layer
--
[![Tests](https://github.com/oddbit-project/rick_db/workflows/Tests/badge.svg?branch=master)](https://github.com/oddbit-project/rick_db/actions)
[![pypi](https://img.shields.io/pypi/v/rick-db.svg)](https://pypi.org/project/rick-db/)
[![license](https://img.shields.io/pypi/l/rick-db.svg)](https://github.com/oddbit-project/rick_db/blob/master/LICENSE)


rick_db is a simple SQL database layer for Python3. It includes connection management, Object Mapper, Query Builder,
and a Repository pattern implementation. It is **not** an ORM, and it's not meant to replace one. 

## Features
- Object Mapper;
- Fluent Sql Query builder;
- High level connectors for PostgreSQL, SqlLite3;
- Pluggable SQL query profiler; 
- Simple migration manager for SQL files;

## Usage scenarios

rick_db was built to cater to a schema-first approach: Database schema is built and managed directly with SQL DDL commands,
and the application layer has no responsibility on the structure of the database.


## Installation
```
$ pip3 install rick-db
```
## Documentation

Project documentation can be found on the [Documentation](https://oddbit-project.github.io/rick_db/) website.


## TL;DR; example

Showcasing the Connection, DTO, Repository and Query Builder objects: 

```python
from rick_db import fieldmapper, Repository
from rick_db.conn.pg import PgConnection
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
        :param id_author: author id
        :return: average rating, if any
        """
        
        # generated query:
        # SELECT avg(rating) AS "rating" FROM "book" INNER JOIN "book_author" ON 
        # "book"."id_book"="book_author"."fk_book" WHERE ("fk_author" = %s)
        qry = Select(self._dialect). \
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
        
        qry = Select(self._dialect). \
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

    conn = PgConnection(**db_cfg)
    repo = AuthorRepository(conn)
    dump_author_rating(repo)
```

## Running tests

To run the tests, you should have both tox and tox-docker, as well as a local docker daemon. Make sure the current user has
access to the docker daemon.
```python
$ pip3 install -r requirements-dev.txt
$ tox 
```
