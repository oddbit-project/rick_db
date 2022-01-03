from pathlib import Path

from rick_db.cli.command import BaseCommand
from rick_db.util import MigrationManager, MigrationRecord


class Command(BaseCommand):
    command = "migrate"
    description = "execute migrations from the specified location"

    def help(self):
        self._tty.title(self.description)
        self._tty.title("Usage: {name} [database] migrate <path_to_sql_files>".format(name=self._name))

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
                self._tty.write("Executing {name}... ".format(name=mig.name), False)
                # check if migration is duplicated
                record = mgr.fetch_by_name(mig.name)
                if record is not None:
                    self._tty.write(self._tty.AMBAR.format(content="skipping, already applied"))
                # check if migration is obviously empty
                elif content.strip() == "":
                    self._tty.write(self._tty.AMBAR.format(content="skipping, empty migration"))
                else:
                    # seems good, ty to execute
                    result = mgr.execute(mig, content)
                    if result.success:
                        self._tty.ok("success")
                    else:
                        # in case of error, abort
                        self._tty.write(self._tty.RED.format(content="error"))
                        self._tty.error("Error : " + result.error)
                        return False

            return True

        except Exception as e:
            self._tty.error("Error : " + str(e))
            return False

    def _load_migrations(self, path: Path) -> list[tuple]:
        """
        Scan path for sql files and loads contents into a list
        :param path: path to scan
        :return: list of (MigrationRecord, content)
        """
        mig_dict = {}
        for entry in sorted(path.glob('*.sql')):
            if entry.is_file():
                with open(entry, encoding="utf-8") as f:
                    mig_dict[entry.name] = f.read()

        result = []
        for name, contents in mig_dict.items():
            record = MigrationRecord(name=name)
            result.append((record, contents))
        return result
