from rick_db.cli.console import ConsoleWriter
from rick_db.cli.manage import CliManager


class TestManage:
    progname = "rickdb"

    def test_manage_init_pgsql(self, pg_settings):
        tty = ConsoleWriter()
        pg_settings["engine"] = "pgsql"
        cfg = {
            "db_pg": pg_settings,
        }
        mgr = CliManager(self.progname, tty, cfg)
        assert mgr._prog_name == self.progname
        assert len(mgr._cmds) == 7
        assert mgr.dispatch(["check"]) == -2

    def test_manage_init_sqlite(self):
        tty = ConsoleWriter()
        cfg = {
            "db_sqlite": {
                "engine": "sqlite",
                "db_file": "/tmp/test.db",
            }
        }
        mgr = CliManager(self.progname, tty, cfg)
        assert mgr._prog_name == self.progname
        assert len(mgr._cmds) == 7
        assert mgr.dispatch(["check"]) == -2
