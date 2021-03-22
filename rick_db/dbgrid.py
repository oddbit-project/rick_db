from collections.abc import Mapping
from rick_db import Repository

from rick_db.sql import Select, Literal


class DbGrid:
    SEARCH_NONE = 0
    SEARCH_ANY = 1
    SEARCH_START = 2
    SEARCH_END = 3

    search_map = {
        SEARCH_START: '{}%',
        SEARCH_ANY: '%{}%',
        SEARCH_END: '%{}'
    }

    def __init__(self, repo: Repository, search_fields: list = None, search_type: int = None, case_sensitive=False):
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
                if search_type not in self.search_map.keys():
                    raise ValueError("search type '%s' is not supported" % search_type)

        self._repo = repo
        record = repo._record()
        self._fields = record.dbfields()
        self._field_pk = getattr(record, '_pk', None)

        for field in search_fields:
            if field not in self._fields:
                raise ValueError("search field '%s' does not exist in the Record" % field)

        self._search_type = search_type
        self._search_fields = search_fields
        self._case_sensitive = case_sensitive is True
        self._ilike = repo.dialect().ilike

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
            return {self._field_pk: 'ASC'}
        return {}

    def run(self, qry: Select = None, search_text: str = None, match_fields: dict = None, limit: int = None,
            offset: int = None, sort_fields: dict = None) -> tuple:
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
        :return: tuple(total_row_count, filtered_rows)
        """

        if not qry:
            qry = self.default_query()
        if not sort_fields:
            sort_fields = self.default_sort()

        if match_fields:
            qry.where_and()
            for field, value in match_fields.items():
                if field not in self._fields:
                    raise ValueError("field '%s' used in match_field does not exist on Record" % field)
                qry.where(field, '=', value)
            qry.where_end()

        if search_text:
            qry.where_and()
            if self._search_type == self.SEARCH_NONE:
                raise RuntimeError('search is not allowed')

            if len(self._search_fields) == 0:
                raise RuntimeError("no available fields are mapped as searchable")

            mask = self.search_map[self._search_type].format(str(search_text))

            operand = 'LIKE'
            psql_mode = False
            if not self._case_sensitive:
                if self._ilike:
                    operand = 'ILIKE'
                    psql_mode = True
            else:
                psql_mode = True

            if psql_mode:
                for field in self._search_fields:
                    qry.orwhere(field, operand, mask.format(str(search_text)))
            else:
                mask = mask.upper()
                for field in self._search_fields:
                    qry.orwhere(Literal('UPPER({})'.format(field)), operand, mask)
            qry.where_end()

        if sort_fields:
            if not isinstance(sort_fields, Mapping):
                raise ValueError("'sort_fields' parameter must be a dict")
            for field, order in sort_fields.items():
                if field in self._fields:
                    qry.order(field, order.upper())
                else:
                    raise ValueError("field '%s' used for sorting does not exist on Record" % field)

        # perform queries
        return self._repo.list(qry, limit=limit, offset=offset)
