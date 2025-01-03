from datetime import datetime

from rick_db.cli.command import BaseCommand
from rick_db.migrations import BaseMigrationManager


class Command(BaseCommand):
    command = "list"
    description = "list applied migrations, sorted by time"

    def help(self):
        self._tty.header("List applied migrations")
        self._tty.header("Usage: {name} [database] list".format(name=self._name))

    def run(self, mgr: BaseMigrationManager, args: list, command_list: dict):
        if not mgr.is_installed():
            self._tty.error("Error : Migration Manager is not installed")
            return False

        for migration in mgr.list():
            if isinstance(migration.applied, datetime):
                dt = migration.applied.strftime("%d/%m/%Y %H:%M:%S")
            else:
                dt = str(migration.applied)
            self._tty.write(dt + "\t", False)
            self._tty.header(migration.name)
        return True
