import pytest
from rick_db import fieldmapper
from rick_db.sql import Update, Select, Literal, Sql
from rick_db.sql import With


@fieldmapper(tablename='folder', pk='id_folder')
class FolderRecord:
    id = 'id_folder'
    parent = 'fk_parent'


with_recursive_cases = [
    [
        # name
        "tree",
        # with_query
        Select().union([
            Select().from_({FolderRecord: 'f1'}).where(FolderRecord.id, '=', 19),
            Select().from_({FolderRecord: 'f2'}).join('tree', FolderRecord.parent, 'f2', FolderRecord.id)
        ], Sql.SQL_UNION_ALL),
        # columns
        [],
        # query
        Select().from_("tree"),
        # result
        'WITH RECURSIVE "tree" AS (SELECT "f1".* FROM "folder" AS "f1" WHERE ("id_folder" = ?) UNION ALL SELECT "f2".* FROM "folder" AS "f2" INNER JOIN "tree" ON "f2"."id_folder"="tree"."fk_parent") SELECT "tree".* FROM "tree"'
    ],
    [
        # name
        't',
        # with query
        Select().union([
            Literal("VALUES(1)"),
            Select().from_("t", cols=[Literal("n+1")]).where("n", "<", 100)
        ]),
        # columns
        ['n'],
        # query
        Select().from_("t", cols={Literal("SUM(n)"): "total"}),
        # result
        'WITH RECURSIVE "t"("n") AS (VALUES(1) UNION SELECT n+1 FROM "t" WHERE ("n" < ?)) SELECT SUM(n) AS "total" FROM "t"'
    ]
]


@pytest.mark.parametrize("name, with_query, columns, query,  result", with_recursive_cases)
def test_with_recursive(name, with_query, columns, query, result):
    qry = With().recursive().clause(name, with_query, columns).query(query)
    sql, _ = qry.assemble()
    assert sql == result
