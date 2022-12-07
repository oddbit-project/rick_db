from rick_db import fieldmapper


@fieldmapper(tablename="pg_database")
class DatabaseRecord:
    id = "oid"
    name = "datname"
    id_owner = "datba"
    encoding = "encoding"
    collation = "datcollate"
    ctype = "datctype"
    is_template = "datistemplate"
    allow_connection = "datallowconn"
    conn_limit = "datconnlimit"
    last_sys_oid = "datlastsysoid"
    frozen_xid = "datfrozenxid"
    min_xid = "datminmxid"
    id_tablespace = "dattablespace"
    acl = "datacl"


@fieldmapper(tablename="pg_roles")
class RoleRecord:
    id = "oid"
    name = "rolname"  # Role name
    is_superuser = "rolsuper"  # Role has superuser privileges
    inherit_privileges = "rolinherit"  # Role automatically inherits privileges of roles it is a member of
    create_roles = "rolcreaterole"  # Role can create more roles
    create_db = "rolcreatedb"  # Role can create databases
    update_catalogs = "rolcatupdate"  # Role can update system catalogs directly. (Even a superuser cannot do this unless this column is true)
    login = "rolcanlogin"  # Role can log in. That is, this role can be given as the initial session authorization identifier
    conn_limit = "rolconnlimit"  # For roles that can log in, this sets maximum number of concurrent connections this role can make. -1 means no limit.
    expires = "rolvaliduntil"  # Password expiry time (only used for password authentication); null if no expiration


@fieldmapper(tablename="pg_user")
class UserRecord:
    name = "usename"  # User name
    id = "usesysid"  # ID of this user
    createdb = "usecreatedb"  # User can create databases
    super = "usesuper"  # User is a superuser
    replication = "userepl"  # User can initiate streaming replication and put the system in and out of backup mode.
    bypassrls = "usebypassrls"  # User bypasses every row-level security policy, see Section 5.8 for more information.
    expires = "valuntil"  # Password expiry time (only used for password authentication)
    defaults = "useconfig"  # Session defaults for run-time configuration variables


@fieldmapper(tablename="pg_group")
class GroupRecord:
    name = "groname"  # Name of the group
    id = "grosysid"  # ID of this group
    roles = "grolist"  # An array containing the IDs of the roles in this group


@fieldmapper(tablename="pg_tablespace")
class TableSpaceRecord:
    name = "spcname"  # Tablespace name
    id_owner = "spcowner"  # Owner of the tablespace, usually the user who created it
    location = "spclocation"  # Location (directory path) of the tablespace
    acl = "spcacl"  # Access privileges
    options = "spcoptions"  # Tablespace-level options, as "keyword=value" strings


@fieldmapper(tablename="pg_settings")
class SettingRecord:
    name = "name"  # Run-time configuration parameter name
    value = "setting"  # Current value of the parameter
    unit = "unit"  # Implicit unit of the parameter
    category = "category"  # Logical group of the parameter
    summary = "short_desc"  # A brief description of the parameter
    description = (
        "extra_desc"  # Additional, more detailed, description of the parameter
    )
    context = "context"  # Context required to set the parameter's value
    var_type = "vartype"  # Parameter type (bool, enum, integer, real, or string)
    source = "source"  # Source of the current parameter value
    min_value = "min_val"  # Minimum allowed value of the parameter (null for non-numeric values)
    max_value = "max_val"  # Maximum allowed value of the parameter (null for non-numeric values)
    enum_options = (
        "enumvals"  # Allowed values of an enum parameter (null for non-enum values)
    )
    boot_value = "boot_value"  # Parameter value assumed at server startup if the parameter is not otherwise set
    reset_value = "reset_val"  # Value that RESET would reset the parameter to in the current session
    source_file = "sourcefile"  # Configuration file the current value was set in (null for values set from sources other than configuration files, or when examined by a non-superuser); helpful when using include directives in configuration files
    source_line = "sourceline"  # Line number within the configuration file the current value was set at (null for values set from sources other than configuration files, or when examined by a non-superuser)


@fieldmapper(tablename="pg_namespace")
class NamespaceRecord:
    name = "nspname"  # Name of the namespace
    id_owner = "nspowner"  # Owner of the namespace
    acl = "nspacl"  # Access privileges; see GRANT and REVOKE for details


@fieldmapper(tablename="tables", schema="information_schema")
class TableRecord:
    catalog = "table_catalog"  # Name of the database that contains the table (always the current database)
    schema = "table_schema"  # Name of the schema that contains the table
    name = "table_name"  # Name of the table
    table_type = "table_type"  # Type of the table: BASE TABLE for a persistent base table (the normal table type), VIEW for a view, FOREIGN TABLE for a foreign table, or LOCAL TEMPORARY for a temporary table
    udt_catalog = "user_defined_type_catalog"  # If the table is a typed table, the name of the database that contains the underlying data type (always the current database), else null.
    udt_schema = "user_defined_type_schema"  # If the table is a typed table, the name of the schema that contains the underlying data type, else null.
    udt_name = "user_defined_type_name"  # If the table is a typed table, the name of the underlying data type, else null.
    is_insertable = "is_insertable_into"  # YES if the table is insertable into, NO if not (Base tables are always insertable into, views not necessarily.)
    is_typed = "is_typed"  # YES if the table is a typed table, NO if not


