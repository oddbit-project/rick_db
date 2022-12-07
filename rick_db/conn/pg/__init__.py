import psycopg2
from psycopg2.extensions import register_adapter

from .postgres import (
    PgConnection,
    PgPooledConnection,
    PgConnectionPool,
    PgThreadedConnectionPool,
)

# Enable dict-to-json conversion
register_adapter(dict, psycopg2.extras.Json)
