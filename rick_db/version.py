RICK_DB_VERSION = ["1", "0", "7"]


def get_version():
    return ".".join(RICK_DB_VERSION)


__version__ = get_version()
