# Changelog

## [2.3.0]

### Added
- ClickHouse backend support via `clickhouse-connect` HTTP client
  - `ClickHouseConnection` — connection wrapper with DB-API 2.0 compatible cursor and client wrappers
  - `ClickHouseRepository` — repository with ClickHouse mutation syntax (`ALTER TABLE ... UPDATE/DELETE`)
  - `ClickHouseManager` — database introspection using `system.*` tables
  - `ClickHouseMigrationManager` — forward-only migration manager for ClickHouse
  - `ClickHouseUpdate` / `ClickHouseDelete` — SQL builders generating ClickHouse mutation syntax
  - `ClickHouseSqlDialect` — dialect with ClickHouse-specific placeholders, JSON functions, and no `INSERT...RETURNING`
- ClickHouse integration tests using `tox-docker` with `clickhouse/clickhouse-server:25.8`
- `clickhouse-connect>=0.7.0` added to dev dependencies
- `MySqlSqlDialect` — MySQL SQL dialect for the query builder, with backtick identifier quoting, `%s` placeholders, JSON support (`JSON_EXTRACT`, `JSON_UNQUOTE`, `JSON_CONTAINS`, `JSON_CONTAINS_PATH`), no `INSERT...RETURNING`, no `ILIKE` (uses `UPPER()` fallback in DbGrid)

### Changed
- Updated `tox.ini` to include ClickHouse docker service alongside PostgreSQL

### Security
- **sql/dialect.py**: Fixed SQL identifier quoting across all dialects (PostgreSQL, SQLite, ClickHouse) to escape embedded double-quotes by doubling them (SQL standard). Previously, `dialect.table()`, `dialect.field()`, and `dialect.database()` wrapped names in double-quotes without escaping, allowing identifier injection in Manager DDL methods (`create_database`, `drop_database`, `drop_table`, `drop_view`)

## [2.2.0]

### Added
- `json_exclude` parameter on `@fieldmapper` decorator to exclude fields from `asdict()` serialization at the class level
- `exclude` parameter on `asdict()` for per-call field exclusion, merged with class-level defaults
- Excluded fields remain accessible via attribute access, `asrecord()`, `fields()`, and `values()`

## [2.1.0]

### Added
- Nested transaction support via savepoints in `Repository.transaction()` context manager; inner transaction failures automatically doom the outer transaction
- Python 3.12, 3.13, and 3.14 support in classifiers, CI matrix, and tox environments
- `Repository.transaction()`, `begin()`, `commit()`, `rollback()` documented in repository docs

### Changed
- Dropped Python 3.9 support (`pytest` 9.x requires Python >=3.10)
- Bumped `psycopg2` dependency from `>=2.9.2` to `>=2.9.11` (required for Python 3.13+ support)
- Removed Python 3.8 classifier (already unsupported via `python_requires = >=3.9`)
- Updated dev dependencies to latest versions:
  - `pytest` 8.3.4 -> 9.0.2
  - `pytest-cov` 4.0.0 -> 7.0.0
  - `pytest-testdox` 3.0.1 -> 3.1.0
  - `flake8` 6.0.0 -> 7.3.0
  - `flake8-black` 0.3.6 -> 0.4.0
  - `coverage` 7.2.5 -> 7.13.4
  - `tox` 4.5.1 -> 4.49.1
  - `psycopg2-binary` 2.9.3 -> 2.9.11
  - `mkdocs-material` 9.2.7 -> 9.7.4
- CI: bumped `actions/checkout` to v4, `actions/setup-python` to v5, added `allow-prereleases: true` for Python 3.14
- CI: modernized publish workflow to use `python -m build --sdist`

### Bug Fixes

#### Core
- **connection.py**: Renamed `ConnectionError` to `DbConnectionError` to avoid shadowing the Python builtin; backward-compatible alias preserved
- **connection.py**: Fixed `cursor()` context manager to guard against `UnboundLocalError` if `get_cursor()` raises
- **connection.py**: Fixed `!= None` comparison to use `is not None`
- **repository.py**: Fixed `transaction()` context manager to properly rollback on exceptions instead of silently swallowing them
- **repository.py**: Fixed `conn()` context manager to guard against `UnboundLocalError` if `getconn()` raises; added `elif` for pool branch and raises `RepositoryError` if no connection or pool is available
- **profiler/profilers.py**: Fixed `filter_duration()` using non-existent attribute `e.duration` instead of `e.elapsed`
- **dbgrid.py**: Fixed search mask using `.format()` which would raise `KeyError` on brace characters in search text; replaced with `.replace("{}", search_str)`

