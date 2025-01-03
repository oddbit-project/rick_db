"""
Complex example 1: Adapting PgInfo's list_foreign keys query using Query Builder

Features:
 - Select() column limitations;
 - Select() as a source table for JOIN;
 - Arbitrary Literal() expressions for JOIN ON complex expressions;

Original Query:

            SELECT sh.nspname AS table_schema,
              tbl.relname AS table_name,
              col.attname AS column_name,
              referenced_sh.nspname AS foreign_table_schema,
              referenced_tbl.relname AS foreign_table_name,
              referenced_field.attname AS foreign_column_name
            FROM pg_constraint c
                INNER JOIN pg_namespace AS sh ON sh.oid = c.connamespace
                INNER JOIN (SELECT oid, unnest(conkey) as conkey FROM pg_constraint) con ON c.oid = con.oid
                INNER JOIN pg_class tbl ON tbl.oid = c.conrelid
                INNER JOIN pg_attribute col ON (col.attrelid = tbl.oid AND col.attnum = con.conkey)
                INNER JOIN pg_class referenced_tbl ON c.confrelid = referenced_tbl.oid
                INNER JOIN pg_namespace AS referenced_sh ON referenced_sh.oid = referenced_tbl.relnamespace
                INNER JOIN (SELECT oid, unnest(confkey) as confkey FROM pg_constraint) conf ON c.oid = conf.oid
                INNER JOIN pg_attribute referenced_field ON
                    (referenced_field.attrelid = c.confrelid AND referenced_field.attnum = conf.confkey)
            WHERE c.contype = 'f' AND sh.nspname = %s and tbl.relname = %s

"""
from rick_db.backend.pg import PgConnection, ForeignKeyRecord
from rick_db.sql import Select, Literal

db_cfg = {
    'dbname': "rickdb-bookstore",
    'user': "rickdb_user",
    'password': "rickdb_pass",
    'host': "localhost",
    'port': 5432,
    'sslmode': 'require'
}

# Connect to Database
conn = PgConnection(**db_cfg)

schema = 'public'
table_name = 'acl_role_resource'

# Build Query
# subqueries that are used as source join tables
subqry1 = Select(conn.dialect()).from_('pg_constraint', ['oid', {Literal('unnest(conkey)'): 'conkey'}])
subqry2 = Select(conn.dialect()).from_('pg_constraint', ['oid', {Literal('unnest(confkey)'): 'confkey'}])

# Main query

qry, values = Select(conn.dialect()) \
    .from_({'pg_constraint': 'c'},
           # please note: Select() must always select columns from the initial table, so we settle on contype (always 'f')
           cols=['contype']) \
    .join({'pg_namespace': 'sh'}, 'oid', 'c', 'connamespace', cols=[{'nspname': ForeignKeyRecord.schema}]) \
    .join({subqry1: 'con'}, 'oid', 'c', 'oid') \
    .join({'pg_class': 'tbl'}, 'oid', 'c', 'conrelid', cols=[{'relname': ForeignKeyRecord.table}]) \
    .join({'pg_attribute': 'col'}, Literal('col.attrelid=tbl.oid AND col.attnum=con.conkey'),
          # join() does not support multi-condition join on, so we hardcode the condition as a Literal
          cols=[{'attname': ForeignKeyRecord.column}]) \
    .join({'pg_class': 'referenced_tbl'}, 'oid', 'c', 'conrelid', cols={'relname': ForeignKeyRecord.foreign_table}) \
    .join({'pg_namespace': 'referenced_sh'}, 'oid', 'referenced_tbl', 'relnamespace',
          cols=[{'nspname': ForeignKeyRecord.foreign_schema}]) \
    .join({subqry2: 'conf'}, 'oid', 'c', 'oid') \
    .join({'pg_attribute': 'referenced_field'},
          # join() does not support multi-condition join on, so we hardcode the condition as a Literal
          Literal('referenced_field.attrelid = c.confrelid AND referenced_field.attnum = conf.confkey'),
          cols={'attname': ForeignKeyRecord.foreign_column}) \
    .where('contype', '=', 'f') \
    .where({'sh': 'nspname'}, '=', schema) \
    .where({'tbl': 'relname'}, '=', table_name) \
    .assemble()

# execute query
with conn.cursor() as c:
    for r in c.exec(qry, values, cls=ForeignKeyRecord):
        print(r.asdict)
