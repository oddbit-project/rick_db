from datetime import datetime

from rick_db.cli.command import BaseCommand
from rick_db.util import MigrationManager


class Command(BaseCommand):
    command = "list"
    description = "list applied migrations, sorted by time"

    def help(self):
        self._tty.title("List applied migrations")
        self._tty.title("Usage: {name} [database] list".format(name=self._name))

    def run(self, mgr: MigrationManager, args: list, command_list: dict):
        if not mgr.has_manager():
            self._tty.error("Error : Migration Manager is not installed")
            return False

        for migration in mgr.list():
            if isinstance(migration.applied, datetime):
                dt = migration.applied.strftime('%d/%m/%Y %H:%M:%S')
            else:
                dt = str(migration.applied)
            self._tty.write(dt + "\t", False)
            self._tty.title(migration.name)
        return True
