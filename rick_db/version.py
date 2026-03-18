RICK_DB_VERSION = ["2", "2", "1"]


def get_version():
    return ".".join(RICK_DB_VERSION)


__version__ = get_version()
