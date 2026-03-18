"""
JSON field operations with PostgreSQL.

Demonstrates:
 - PgJsonField extraction (->>, ->)
 - Bracket notation for nested access
 - json_where() for filtering on JSON fields
 - json_extract() for selecting JSON values
 - Contains and path queries

Note: These examples generate SQL strings; they require a PostgreSQL
connection to execute.
"""
from rick_db.sql import Select, PgJsonField, PgSqlDialect, Literal

dialect = PgSqlDialect()


# -- Basic JSON extraction --

jf = PgJsonField("metadata", dialect)

# Extract as text (uses ->>)
qry, _ = (
    Select(dialect)
    .from_("events", ["id", jf.extract_text("name", alias="event_name")])
    .assemble()
)
# SELECT "id","metadata"::jsonb->>'name' AS "event_name" FROM "events"
print("=== Extract text ===")
print(qry)


# Extract as JSON object (uses ->, preserves type)
qry, _ = (
    Select(dialect)
    .from_("events", ["id", jf.extract_object("payload", alias="event_payload")])
    .assemble()
)
print("\n=== Extract object ===")
print(qry)


# -- Bracket notation for nested access --

jf = PgJsonField("profile", dialect)

# Access nested fields: profile->"address"->"city"
# Bracket notation returns a PgJsonField; wrap with Literal() for use in where()
city_field = Literal(str(jf["address"]["city"]))
qry, values = (
    Select(dialect)
    .from_("users")
    .where(city_field, "=", "New York")
    .assemble()
)
print("\n=== Nested bracket notation ===")
print(qry)
print("values:", values)


# -- WHERE on JSON fields using json_where --

qry, values = (
    Select(dialect)
    .from_("users")
    .json_where("profile", "active", "=", True)
    .assemble()
)
print("\n=== json_where ===")
print(qry)
print("values:", values)


# -- JSON extraction in SELECT using json_extract --

qry, _ = (
    Select(dialect)
    .from_("users", ["id"])
    .json_extract("profile", "name", "user_name")
    .assemble()
)
print("\n=== json_extract ===")
print(qry)


# -- Contains check (@>) --

jf = PgJsonField("tags", dialect)
expr = jf.contains('["python", "sql"]')
print("\n=== Contains ===")
print(str(expr))


# -- Path query (PostgreSQL 12+, uses @?) --

jf = PgJsonField("data", dialect)
expr = jf.path_query("$.items[*].name")
print("\n=== Path query ===")
print(str(expr))


# -- Combined example: filter + extract + sort --

jf = PgJsonField("metadata", dialect)
qry, values = (
    Select(dialect)
    .from_("events", {
        "id": None,
        "event_type": None,
        jf.extract_text("severity", alias="severity"): None,
        jf.extract_text("source", alias="source"): None,
    })
    .where("event_type", "=", "error")
    .json_where("metadata", "severity", "=", "critical")
    .order("id", Select.ORDER_DESC)
    .limit(50)
    .assemble()
)
print("\n=== Combined filter + extract ===")
print(qry)
print("values:", values)
