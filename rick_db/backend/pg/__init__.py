import psycopg2
from psycopg2.extensions import register_adapter

from .connection import PgConnection
from .pool import PgConnectionPool
from .manager import PgManager
from .pginfo import PgInfo
from .pginfo_records import (
    DatabaseRecord,
    RoleRecord,
    TableSpaceRecord,
    SettingRecord,
    NamespaceRecord,
    TableRecord,
    ColumnRecord,
    ConstraintRecord,
    KeyColumnUsageRecord,
    UserRecord,
    GroupRecord,
    ForeignKeyRecord,
    IdentityRecord,
    SequenceRecord,
)
from .migrations import PgMigrationManager

# Enable dict-to-json conversion
register_adapter(dict, psycopg2.extras.Json)
