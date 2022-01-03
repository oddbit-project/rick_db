import importlib
import sys
from pathlib import Path
from typing import Optional

from rick_db.cli.command import BaseCommand
from rick_db.cli.config import ConfigFile
from rick_db.util import ConsoleWriter, MigrationManager


class CliManager:
    ENV_NAME = "RICKDB_CONFIG"
    CMD_DEFAULT = "help"
    DB_FACTORIES = {
        '_pgsql': ['pg', 'pgsql', 'postgres'],
        '_sqlite': ['sqlite', 'sql3', 'sqlite3']
    }

    def __init__(self, prog_name: str, tty: ConsoleWriter, cfg: dict):
        """
        Constructor
        :param prog_name: program name (manage.py)
        :param tty: ConsoleWriter object
        :param cfg: config dict (from ConfigFile.load())
        """
        self._prog_name = prog_name
        self._cfg = cfg
        self._tty = tty
        # load rick_db commands
        self._cmds = self.discover('rick_db.cli.commands', Path(__file__).parent / 'commands')
        if len(self._cmds) == 0:
            raise RuntimeError("could not detect commands, something went wrong")

    def dispatch(self, args: list) -> int:
        """
        Parse and execute command
        :param args: sys.argv[] without the program name
        :return: exit code (0 if success, <0 if error)
        """
        db_name = ConfigFile.KEY_DEFAULT
        if len(args) == 0:
            cmd = self.CMD_DEFAULT
        else:
            cmd = args.pop(0)

        if cmd not in self._cmds.keys():
            # first argument is either a wrong command, or a database name
            if len(args) == 0:
                self._tty.error(
                    "Error : invalid command '{cmd}'; try '{name} help'".format(cmd=cmd, name=self._prog_name))
                return -1

            db_name = ConfigFile.KEY_PREFIX + cmd
            if db_name not in self._cfg.keys():
                self._tty.error("Error : database '{db}' not found in the config file".format(db=cmd))
                return -2

            # first arg is a database, extract actual command
            cmd = args.pop(0)
            if cmd not in self._cmds.keys():
                self._tty.error(
                    "Error : invalid command '{cmd}'; try '{name} help'".format(cmd=cmd, name=self._prog_name))
                return -1

        else:
            if db_name not in self._cfg.keys():
                self._tty.error("Error : default database configuration not found in the config file")
                return -2

        # build database connection
        mgr = self._resolve_db(db_name)
        if mgr is None:
            return -3

        if self._cmds[cmd].run(mgr, args, self._cmds):
            return -4
        return 0

    def _resolve_db(self, db_name: str) -> Optional[MigrationManager]:
        """
        Build database connection and instantiate migration manager
        :param db_name: configuration key with database configuration
        :return: MigrationManager instance or None
        """
        cfg = self._cfg[db_name]
        engine = cfg[ConfigFile.KEY_ENGINE]
        del cfg[ConfigFile.KEY_ENGINE]
        factory = None

        for fname, tags in self.DB_FACTORIES.items():
            if engine in tags:
                factory = fname

        if factory is None:
            self._tty.error("Error : engine '{}' is invalid or not supported".format(engine))
            return None
        return getattr(self, factory)(cfg)

    def _pgsql(self, cfg: dict) -> Optional[MigrationManager]:
        """
        Assemble PostgreSQL Migration Manager instance
        :param cfg: Conn parameters
        :return: MigrationManager instance
        """
        # imports are local to avoid direct dependency from drivers
        from rick_db.conn.pg import PgConnection
        from rick_db.util.pg import PgMigrationManager
        try:
            conn = PgConnection(**cfg)
            return PgMigrationManager(conn)
        except Exception as e:
            self._tty.error("Error: {}".format(str(e)))
            return None

    def _sqlite(self, cfg: dict) -> Optional[MigrationManager]:
        """
        Assemble Sqlite Migration Manager instance
        :param cfg: Conn parameters
        :return: MigrationManager instance
        """
        from rick_db.conn.sqlite import Sqlite3Connection
        from rick_db.util.sqlite import Sqlite3MigrationManager
        try:
            conn = Sqlite3Connection(**cfg)
            return Sqlite3MigrationManager(conn)
        except Exception as e:
            self._tty.error("Error: {}".format(str(e)))
            return None

    def discover(self, module_prefix: str, path: Path) -> dict:
        """
        Loads available commands in runtime
        :param module_prefix: module prefix to use on import
        :param path: path to scan for python files
        :return: dict with command_name: object
        """
        cmds = {}
        for p in path.glob('*.py'):
            if p.is_file() and p.name[0] != '_':
                command_ns = '{}.{}'.format(module_prefix, p.name.rsplit('.py')[0])
                loaded = command_ns in sys.modules
                try:
                    module = importlib.import_module(command_ns)
                except ModuleNotFoundError:
                    continue
                else:
                    if loaded:
                        importlib.reload(module)

                    command = getattr(module, 'Command', None)
                    if command is None:
                        raise RuntimeError("command class not found in '%s'" % p.name)

                    if not issubclass(command, BaseCommand):
                        raise RuntimeError("Command class does not extend BaseCommand in '%s'" % p.name)

                    cmds[command.command] = command(self._prog_name, self._tty)
        return cmds


def main():
    tty = ConsoleWriter()
    cfg = ConfigFile()
    if not cfg.exists():
        tty.error("Error: Could not locate configuration file - rickdb.toml")
        exit(-1)

    try:
        cfg = cfg.load()
    except Exception as e:
        tty.error("Error : " + str(e))
        exit(-1)

    args = []
    if len(sys.argv) > 1:
        args = sys.argv[1:]

    mgr = CliManager(Path(sys.argv[0]).name, tty, cfg)
    exit(mgr.dispatch(args))


if __name__ == '__main__':
    main()
