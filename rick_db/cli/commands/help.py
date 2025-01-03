from rick_db.cli.command import BaseCommand
from rick_db.migrations import BaseMigrationManager


class Command(BaseCommand):
    command = "help"
    description = "display general help about available commands"

    def help(self):
        self._tty.header("Usage: {name} help [command]".format(name=self._name))

    def run(self, mgr: BaseMigrationManager, args: list, command_list: dict):
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
            self._tty.header(name, False)
            self._tty.header("\t", False)
            self._tty.success(obj.description)
        self._tty.write("")
        return True
