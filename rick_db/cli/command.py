from rick_db.util import ConsoleWriter, MigrationManager


class BaseCommand:
    command = ""
    description = ""

    def __init__(self, prog_name: str, tty: ConsoleWriter):
        self._name = prog_name
        self._tty = tty

    def help(self):
        pass

    def run(self, mgr: MigrationManager, args: list, command_list: dict):
        pass
