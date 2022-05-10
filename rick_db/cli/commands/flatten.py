from rick_db.cli.command import BaseCommand
from rick_db.util import MigrationManager, MigrationRecord


class Command(BaseCommand):
    command = "flatten"
    description = "replaces all migration entries in the migration manager with a new one, with a specified name"

    def help(self):
        self._tty.title(self.description)
        self._tty.title("Usage: {name} [database] flatten <name_to_use>".format(name=self._name))

    def run(self, mgr: MigrationManager, args: list, command_list: dict):
        if not mgr.has_manager():
            self._tty.error("Error : Migration Manager is not installed")
            return False

        if len(args) == 0:
            self._tty.error("Error : missing name for flattened migration to be inserted")
            return False

        if len(mgr.list()) == 0:
            self._tty.error("Error : no migrations inserted yet, cannot flatten")
            return False

        try:
            mig = MigrationRecord(name=args.pop(0))
            self._tty.write("Flattening all migrations to {name}... ".format(name=mig.name), False)
            result = mgr.flatten(mig)
            if result.success:
                self._tty.ok("success")
            else:
                self._tty.write(self._tty.RED.format(content="error"))
                self._tty.error("Error : " + result.error)
                return False

        except Exception as e:
            self._tty.error("Error : " + str(e))
            return False
