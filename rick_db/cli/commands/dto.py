from pathlib import Path

from rick_db.cli.command import BaseCommand
from rick_db.util import MigrationManager
from rick_db.util.metadata import FieldRecord


class Command(BaseCommand):
    command = "dto"
    description = "generate a python data transfer object (DTO) for a given database object"

    def help(self):
        self._tty.title(self.description)
        self._tty.title("Usage: {name} [database] dto <[schema.]table_name> <output_file.py>".format(name=self._name))

    def run(self, mgr: MigrationManager, args: list, command_list: dict):
        if len(args) < 1:
            self._tty.error("Error : Missing table name")
            return False

        if len(args) < 2:
            self._tty.error("Error : Missing output file")
            return False

        view = False
        table_name = args[0].split('.', 1)
        schema = None
        output_file = Path(args[1])

        if output_file.exists():
            self._tty.error("Error : Output file already exists")
            return False

        if len(table_name) > 1:
            schema = table_name[0]
            table_name = table_name[1]
        else:
            table_name = table_name.pop(0)

        meta = mgr.get_meta()
        if not meta.table_exists(table_name, schema):
            view = True
            if not meta.view_exists(table_name, schema):
                self._tty.error("Error : Database object '{}' not found".format(args[0]))
                return False

        if view:
            fields = meta.view_fields(table_name, schema)
        else:
            fields = meta.table_fields(table_name, schema)

        try:
            contents = self._code_gen(table_name, schema, fields)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(contents)
            self._tty.title("DAO written to file {name}".format(name=output_file))
            return True

        except Exception as e:
            self._tty.error("Error : " + str(e))
            return False

    def _code_gen(self, table_name: str, schema: str, fields: list[FieldRecord]) -> str:
        """
        Build Python class definition
        :param table_name: table name
        :param schema: optional schema name
        :param fields: field list
        :return: string
        """
        result = []
        pk = None
        has_id = False
        for f in fields:
            if f.field == 'id':
                has_id = True
            if f.primary:
                pk = f.field

        result.append("from rick_db import fieldmapper")
        result.append("")
        result.append("")

        # build fieldmapper decorator fields
        name = table_name.title().replace("_", "")
        line = ["tablename='{name}'".format(name=table_name)]
        if schema is not None:
            line.append("schema='{schema}'".format(schema=schema))
        if pk is not None:
            line.append("pk='{pk}'".format(pk=pk))

        result.append("@fieldmapper({fields})".format(fields=", ".join(line)))
        result.append("class {name}:".format(name=name))

        for f in fields:
            attr_name = f.field
            if f.primary:
                if not has_id:
                    attr_name = 'id'
            result.append("    {attr} = '{field}'".format(attr=attr_name, field=f.field))

        result.append("")
        return "\n".join(result)
