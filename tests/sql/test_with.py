import pytest
from rick_db import fieldmapper
from rick_db.sql import Update, Select, Literal, Sql
from rick_db.sql import With


@fieldmapper(tablename="folder", pk="id_folder")
class FolderRecord:
    id = "id_folder"
    parent = "fk_parent"


with_cases = [
    [
        # name
        "w",
        # with_query
        Select().from_("big_table"),
        # columns
        [],
        # query
        Select().from_("w").where("key", "=", 123),
        # materialized?
        True,
        # expected result
        'WITH "w" AS (SELECT "big_table".* FROM "big_table") SELECT "w".* FROM "w" WHERE ("key" = ?)',
    ],
    [
        # name
        "w",
        # with_query
        Select().from_("big_table"),
        # columns
        [],
        # query
        Select().from_("w").where("key", "=", 123),
        # materialized?
        False,
        # expected result
        'WITH "w" AS NOT MATERIALIZED (SELECT "big_table".* FROM "big_table") SELECT "w".* FROM "w" WHERE ("key" = ?)',
    ],
]

with_cases_multi = [
    [
        [
            # first cte
            [
                # name
                "sales_per_make",
                # first query
                Select()
                .from_(
                    "cars",
                    cols={
                        "car_make": None,
                        Literal("SUM(sales)"): "total_sales_per_make",
                    },
                )
                .join("car_sales", "cars_id", "cars", "id")
                .group(["car_make"]),
                # columns
                [],
            ],
            # second cte
            [
                # name
                "sales_sum",
                # first query
                Select().from_(
                    "car_sales", cols={Literal("SUM(sales)"): "total_sales"}
                ),
                # columns
                [],
            ],
        ],
        # CTE query
        Select()
        .from_("sales_per_make", cols=["car_make", "total_sales_per_make"])
        .from_("sales_sum", cols=["total_sales"]),
        # Expected result
        'WITH "sales_per_make" AS (SELECT "car_make",SUM(sales) AS "total_sales_per_make" FROM "cars" INNER JOIN "car_sales" ON "cars"."id"="car_sales"."cars_id" GROUP BY "car_make"),"sales_sum" AS (SELECT SUM(sales) AS "total_sales" FROM "car_sales") SELECT "car_make","total_sales_per_make","total_sales" FROM "sales_per_make", "sales_sum"',
    ]
]

with_recursive_cases = [
    [
        # name
        "tree",
        # with_query
        Select().union(
            [
                Select().from_({FolderRecord: "f1"}).where(FolderRecord.id, "=", 19),
                Select()
                .from_({FolderRecord: "f2"})
                .join("tree", FolderRecord.parent, "f2", FolderRecord.id),
            ],
            Sql.SQL_UNION_ALL,
        ),
        # columns
        [],
        # query
        Select().from_("tree"),
        # result
        'WITH RECURSIVE "tree" AS (SELECT "f1".* FROM "folder" AS "f1" WHERE ("id_folder" = ?) UNION ALL SELECT "f2".* FROM "folder" AS "f2" INNER JOIN "tree" ON "f2"."id_folder"="tree"."fk_parent") SELECT "tree".* FROM "tree"',
    ],
    [
        # name
        "t",
        # with query
        Select().union(
            [
                Literal("VALUES(1)"),
                Select().from_("t", cols=[Literal("n+1")]).where("n", "<", 100),
            ]
        ),
        # columns
        ["n"],
        # query
        Select().from_("t", cols={Literal("SUM(n)"): "total"}),
        # result
        'WITH RECURSIVE "t"("n") AS (VALUES(1) UNION SELECT n+1 FROM "t" WHERE ("n" < ?)) SELECT SUM(n) AS "total" FROM "t"',
    ],
    [
        # name
        "search_tree",
        # with query
        Select().union(
            [
                Select().from_(
                    {"tree": "t"}, cols=["id", "link", "data", Literal("0")]
                ),
                Select()
                .from_({"tree": "t"}, cols=["id", "link", "data", Literal("depth+1")])
                .join({"search_tree": "st"}, "link", "t", "id"),
            ],
            Sql.SQL_UNION_ALL,
        ),
        # columns
        ["id", "link", "data", "depth"],
        # query
        Select().from_("search_tree").order("depth"),
        # result
        'WITH RECURSIVE "search_tree"("id","link","data","depth") AS (SELECT "t"."id","t"."link","t"."data",0 FROM "tree" AS "t" UNION ALL SELECT "t"."id","t"."link","t"."data",depth+1 FROM "tree" AS "t" INNER JOIN "search_tree" AS "st" ON "t"."id"="st"."link") SELECT "search_tree".* FROM "search_tree" ORDER BY "depth" ASC',
    ],
]


@pytest.mark.parametrize(
    "name, with_query, columns, query, materialized, result", with_cases
)
def test_with(name, with_query, columns, query, materialized, result):
    qry = With().clause(name, with_query, columns, materialized).query(query)
    sql, _ = qry.assemble()
    assert sql == result


@pytest.mark.parametrize(
    "name, with_query, columns, query,  result", with_recursive_cases
)
def test_with_recursive(name, with_query, columns, query, result):
    qry = With().recursive().clause(name, with_query, columns).query(query)
    sql, _ = qry.assemble()
    assert sql == result


@pytest.mark.parametrize("clauses, query, result", with_cases_multi)
def test_with_multi(clauses, query, result):
    qry = With()
    for c in clauses:
        qry.clause(c[0], c[1], c[2])

    qry.query(query)
    sql, _ = qry.assemble()
    assert sql == result
