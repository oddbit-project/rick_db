import pytest

from rick_db.backend.pg import PgConnection, PgConnectionPool, PgManager


@pytest.fixture(params=["conn", "pool"])
def pg_backend(request, pg_settings):
    if request.param == "conn":
        backend = PgConnection(**pg_settings)
    else:
        backend = PgConnectionPool(**pg_settings)

    yield backend

    # teardown
    if isinstance(backend, PgConnectionPool):
        with backend.connection() as conn:
            md = PgManager(conn)
            md.drop_table("_migration")
            md.drop_view("list_animal")
            md.drop_table("animal_type")
            md.drop_table("animal")
            md.drop_table("foo")
            md.drop_schema("myschema", True)
    else:
        md = PgManager(backend)
        md.drop_table("_migration")
        md.drop_view("list_animal")
        md.drop_table("animal_type")
        md.drop_table("animal")
        md.drop_table("foo")
        md.drop_schema("myschema", True)

    backend.close()
