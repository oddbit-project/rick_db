from rick_db.cli.command import BaseCommand
from rick_db.util import MigrationManager


class Command(BaseCommand):
    command = "help"
    description = "display general help about available commands"

    def help(self):
        self._tty.title("Usage: {name} help [command]".format(name=self._name))

    def run(self, mgr: MigrationManager, args: list, command_list: dict):
        # if command help, display it
        cmd = None
        if len(args) > 0:
            cmd = args.pop(0)
        if cmd is not None:
            if cmd in command_list.keys():
                command_list[cmd].help()
                return True

        # list all commands
        self._tty.write("\nAvailable commands:")
        self._tty.write("=" * 19)
        for name, obj in command_list.items():
            self._tty.title(name, False)
            self._tty.title("\t", False)
            self._tty.ok(obj.description)
        self._tty.write("")
        return True
