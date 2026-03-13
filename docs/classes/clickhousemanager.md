# Class rick_db.backend.clickhouse.**ClickHouseManager**

This class extends [ManagerInterface](managerinterface.md) to provide a specific ClickHouse implementation.
It uses ClickHouse `system.*` tables for introspection. The `schema` parameter maps to ClickHouse `database`;
when `None`, the connection's current database is used.

The following methods are **NOT** supported, and either return empty lists or raise a *NotImplementedError* exception:

- ClickHouseManager.user_groups()
- ClickHouseManager.create_schema()
- ClickHouseManager.drop_schema()
- ClickHouseManager.kill_clients()

The following methods delegate to their database equivalents (ClickHouse databases are equivalent to schemas):

- ClickHouseManager.schemas() — delegates to databases()
- ClickHouseManager.schema_exists() — delegates to database_exists()
