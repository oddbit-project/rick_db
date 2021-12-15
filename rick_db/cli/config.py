import os
from pathlib import Path
import toml


class ConfigFile:
    CONF_FILE = "rickdb.toml"
    ENV_FILE = "RICKDB_CONFIG"
    KEY_DEFAULT = "db"
    KEY_PREFIX = "db_"
    KEY_PASSFILE = "passfile"
    KEY_PASSWORD = "password"
    KEY_ENGINE = "engine"

    def __init__(self, file: str = None):
        if file is not None:
            self._file = file
        else:
            self._file = os.getenv(self.ENV_FILE, self.CONF_FILE)

    def exists(self) -> bool:
        p = Path(self._file)
        return p.exists() and p.is_file()

    def load(self) -> dict:
        """
        Loads TOML configuration file
        if passfile keys are found on the available configurations, they are automatically expanded to "password" with
        the passfile file content
        :return: dict
        """

        result = {}
        if not self.exists():
            return result

        config = toml.load(self._file)
        for k in config.keys():
            if k.startswith(self.KEY_PREFIX) or k == self.KEY_DEFAULT:
                if type(config[k]) is dict:
                    if self.KEY_ENGINE not in config[k].keys():
                        raise RuntimeError(
                            "missing 'engine' parameter in database configuration key '{}' in {}".format(k, self._file))
                    result[k] = config[k]
                    if self.KEY_PASSFILE in config[k].keys():
                        result[self.KEY_PASSWORD] = self._load_pass(config[k][self.KEY_PASSFILE])
                        del result[self.KEY_PASSFILE]
        return result

    def _load_pass(self, passfile: str) -> str:
        p = Path(passfile)
        if not p.exists() or not p.is_file():
            raise RuntimeError("could not open passfile '{}'".format(passfile))
        with open(p, encoding="utf-8") as f:
            return f.readline()
