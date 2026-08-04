import copy
from collections.abc import Mapping
from rick_db import Repository

from rick_db.keyset import Keyset
from rick_db.sql import Select, Literal


class DbGrid:
    SEARCH_NONE = 0
    SEARCH_ANY = 1
    SEARCH_START = 2
    SEARCH_END = 3

    search_map = {SEARCH_START: "{}%", SEARCH_ANY: "%{}%", SEARCH_END: "%{}"}

    def __init__(
        self,
        repo: Repository,
        search_fields: list = None,
        search_type: int = None,
        case_sensitive=False,
    ):
        """
        Constructor
        :param repo: Repository to use
        :param search_fields: list of valid field names that can be searched
        :param search_type: one of SEARCH_NONE, SEARCH_ANY, SEARCH_START, SEARCH_END
        :param case_sensitive: if True, search will use LIKE instead of ILIKE
        """
        if not search_fields:
            search_fields = []
        if search_type is None:
            search_type = self.SEARCH_ANY
        else:
            if search_type != self.SEARCH_NONE:
                if search_type not in self.search_map:
                    raise ValueError("search type '%s' is not supported" % search_type)

        self._repo = repo
        record = repo.record_class()()
        self._fields = record.dbfields()
        self._field_pk = getattr(record, "_pk", None)

        for field in search_fields:
            if field not in self._fields:
                raise ValueError(
                    "search field '%s' does not exist in the Record" % field
                )

        self._search_type = search_type
        self._search_fields = search_fields
        self._case_sensitive = case_sensitive is True
        self._ilike = repo.dialect.ilike

    def default_query(self) -> Select:
        """
        Build a default query. Can be overridden on descendants
        :return: Select() for "select * from table"
        """
        return self._repo.select()

    def default_sort(self) -> dict:
        """
        Build default sort dictionary. Can be overridden on descendants
        The default sort order is primary_key DESC
        :return: dict
        """
        if self._field_pk:
            return {self._field_pk: "ASC"}
        return {}

    def default_keyset(self) -> "Keyset":
        """
        Build a default keyset. Can be overridden on descendants
        The default keyset is the primary key, ascending
        :return: Keyset
        """
        if not self._field_pk:
            raise ValueError(
                "default_keyset(): Record has no primary key; pass an explicit "
                "keyset to run_seek()"
            )
        return Keyset(self._field_pk, Keyset.ASC, unique=True)

    def _assemble(
        self,
        qry: Select = None,
        search_text: str = None,
        match_fields: dict = None,
        sort_fields: dict = None,
        search_fields: list = None,
        apply_sort: bool = True,
    ) -> Select:
        """
        Assembles a query for a run() operation

        search_text is applied by default to all fields  present in search_fields and are OR'ed; this list can be reduced
        by specifying search_fields

        match_fields contains fieldnames and values to be matched for equality; they are AND'ed;

        :param qry: optional Select query
        :param search_text: optional search string
        :param match_fields: optional field filter
        :param sort_fields: optional sort fields in the format {field_name: order}
        :param search_fields: optional search fields
        :return: Select
        """

        if not qry:
            qry = self.default_query()
        if not apply_sort:
            # the caller supplies the ordering (see run_seek(), where the keyset
            # is the ordering and a default sort would contradict it)
            sort_fields = None
        elif not sort_fields:
            sort_fields = self.default_sort()

        if match_fields:
            qry.where_and()
            for field, value in match_fields.items():
                if field not in self._fields:
                    raise ValueError(
                        "field '%s' used in match_field does not exist on Record"
                        % field
                    )
                qry.where(field, "=", value)
            qry.where_end()

        if search_text:
            qry.where_and()
            if self._search_type == self.SEARCH_NONE:
                raise RuntimeError("search is not allowed")

            if len(self._search_fields) == 0:
                raise RuntimeError("no available fields are mapped as searchable")

            if search_fields:
                # ensure search_fields only has allowed field names
                tmp = []
                for field in search_fields:
                    if field in self._search_fields:
                        tmp.append(field)
                search_fields = tmp

            if not search_fields:
                # either search_fields was not passed as parameter, or had invalid fields
                search_fields = self._search_fields

            search_str = str(search_text)
            mask = self.search_map[self._search_type].replace("{}", search_str)

            operand = "LIKE"
            psql_mode = False
            if not self._case_sensitive:
                if self._ilike:
                    operand = "ILIKE"
                    psql_mode = True
            else:
                psql_mode = True

            if psql_mode:
                for field in search_fields:
                    qry.orwhere(field, operand, mask)
            else:
                mask = mask.upper()
                for field in search_fields:
                    # note: assuming non-pg operation does NOT support schemas or is referencing ambiguous fields
                    field = self._repo.dialect.field(field)
                    qry.orwhere(Literal("UPPER({})".format(field)), operand, mask)
            qry.where_end()

        if sort_fields:
            if not isinstance(sort_fields, Mapping):
                raise ValueError("'sort_fields' parameter must be a dict")
            for field, order in sort_fields.items():
                if field in self._fields:
                    qry.order(field, order.upper())
                else:
                    raise ValueError(
                        "field '%s' used for sorting does not exist on Record" % field
                    )

        return qry

    def run(
        self,
        qry: Select = None,
        search_text: str = None,
        match_fields: dict = None,
        limit: int = None,
        offset: int = None,
        sort_fields: dict = None,
        search_fields: list = None,
    ) -> tuple:
        """
        Executes a query and returns the total row count matching the query, as well as the records within the specified
        range.

        If no query specified, a default query is built; If no sort dict specified, the default sort is used;
        If limit is omitted, all results are returned

        search_text is applied to all fields present in search_fields and are OR'ed;
        match_fields contains fieldnames and values to be matched for equality; they are AND'ed;

        :param qry: optional Select query
        :param search_text: optional search string
        :param match_fields: optional field filter
        :param limit: optional limit
        :param offset: optional offset (ignored if no limit)
        :param sort_fields: optional sort fields in the format {field_name: order}
        :param search_fields: optional search fields
        :return: tuple(total_row_count, filtered_rows)
        """

        # assemble query
        qry = self._assemble(
            qry=qry,
            search_text=search_text,
            match_fields=match_fields,
            sort_fields=sort_fields,
            search_fields=search_fields,
        )

        # execute query
        return self._repo.list(qry, limit=limit, offset=offset)

    def run_seek(
        self,
        limit: int,
        cursor: str = None,
        keyset: Keyset = None,
        qry: Select = None,
        search_text: str = None,
        match_fields: dict = None,
        search_fields: list = None,
    ) -> tuple:
        """
        Executes a query for one keyset-paginated page, and returns the rows
        together with the cursor for the next page.

        The keyset counterpart to run(). Where run() answers "N rows at offset
        M" and reports the total, this answers "the N rows after this cursor"
        and reports whether there is another page. The database seeks to the
        cursor on the index instead of counting rows it will discard, so a deep
        page costs what the first one costs, and rows do not shift across page
        boundaries when the table is written to mid-scroll.

        There is deliberately no sort_fields parameter: the keyset IS the
        ordering. Accepting both would let a caller sort by one column and seek
        on another, which returns wrong pages rather than an error.

        Pass cursor=None for the first page; pass the returned cursor for the
        next. A None cursor comes back when the page is the last one.

        search_text and match_fields behave exactly as in run().

        :param limit: rows per page; must be a positive integer
        :param cursor: cursor from a previous call, or None for the first page
        :param keyset: optional Keyset; defaults to default_keyset()
        :param qry: optional Select query
        :param search_text: optional search string
        :param match_fields: optional field filter
        :param search_fields: optional search fields
        :return: tuple(rows, next_cursor)
        """
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("run_seek(): limit must be a positive integer")

        if keyset is None:
            keyset = self.default_keyset()

        for name in keyset.fields:
            if name not in self._fields:
                raise ValueError(
                    "run_seek(): field '%s' used in keyset does not exist on Record"
                    % name
                )

        # copy before assembling: _assemble() and Keyset.apply() both mutate the
        # query in place, and paging a cursor is a LOOP — reusing one query
        # across pages would otherwise accumulate a WHERE group and an ORDER BY
        # term per page until the statement outgrows the backend's limits.
        # This covers default_query() as well as a caller-supplied qry: an
        # override is free to return a cached Select, and mutating that would
        # corrupt run() too, not just the next page.
        qry = copy.deepcopy(qry if qry is not None else self.default_query())

        qry = self._assemble(
            qry=qry,
            search_text=search_text,
            match_fields=match_fields,
            search_fields=search_fields,
            apply_sort=False,
        )
        qry = keyset.apply(qry, cursor)

        rows, has_more = self._repo.seek(qry, limit)
        # A NULL in a keyset column cannot be seeked past: every comparison
        # against it is NULL, so such rows are excluded by the predicate on
        # every page after the first and the walk simply ends short. It cannot
        # be refused at construction — nullability is not on the Record — but
        # any NULL that does surface is proof the precondition is broken, so
        # say so rather than returning a page from a walk that is already
        # losing rows.
        keyset.assert_no_nulls(rows)
        next_cursor = keyset.encode(rows[-1]) if has_more and rows else None
        return rows, next_cursor
