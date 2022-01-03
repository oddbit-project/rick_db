# Migrations

RickDb is a schema-first library - there is no automatic generation of database objects; instead they are
usually modeled using raw SQL, and kept in files separated from application code.

While there are plenty of tools to manage migration, RickDb provides a simple, forward-only migration manager
cli utility that can be used to manage these SQL files, **rickdb**.

## Why forward-only?

Many database migration tools provide mechanisms to create and remove database objects, with the purpose of 
rolling back schema changes. However, rolling back schema changes can lead to the truncation of relevant data;
adding a field, then removing it will effectively truncate the stored information; however, adding a row with an 
automatic identity field, then removing it will not rollback the underlying identity sequence value. While this
kind of rollback capability is quite popular, it is obvious most SGBDs can't actually perform rollbacks the way
they were conceptualized.

Instead of this approach, RickDb's Migration Manager only supports "forward-only" migrations - a sequence of SQL
files with the desired changes for a given database. These changes can be additive (e.g. creating tables and 
views), transformational (e.g. adding fields or indexes) or destructive (e.g. removing tables, views, fields, etc).

## Configuration

The bundled Migration Manager requires a TOML configuration file, called by default **rickdb.toml**, containing 
the database connection details. The file usually resides in the project root directory, but can also have a
custom location, specified by the environment variable **RICKDB_CONFIG**.

The TOML config file can have one or more database configuration keys. These keys may be a single
default key **db** (for single database applications), or multiple, name-based keys prefixed with **db_**:

Simple single-database configuration example:

```toml
# single database, no name
[db]
engine = "pgsql"
host = "localhost"
port = 5432
user = "myuser"
password = "mypassword"
dbname = "myschema"
```
Multiple database configuration example:

```toml
# administration database
[db_admin]
engine = "pgsql"
host = "localhost"
port = 5432
user = "myuser"
password = "mypassword"
dbname = "admin_schema"

# application database
[db_app]
engine = "pgsql"
host = "localhost"
port = 5432
user = "myuser"
dbname = "app_schema"
passfile = "/var/run/super_secret_pwd"

# test database
[db_test]
engine = "sqlite"
db_file = "/tmp/test.db"    
```

If a **[db]** section exists, it will be used when no database is specified in the cli arguments; db_&lt;name&gt; configurations
can be invoked by providing &lt;name&gt; as the first argument:

```shell
# use [db] database
$ rickdb list 
14/12/2021 18:28:56     001.sql
15/12/2021 19:32:58     002.sql
15/12/2021 19:33:42     003.sql

# use [db_app] database
$ rickdb app list
15/12/2021 19:15:00     001_schema.sql
```


In addition to the parameters required by the connection object, there are two additional parameters:

|Parameter | Mandatory | Description|
|---|---|---|
|engine|yes|Database engine to use (currently "pgsql" or "sqlite")|
|passfile|no|Optional password file containing the database password|

Engine is a mandatory field that specifies which database Connection object will be used. Currently, its value can
be either 'pgsql' or 'sqlite'.

Passfile is an optional parameter indicating that the password should be read from an existing file
instead. When **passfile** is used, the file is read into a **password** parameter automatically. Keep in
mind, if both **password** and **passfile** are used, **passfile** overrides the password contents.

## Installation

The Migration Manager requires a database table to record executed migration information. This database table
can be easily created via command-line:

Single database configuration:
```shell
$ rickdb init
Migration Manager installed sucessfully!
$
```

Multiple database configuration, in this case for db_app:
```shell
$ rickdb app init
Migration Manager installed sucessfully!
$
```

## Creating migrations

To create a migration, just create a directory with a set of SQL files. It is good practice to name the files sequentially,
as migrations are executed ordered by name. The naming format is free-form, as long as the file has an **.sql** extension
in lowercase.

Common migration naming examples:
```shell
# sequence number
0001.sql
0002.sql

# sequence number & description
0001-base_schema.sql
0002-index_change_users.sql

# ticket name & description
TICKET001-some_stuff.sql
TICKET002-other_stuff.sql

# date
20210101-something.sql
20210102-something_else.sql
```
Keep in mind, each migration file should be treated as immutable - each file is only applied/executed once. Subsequent
changes to the file will be ignored; any desired changes to the file after it has been run should be made on a separate 
migration. 

## Applying migrations

The migration manager provides two useful commands to manage pending migrations - check and migrate.

#### rickdb check &lt;path&gt;

This command compares all migration names in the specified path with the already applied ones, indicating which ones were
already applied:

```shell
$ rickdb check migrations/
Checking 001.sql... already applied
Checking 002.sql... already applied
Checking 003.sql... new migration
$
```

#### rickdb migrate &lt;path&gt;

This command executes the new migrations, one by one, from the specified directory, ordered by file name. If any error occurs,
execution is aborted. The migrations are not executed within a transaction, due to varying transaction support in 
database engines; any required transaction blocks must be explicit, or there is always the possibility of failure in the
middle of a multi-statement migration. Partially failed migrations are not registered (because execution is aborted), and
should be handled manually.

```shell
$ rickdb migrate migrations/
Executing 001.sql... skipping, already applied
Executing 002.sql... skipping, already applied
Executing 003.sql... success
$
```

## Flattening migrations

During a schema-first application lifecycle, it is common to periodically combine all the migrations in a single sql
file, or to replace them with a clean schema dump instead. This way, the number of migration files is kept to a sane level
while assuming a certain schema state (either from a backup or from a plain file).

When this is done, it is necessary to "notify" the migration manager that all the applied migrations ceased to exist, and
now reside on a specific file **to be ignored** (except on clean deploys), as migrations have already been applied.

To remove all those applied migration names and replace them with a single entry with a custom name, we use the 
**flatten** command:
```shell
$ rickdb flatten schema.sql
Flattening all migrations to schema.sql... success
```
In the above example, the migration manager will remove all information of applied migrations, and create a single entry
with schema.sql as migration name.

## Generating DTOs 

In addition to the Migration Manager functionalities, rickdb cli also provides basic code-generation capabilities based
on the object mapper - specifically, the capability of generating field mapper class definitions from database objects - 
tables and views:

```python
$ rickdb dto page page.py
DAO written to file page.py
$ cat page.py 
from rick_db import fieldmapper


@fieldmapper(tablename='page', pk='id_page')
class Page:
    id = 'id_page'
    crawled = 'crawled'
    url = 'url'
    type = 'type'
    title = 'title'
    description = 'description'
    breadcrumbs = 'breadcrumbs'
```

And, of course, PostgreSQL schemas are supported out-of-the-box, too:
```python
$ rickdb dto test.some_page page.py
DAO written to file page.py
$ cat page.py 
from rick_db import fieldmapper


@fieldmapper(tablename='some_page', schema='test', pk='id_page')
class SomePage:
    id = 'id_page'
    crawled = 'crawled'
    url = 'url'
    type = 'type'
    title = 'title'
    description = 'description'
    breadcrumbs = 'breadcrumbs'
```
