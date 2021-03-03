import os

postgres_db = {
    'dbname': os.getenv('POSTGRES_DB', 'testdb'),
    'user': os.getenv('POSTGRES_USER', 'someUser'),
    'password': os.getenv('POSTGRES_PASSWORD', 'somePassword'),
    'host': os.getenv('PG_DB_HOST', ''),
    'port': os.getenv('POSTGRES_PORT', 5432),
}
