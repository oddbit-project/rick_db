# Examples

Complete, runnable examples are available in the
[examples/](https://github.com/oddbit-project/rick_db/blob/master/examples) directory. SQLite and query
builder examples run standalone with no external dependencies. PostgreSQL, ClickHouse, and bookstore examples
require a running database server.

## Repository

### CRUD with SQLite

Basic insert, fetch, update, and delete operations using an in-memory SQLite database. No external
dependencies required.

```python
{! ../examples/repository/crud_sqlite.py !}
```

**Source:** [examples/repository/crud_sqlite.py](https://github.com/oddbit-project/rick_db/blob/master/examples/repository/crud_sqlite.py)

### Transactions

Transaction context manager with automatic commit on success and rollback on exception. Demonstrates
a funds transfer between accounts.

```python
{! ../examples/repository/transactions.py !}
```

**Source:** [examples/repository/transactions.py](https://github.com/oddbit-project/rick_db/blob/master/examples/repository/transactions.py)

### DbGrid Search

Searchable, filterable, paginated data listings using DbGrid. Shows text search, match filters,
sorting, pagination, and search types.

```python
{! ../examples/repository/dbgrid_search.py !}
```

**Source:** [examples/repository/dbgrid_search.py](https://github.com/oddbit-project/rick_db/blob/master/examples/repository/dbgrid_search.py)

### Bookstore (PostgreSQL)

Custom repository with JOINs and aggregate queries. Requires a running PostgreSQL instance.

```python
{! ../examples/repository/example_bookstore.py !}
```

**Source:** [examples/repository/example_bookstore.py](https://github.com/oddbit-project/rick_db/blob/master/examples/repository/example_bookstore.py)

## Query Builder

### Fn Helper Functions

Aggregate, math, and general SQL functions using the `Fn` class. Covers `COUNT`, `SUM`, `AVG`,
`ROUND`, `COALESCE`, `CAST`, nesting, GROUP BY with HAVING, and dict-style column aliases.

```python
{! ../examples/query_builder/fn_aggregation.py !}
```

**Source:** [examples/query_builder/fn_aggregation.py](https://github.com/oddbit-project/rick_db/blob/master/examples/query_builder/fn_aggregation.py)

### Recursive CTEs

Common Table Expressions with the `With` builder. Includes recursive tree walks, number series
generation, non-recursive CTEs, and multiple CTE clauses.

```python
{! ../examples/query_builder/cte_recursive.py !}
```

**Source:** [examples/query_builder/cte_recursive.py](https://github.com/oddbit-project/rick_db/blob/master/examples/query_builder/cte_recursive.py)

### JSON Queries (PostgreSQL)

JSON field operations using `PgJsonField`. Covers text extraction (`->>`), object extraction (`->`),
bracket notation for nested access, `json_where()`, `json_extract()`, contains checks, and path queries.

```python
{! ../examples/query_builder/json_queries.py !}
```

**Source:** [examples/query_builder/json_queries.py](https://github.com/oddbit-project/rick_db/blob/master/examples/query_builder/json_queries.py)

### Complex Query (PostgreSQL)

Advanced SELECT with subquery joins, Literal expressions for multi-condition ON clauses, and
PostgreSQL system catalog introspection.

```python
{! ../examples/query_builder/complex_query_01.py !}
```

**Source:** [examples/query_builder/complex_query_01.py](https://github.com/oddbit-project/rick_db/blob/master/examples/query_builder/complex_query_01.py)

## Migrations

### Migration Workflow

Programmatic migration workflow using SQLite. Demonstrates installing the migration table, executing
migrations, idempotent re-runs, and schema verification.

```python
{! ../examples/migrations/migration_workflow.py !}
```

**Source:** [examples/migrations/migration_workflow.py](https://github.com/oddbit-project/rick_db/blob/master/examples/migrations/migration_workflow.py)

## ClickHouse

### ClickHouse Example

Connection setup, schema introspection with `ClickHouseManager`, repository CRUD, and aggregate
queries using the query builder. Requires a running ClickHouse server.

```python
{! ../examples/clickhouse/clickhouse_example.py !}
```

**Source:** [examples/clickhouse/clickhouse_example.py](https://github.com/oddbit-project/rick_db/blob/master/examples/clickhouse/clickhouse_example.py)

## Running the Examples

SQLite and query builder examples run directly:

```bash
python examples/repository/crud_sqlite.py
python examples/query_builder/fn_aggregation.py
```

For PostgreSQL and ClickHouse examples, a Docker Compose file is provided:

```bash
# Start database services
docker compose -f examples/docker-compose.yml up -d --wait

# Run an example
python examples/clickhouse/clickhouse_example.py

# Stop services
docker compose -f examples/docker-compose.yml down
```

### Test Harness

A pytest test harness validates all examples:

```bash
# Run only SQLite/query builder tests (no Docker needed)
./examples/run_tests.sh sqlite

# Run all tests (starts and stops Docker automatically)
./examples/run_tests.sh

# Run all tests, keep containers running afterward
./examples/run_tests.sh --no-teardown
```
