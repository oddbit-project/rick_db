import pytest

from rick_db.conn.pg import PgConnection
from rick_db.util.pg import PgMetadata
from tests.config import postgres_db, connectSimple


class TestPgMetadata:
    createTable = "create table if not exists animals(legs serial not null primary key, name varchar);"
    dropTable = "drop table if exists animals"
    createSchema = "create schema myschema"
    dropSchema = "drop schema myschema"
    createSchemaTable = "create table if not exists myschema.aliens(legs serial not null primary key, name varchar);"
    dropSchemaTable = "drop table if exists myschema.aliens"
    createView = "create view list_animals as select * from animals"
    dropView = "drop view list_animals"
    createSchemaView = "create view myschema.list_aliens as select * from myschema.aliens"
    dropSchemaView = "drop view myschema.list_aliens"
    createGroup = "create group staff"
    addGroup = "alter group staff add user {user}"
    dropGroup = "drop group staff"

    @pytest.fixture()
    def conn(self) -> PgConnection:
        return connectSimple()

    def test_tables(self, conn):
        pgmeta = PgMetadata(conn)
        # no tables created yet
        tables = pgmeta.tables()
        assert len(tables) == 0
        assert pgmeta.table_exists('animals') is False

        # create one table
        with conn.cursor() as qry:
            qry.exec(self.createTable)

        tables = pgmeta.tables()
        assert len(tables) == 1
        assert tables[0] == 'animals'
        assert pgmeta.table_exists('animals') is True

        # cleanup
        with conn.cursor() as c:
            c.exec(self.dropTable)

        # test with schema
        with conn.cursor() as qry:
            qry.exec(self.createSchema)
        tables = pgmeta.tables('myschema')
        assert len(tables) == 0
        assert pgmeta.table_exists('aliens', 'myschema') is False

        # create one schema table
        with conn.cursor() as qry:
            qry.exec(self.createSchemaTable)
        tables = pgmeta.tables('myschema')
        assert len(tables) == 1
        assert tables[0] == 'aliens'
        assert pgmeta.table_exists('aliens', 'myschema') is True

        # cleanup
        with conn.cursor() as c:
            c.exec(self.dropSchemaTable)
            c.exec(self.dropSchema)

    def test_schemas(self, conn):
        pgmeta = PgMetadata(conn)
        schemas = pgmeta.schemas()
        assert len(schemas) > 2
        assert 'public' in schemas
        assert 'information_schema' in schemas

        # create schema
        with conn.cursor() as c:
            c.exec(self.createSchema)

        schemas = pgmeta.schemas()
        assert 'myschema' in schemas
        assert len(schemas) > 2
        # cleanup
        with conn.cursor() as c:
            c.exec(self.dropSchema)

    def test_databases(self, conn):
        pgmeta = PgMetadata(conn)
        dbs = pgmeta.databases()
        assert len(dbs) > 0
        assert postgres_db['dbname'] in dbs

    def test_views(self, conn):
        pgmeta = PgMetadata(conn)
        # no views created yet
        views = pgmeta.views()
        assert len(views) == 0
        assert pgmeta.view_exists('list_animals') is False

        # create one table
        with conn.cursor() as qry:
            qry.exec(self.createTable)
            qry.exec(self.createView)

        views = pgmeta.views()
        assert len(views) == 1
        assert views[0] == 'list_animals'
        assert pgmeta.view_exists('list_animals') is True

        # cleanup
        with conn.cursor() as qry:
            qry.exec(self.dropView)
            qry.exec(self.dropTable)

        # test with schema
        with conn.cursor() as qry:
            qry.exec(self.createSchema)
        views = pgmeta.tables('myschema')
        assert len(views) == 0
        assert pgmeta.view_exists('list_aliens', 'myschema') is False

        # create one schema table
        with conn.cursor() as qry:
            qry.exec(self.createSchemaTable)
            qry.exec(self.createSchemaView)
        views = pgmeta.views('myschema')
        assert len(views) == 1
        assert views[0] == 'list_aliens'
        assert pgmeta.view_exists('list_aliens', 'myschema') is True

        # cleanup
        with conn.cursor() as qry:
            qry.exec(self.dropSchemaView)
            qry.exec(self.dropSchemaTable)
            qry.exec(self.dropSchema)

    def test_table_fields(self, conn):
        pgmeta = PgMetadata(conn)
        with conn.cursor() as qry:
            qry.exec(self.createTable)
            qry.exec(self.createView)

        # test table fields
        fields = pgmeta.table_fields('animals')
        assert len(fields) == 2
        field1, field2 = fields
        assert field1.field == 'legs'
        assert field1.primary is True
        assert field2.field == 'name'
        assert field2.primary is False

        # test view fields
        fields = pgmeta.view_fields('list_animals')
        assert len(fields) == 2
        field1, field2 = fields
        assert field1.field == 'legs'
        assert field1.primary is False  # views don't have keys
        assert field2.field == 'name'
        assert field2.primary is False

        with conn.cursor() as qry:
            qry.exec(self.dropView)
            qry.exec(self.dropTable)

    def test_table_keys(self, conn):
        pgmeta = PgMetadata(conn)
        # create one table
        with conn.cursor() as qry:
            qry.exec(self.createTable)

        # create table
        tables = pgmeta.tables()
        assert len(tables) == 1
        assert tables[0] == 'animals'
        assert pgmeta.table_exists('animals') is True

        keys = pgmeta.table_indexes('animals')
        assert len(keys) == 1
        assert keys[0].field == 'legs'
        assert keys[0].primary is True

        pk = pgmeta.table_pk('animals')
        assert pk.field == keys[0].field
        assert pk.primary == keys[0].primary
        assert pk.type == keys[0].type

        # cleanup
        with conn.cursor() as qry:
            qry.exec(self.dropTable)

        # create table with schema
        with conn.cursor() as qry:
            qry.exec(self.createSchema)
            qry.exec(self.createSchemaTable)

        keys = pgmeta.table_indexes('aliens', 'myschema')
        assert len(keys) == 1
        assert keys[0].field == 'legs'
        assert keys[0].primary is True

        pk = pgmeta.table_pk('aliens', 'myschema')
        assert pk.field == keys[0].field
        assert pk.primary == keys[0].primary
        assert pk.type == keys[0].type

        # cleanup
        with conn.cursor() as qry:
            qry.exec(self.dropSchemaTable)
            qry.exec(self.dropSchema)

    def test_users(self, conn):
        pgmeta = PgMetadata(conn)
        users = pgmeta.users()
        assert len(users) > 0
        names = []
        for r in users:
            names.append(r.name)
        assert postgres_db['user'] in names

    def test_user_groups(self, conn):
        pgmeta = PgMetadata(conn)
        groups = pgmeta.user_groups(postgres_db['user'])
        assert len(groups) == 0

        for r in pgmeta.users():
            print(r.name)
        with conn.cursor() as qry:
            qry.exec(self.createGroup)
            qry.exec(self.addGroup.format(user=postgres_db['user']))

        groups = pgmeta.user_groups(postgres_db['user'])
        assert len(groups) == 1
        assert groups[0] == 'staff'

        with conn.cursor() as qry:
            qry.exec(self.dropGroup)
