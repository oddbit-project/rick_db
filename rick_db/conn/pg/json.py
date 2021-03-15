from psycopg2._json import Json
from psycopg2.extensions import register_adapter

# Enable dict-to-json conversion
register_adapter(dict, Json)
