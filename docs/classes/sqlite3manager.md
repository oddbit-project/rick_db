# Class rick_db.backend.sqlite.**Sqlite3Manager**

This class extends [ManagerInterface](managerinterface.md) to provide a specific Sqlite3 implementation. 
The following methods are **NOT** supported, and either return empty list or raise a *NotImplemented* exception:

- Sqlite3Manager.schemas()
- Sqlite3Manager.databases()
- Sqlite3Manager.users()
- Sqlite3Manager.user_groups()
- Sqlite3Manager.create_database()
- Sqlite3Manager.database_exists()
- Sqlite3Manager.drop_database()
- Sqlite3Manager.create_schema()
- Sqlite3Manager.schema_exists()
- Sqlite3Manager.drop_schema()
- Sqlite3Manager.kill_clients()
