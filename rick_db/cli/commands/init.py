from rick_db.cli.command import BaseCommand
from rick_db.migrations import BaseMigrationManager


class Command(BaseCommand):
    command = "init"
    description = "install Migration Manager on a database"

    def help(self):
        self._tty.header(self.description)
        self._tty.header("Usage: {name} [database] init".format(name=self._name))

    def run(self, mgr: BaseMigrationManager, args: list, command_list: dict):
        if mgr.is_installed():
            self._tty.warn("Warning : Migration Manager is already installed")
            return True

        result = mgr.install()
        if result.success:
            self._tty.success("Migration Manager installed sucessfully!")
            return True

        self._tty.error("Error : " + result.error)
        return False
