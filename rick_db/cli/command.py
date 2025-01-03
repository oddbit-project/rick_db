from .console import ConsoleWriter, AnsiColor
from ..migrations import BaseMigrationManager


class BaseCommand:
    command = ""
    description = ""

    def __init__(self, prog_name: str, tty: ConsoleWriter):
        self._name = prog_name
        self._tty = tty
        self._color = AnsiColor()

    def help(self):
        pass

    def run(self, mgr: BaseMigrationManager, args: list, command_list: dict):
        pass
