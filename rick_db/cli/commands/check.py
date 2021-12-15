from pathlib import Path

from .migrate import Command as MigrateCommand
from rick_db.util import MigrationManager


class Command(MigrateCommand):
    command = "check"
    description = "compares existing migrations with the applied migrations, and list new ones"

    def help(self):
        self._tty.title(self.description)
        self._tty.title("Usage: {name} [database] check <path_to_sql_files>".format(name=self._name))

    def run(self, mgr: MigrationManager, args: list, command_list: dict):
        if not mgr.has_manager():
            self._tty.error("Error : Migration Manager is not installed")
            return False

        if len(args) == 0:
            self._tty.error("Error : missing path to migration files")
            return False

        path = Path(args.pop(0))
        if not path.exists() or not path.is_dir():
            self._tty.error("Error : migration path must be a directory")
            return False

        try:
            for record in self._load_migrations(path):
                mig, content = record
                self._tty.write("Checking {name}... ".format(name=mig.name), False)
                # check if migration is duplicated
                record = mgr.fetch_by_name(mig.name)
                if record is not None:
                    self._tty.write(self._tty.AMBAR.format(content="already applied"))
                # check if migration is obviously empty
                elif content.strip() == "":
                    self._tty.write(self._tty.AMBAR.format(content="empty migration"))
                else:
                    self._tty.write(self._tty.BOLD.format(content="new migration"))

            return True

        except Exception as e:
            self._tty.error("Error : " + str(e))
            return False
