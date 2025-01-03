# Repositories

Repositories provide useful functions for [Record](object_mapper.md) interact with the database. They are also a Repository
pattern implementation, as hinted by the naming. These constructs are quite handy in the segregation of the data access
layer and the business logic or service layer in multi-layer applications, but can also be quite useful as a shortcut
for common read, write or delete operations.

For more details on all the available methods, check the [Repository](classes/repository.md) class documentation.

## Declaring Repositories

A Repository class can be instantiated directly, or declared via direct inheritance. Typically, direct inheritance
has the advantage of resulting in a properly named class that can be easily extendable by adding methods. Regardless, there
are usage scenarios where direct instantiation can be quite convenient:

```python
from rick_db import fieldmapper, Repository
from rick_db.backend.pg import PgConnectionPool

@fieldmapper(tablename='character', pk='id_character')
class Character:
    id = 'id_character'
    name = 'name'


# declare a Repository class for Character using inheritance
class CharacterRepository(Repository):
    
    def __init__(self, db):
        # new constructor
        super().__init__(db, Character)


db_cfg = {...}
pool = PgConnectionPool(**db_cfg)

# instantiate declared repository class
repo = CharacterRepository(pool)

# insert some records
repo.insert(Character(id=1, name='Sarah Connor'))
repo.insert(Character(id=2, name='John Connor'))

# read all records using the repo object
for record in repo.fetch_all():
    print(record.name)

# alternative method, instantiate a repository directly
repo = Repository(pool, Character)

# use the repo object
repo.insert(Character(id=3, name='T-1000'))

```

## Extending Repositories

Repository classes can also contain custom methods; This is the preferred approach when implementing additional database
functionality. However, the methods should be designed to be stateless - they should not add or modify internal object
attributes, nor depend on previous or future executions to carry their functions. By respecting this, Repository objects
can be instantiated or reused in different contexts without any extra supervision:

```python
from rick_db import fieldmapper, Repository
from rick_db.sql import Select, Literal


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
```

## Advanced usage

While Repository objects are stateless from an operational perspective, there is actually an internal, thread-safe, local cache that
is used to accelerate query building. Most Repository methods perform actions with SQL generated from the [Query Builder](building_queries.md),
and these generated SQL statements can often be cached, due to the fact that any required values are passed in a separate
structure.

Each Repository contains its own QueryCache instance, that can be accessed via the *query_cache* attribute.

The typical usage scenario for cache interaction is:
```python
from rick_db import Repository
class MyRepository(Repository):
    
    def some_method(self):
        sql = self.query_cache.get("<unique cache entry name>")
        if not sql:
           sql, values = some_query_using_query_builder.assemble()
           self.query_cache.set("<unique cache entry name>", sql)
        else:
            values = list_of_required_values
        (...)
```

The implementation of the actual [Registry.fetch_pk()](classes/repository.md#repositoryfetch_pkpk_value) provides a good
example of the typical pattern usage of the cache manipulation methods:

```python
    (...)   

    def fetch_pk(self, pk_value) -> Optional[object]:
        
        (...)
        
        qry = self.query_cache.get("find_pk")
        if qry is None:
            qry, values = (
                self.select().where(self.pk, "=", pk_value).limit(1).assemble()
            )
            self.query_cache.set("find_pk", qry)
        else:
            values = [pk_value]

        with self.cursor() as c:
            return c.fetchone(qry, values, self._record)

    (...)
```

