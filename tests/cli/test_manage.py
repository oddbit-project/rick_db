from rick_db.backend.pg import PgManager
from rick_db.cli.console import ConsoleWriter
from rick_db.cli.manage import CliManager
from rick_db.migrations import BaseMigrationManager


class TestManage:
    progname = "rickdb"

    def test_manage_init_pgsql(self, pg_conn, pg_settings):
        tty = ConsoleWriter()
        pg_settings["engine"] = "pgsql"
        cfg = {
            "db": pg_settings,
        }
        mgr = CliManager(self.progname, tty, cfg)
        assert mgr._prog_name == self.progname
        assert len(mgr._cmds) == 7
        assert mgr.dispatch(["check", "db"]) == -4  # not installed
        assert mgr.dispatch(["init", "db"]) == 0  # install

        # remove migration table
        mgr = PgManager(pg_conn)
        mgr.drop_table(BaseMigrationManager.MIGRATION_TABLE)

    def test_manage_init_sqlite(self):
        tty = ConsoleWriter()
        cfg = {
            "db": {
                "engine": "sqlite",
                "db_file": "file::memory:",
            }
        }
        mgr = CliManager(self.progname, tty, cfg)
        assert mgr._prog_name == self.progname
        assert len(mgr._cmds) == 7
        assert mgr.dispatch(["check", "db"]) == -4  # not installed
        assert mgr.dispatch(["init", "db"]) == 0  # install
