# Class rick_db.sql.**MySqlSqlDialect**

MySQL dialect implementation for the query builder. Extends [SqlDialect](sqldialect.md).

```python
from rick_db.sql import Select, Insert, Update, Delete, MySqlSqlDialect

dialect = MySqlSqlDialect()
```

> **Note:** RickDb does not include a MySQL connection backend. This dialect is provided for SQL
> generation only — you must execute the generated SQL using your own MySQL connection library
> (e.g. `mysql-connector-python`, `PyMySQL`, or `mysqlclient`).

### Dialect properties

| Property | Value | Description |
|----------|-------|-------------|
| `placeholder` | `%s` | Parameter placeholder |
| `insert_returning` | `False` | `INSERT...RETURNING` not supported |
| `ilike` | `False` | `ILIKE` not supported (use `LIKE` with `COLLATE`) |
| `json_support` | `True` | JSON operations supported |

### Identifier quoting

MySqlSqlDialect uses **backticks** for identifier quoting, unlike PostgreSQL's double quotes:

```python
from rick_db.sql import Select, MySqlSqlDialect, PgSqlDialect

# MySQL: backticks
qry, _ = Select(MySqlSqlDialect()).from_("users", ["name"]).assemble()
# SELECT `name` FROM `users`

# PostgreSQL: double quotes
qry, _ = Select(PgSqlDialect()).from_("users", ["name"]).assemble()
# SELECT "name" FROM "users"
```

### Comparison with other dialects

| Feature | MySqlSqlDialect | PgSqlDialect | Sqlite3SqlDialect |
|---------|-----------------|--------------|-------------------|
| Placeholder | `%s` | `%s` | `?` |
| Identifier quoting | Backticks (`` ` ``) | Double quotes (`"`) | Double quotes (`"`) |
| `INSERT...RETURNING` | No | Yes | Yes (3.35+) |
| `ILIKE` | No | Yes | No |
| Type casting | `CAST(x AS type)` | `x::type` | `CAST(x AS type)` |
| JSON extract text | `JSON_UNQUOTE(JSON_EXTRACT(...))` | `->>`  | `JSON_EXTRACT(...)` |

### Usage example

```python
from rick_db import fieldmapper
from rick_db.sql import Select, Insert, Update, Delete, Fn, MySqlSqlDialect

dialect = MySqlSqlDialect()

@fieldmapper(tablename="users", pk="id")
class User:
    id = "id"
    name = "name"
    email = "email"

# SELECT
qry, values = (
    Select(dialect)
    .from_(User, [User.name, User.email])
    .where(User.name, "LIKE", "%alice%")
    .order(User.name)
    .limit(10)
    .assemble()
)
# SELECT `name`,`email` FROM `users` WHERE (`name` LIKE %s) ORDER BY `name` ASC LIMIT 10
print(qry)

# INSERT
qry, values = Insert(dialect).into(User).values({"name": "Bob", "email": "bob@test.com"}).assemble()
# INSERT INTO `users` (`name`, `email`) VALUES (%s, %s)
print(qry)

# UPDATE
qry, values = Update(dialect).table(User).values({"name": "Bob"}).where(User.id, "=", 1).assemble()
# UPDATE `users` SET `name`=%s WHERE `id` = %s
print(qry)

# DELETE
qry, values = Delete(dialect).from_(User).where(User.id, "=", 1).assemble()
# DELETE FROM `users` WHERE `id` = %s
print(qry)

# Aggregation
qry, _ = (
    Select(dialect)
    .from_(User, {Fn.count(): "total"})
    .assemble()
)
# SELECT COUNT(*) AS `total` FROM `users`
print(qry)
```