#### PostgreSQL Backend
- **pg/manager.py**: Fixed `create_database()` overwriting the `args` parameter with kwargs processing; uses separate `parts` list
- **pg/manager.py**: Fixed `create_database()` and `drop_database()` not saving/restoring the original isolation level
- **pg/manager.py**: Fixed `conn()` context manager to use `if/elif/else` pattern with `UnboundLocalError` guard
- **pg/pginfo.py**: Fixed `conn()` context manager with same `if/elif/else` pattern and guard
- **pg/pginfo_records.py**: Fixed typo in `DatabaseRecord.id_owner` field name (`"datba"` corrected to `"datdba"`)
- **pg/pool.py**: Fixed `getconn()` to also catch `psycopg2.InterfaceError` and added generic `except Exception` that safely returns connection to pool before re-raising
- **pg/pool.py**: Fixed `putconn()` to rollback any open transaction before returning connection to pool

#### SQLite Backend
- **sqlite/connection.py**: Added automatic URI detection - `uri=True` is now passed to `sqlite3.connect()` when `db_file` starts with `"file:"`
- **sqlite/manager.py**: Removed `CASCADE` from `drop_table()` and `drop_view()` as SQLite does not support this syntax
- **sqlite/migrations.py**: Replaced `executescript()` with statement-by-statement `exec()` to avoid implicit commits that broke transaction semantics

#### SQL Builder
- **sql/select.py**: Fixed duplicate alias error message using literal `{tbl}` instead of the actual alias value

#### CLI
- **cli/commands/check.py**: Fixed call to non-existent `self._tty.title()` method; changed to `self._tty.header()`
- **cli/commands/flatten.py**: Added missing `return True` after successful flatten operation
- **cli/commands/dto.py**: Fixed success message saying "DAO" instead of "DTO"
- **cli/config.py**: Fixed passfile handling storing password under the raw config key instead of using `self.KEY_PASSWORD` / `self.KEY_PASSFILE` constants

#### Migrations
- **migrations.py**: Added documentation comment noting that `execute()` is not transactional between SQL execution and migration registration

### Documentation
- Fixed `ConnectionError` references to `DbConnectionError` throughout docs
- Fixed `Profiler` references to `ProfilerInterface` in profiler and related docs
- Added transaction methods (`begin()`, `commit()`, `rollback()`, `transaction()`) to repository documentation
- Fixed `update_where` example (wrong method name and missing operator)
- Fixed `DbGrid` class path from `rick_db.sql.DbGrid` to `rick_db.DbGrid`
- Fixed `Registry.fetch_pk()` typo to `Repository.fetch_pk()`
- Fixed `repo.Select()` to `repo.select()` (lowercase)
- Fixed CLI commands in CLAUDE.md: `install` to `init`, `apply` to `migrate`
- Modernized install docs: replaced `python3 setup.py install` with `pip install .`

### Test Improvements
- Consolidated PG test classes using parametrized fixtures (`test_manager.py`, `test_pginfo.py`, `test_migrations.py`)
- Decoupled `base_repository.py` from backend-specific imports (`PgConnection`, `PgConnectionPool`, `Sqlite3Connection`)
- Decoupled `base_cursor.py` from psycopg2; moved `test_duplicate_record` to PG-specific test classes
- Extracted shared helper functions in PG repository and dbgrid tests (`_setup_users`, `_teardown_users`, `_setup_grid`, `_teardown_grid`)
- Created `tests/backend/sqlite/common.py` for shared SQLite DDL constants
- Fixed `sqlite_conn` fixture teardown to use `yield` + `close()` pattern
- Removed redundant `close()` call in SQLite cursor test fixture
- Fixed trailing whitespace and Black formatting across `rick_db/sql/` and test files

### Test Fixes
- **tests/conftest.py**: Changed `sqlite_conn` fixture from `"file::memory:"` to `":memory:"` to fix test isolation (URI was treated as a literal filename without `uri=True`, causing shared state between tests)
- **tests/repository/test_sqlite_repository.py**: Changed fixture from `"file::memory:?cache=shared"` to `":memory:"` (shared cache unnecessary for single connection)
- **tests/dbgrid/test_sqlite_dbgrid.py**: Same fix as above
- **tests/backend/sqlite/test_connection.py**: Added `DROP TABLE test3` cleanup in `test_transaction_rollback_multi` for Python < 3.12 where DDL rollback is not supported
- **tests/backend/sqlite/test_manager.py**: Fixed `drop_table("animals")` to `drop_table("animal")` (table name mismatch)
- **tests/repository/base_repository.py**: Fixed tautological assertion `len(users) == len(users)` to compare against `len(fixture_users)`
- **tests/repository/base_repository.py**: Fixed `isinstance` checks using `self.conn` instead of the `conn` fixture parameter
