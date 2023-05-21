RICK_DB_VERSION = ["1", "1", "2"]


def get_version():
    return ".".join(RICK_DB_VERSION)


__version__ = get_version()