@fieldmapper(tablename="columns", schema="information_schema")
class ColumnRecord:
    catalog = "table_catalog"  # Name of the database containing the table (always the current database)
    schema = "table_schema"  # Name of the database containing the table (always the current database)
    table_name = "table_name"  # Name of the table
    column = "column_name"  # " Name of the column
    position = "ordinal_position"  # Ordinal position of the column within the table (count starts at 1)
    default_value = "column_default"  # Default expression of the column
    is_identity = "is_identity"  # YES if the column is possibly nullable, NO if it is known not nullable. A not-null constraint is one way a column can be known not nullable, but there can be others.
    is_nullable = "is_nullable"  # YES if the column is possibly nullable, NO if it is known not nullable. A not-null constraint is one way a column can be known not nullable, but there can be others.
    data_type = "data_type"  # Data type of the column, if it is a built-in type, or ARRAY if it is some array (in that case, see the view element_types), else USER-DEFINED (in that case, the type is identified in udt_name and associated columns). If the column is based on a domain, this column refers to the type underlying the domain (and the domain is identified in domain_name and associated columns).
    maxlen = "character_maximum_length"  # If data_type identifies a character or bit string type, the declared maximum length; null for all other data types or if no maximum length was declared.
    byte_len = "character_octet_length"  # If data_type identifies a character type, the maximum possible length in octets (bytes) of a datum; null for all other data types. The maximum octet length depends on the declared character maximum length (see above) and the server encoding.
    numeric_precision = "numeric_precision"  # If data_type identifies a numeric type, this column contains the (declared or implicit) precision of the type for this column. The precision indicates the number of significant digits. It can be expressed in decimal (base 10) or binary (base 2) terms, as specified in the column numeric_precision_radix. For all other data types, this column is null.
    numeric_precision_cardinal = "numeric_precision_radix"  # If data_type identifies a numeric type, this column indicates in which base the values in the columns numeric_precision and numeric_scale are expressed. The value is either 2 or 10. For all other data types, this column is null.
    numeric_scale = "numeric_scale"  # If data_type identifies an exact numeric type, this column contains the (declared or implicit) scale of the type for this column. The scale indicates the number of significant digits to the right of the decimal point. It can be expressed in decimal (base 10) or binary (base 2) terms, as specified in the column numeric_precision_radix. For all other data types, this column is null.
    datetime_precision = "datetime_precision"  # If data_type identifies a date, time, timestamp, or interval type, this column contains the (declared or implicit) fractional seconds precision of the type for this column, that is, the number of decimal digits maintained following the decimal point in the seconds value. For all other data types, this column is null.
    domain_catalog = "domain_catalog"  # If the column has a domain type, the name of the database that the domain is defined in (always the current database), else null.
    domain_schema = "domain_schema"  # If the column has a domain type, the name of the schema that the domain is defined in, else null.
    domain_name = "domain_name"  # If the column has a domain type, the name of the domain, else null.
    udt_catalog = "udt_catalog"  # Name of the database that the column data type (the underlying type of the domain, if applicable) is defined in (always the current database)
    udt_schema = "udt_schema"  # Name of the schema that the column data type (the underlying type of the domain, if applicable) is defined in
    udt_name = "udt_name"  # Name of the column data type (the underlying type of the domain, if applicable)
    data_type_descriptor = "dtd_identifier"  # An identifier of the data type descriptor of the column, unique among the data type descriptors pertaining to the table. This is mainly useful for joining with other instances of such identifiers. (The specific format of the identifier is not defined and not guaranteed to remain the same in future versions.)
    is_updatable = "is_updatable"  # YES if the column is updatable, NO if not (Columns in base tables are always updatable, columns in views not necessarily)


@fieldmapper(tablename="key_column_usage", schema="information_schema")
class KeyColumnUsageRecord:
    constraint_catalog = "constraint_catalog"  # Name of the database that contains the constraint (always the current database)
    constraint_schema = (
        "constraint_schema"  # Name of the schema that contains the constraint
    )
    name = "constraint_name"  # Name of the constraint
    table_catalog = "table_catalog"  # Name of the database that contains the table that contains the column that is restricted by this constraint (always the current database)
    table_schema = "table_schema"  # Name of the schema that contains the table that contains the column that is restricted by this constraint
    table_name = "table_name"  # Name of the table that contains the column that is restricted by this constraint
    column = "column_name"  # Name of the column that is restricted by this constraint
    position = "ordinal_position"  # Ordinal position of the column within the constraint key (count starts at 1)
    position_unique_constraint = "position_in_unique_constraint"  # For a foreign-key constraint, ordinal position of the referenced column within its unique constraint (count starts at 1); otherwise null


@fieldmapper(tablename="table_constraints", schema="information_schema")
class ConstraintRecord:
    catalog = "constraint_catalog"  # Name of the database that contains the constraint (always the current database)
    schema = "constraint_schema"  # Name of the schema that contains the constraint
    const_name = "constraint_name"  # Name of the constraint
    table_catalog = "table_catalog"  # Name of the database that contains the table (always the current database)
    table_schema = "table_schema"  # Name of the schema that contains the table
    table_name = "table_name"  # Name of the table
    constraint_type = "constraint_type"  # Type of the constraint: CHECK, FOREIGN KEY, PRIMARY KEY, or UNIQUE
    is_deferrable = "is_deferrable"  # YES if the constraint is deferrable, NO if not
    initially_deferred = "initially_deferred"  # YES if the constraint is deferrable and initially deferred, NO if not
    column = "column_name"  # Name of the column
    position = "ordinal_position"  # Ordinal position of the column within the table (count starts at 1)


@fieldmapper()
class ForeignKeyRecord:
    schema = "table_schema"  # original schema
    table = "table_name"  # original table name
    column = "column_name"  # original column name
    foreign_schema = "foreign_table_schema"  # foreign table schema
    foreign_table = "foreign_table_name"  # foreign table
    foreign_column = "foreign_column_name"  # foreign field


@fieldmapper(tablename="pg_attribute")
class IdentityRecord:
    column = "attname"
    identity = "attidentity"  # 'a' if generated always, 'd' if generated by default
    generated = "attgenerated"  # if 's', stored
