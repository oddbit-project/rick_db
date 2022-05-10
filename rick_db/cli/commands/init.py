from rick_db.cli.command import BaseCommand
from rick_db.util import MigrationManager


class Command(BaseCommand):
    command = "init"
    description = "install Migration Manager on a database"

    def help(self):
        self._tty.title(self.description)
        self._tty.title("Usage: {name} [database] init".format(name=self._name))

    def run(self, mgr: MigrationManager, args: list, command_list: dict):
        if mgr.has_manager():
            self._tty.warn("Warning : Migration Manager is already installed")
            return True

        result = mgr.install_manager()
        if result.success:
            self._tty.ok("Migration Manager installed sucessfully!")
            return True

        self._tty.error("Error : " + result.error)
        return False
