RICK_DB_VERSION = ["1", "0", "8"]


def get_version():
    return ".".join(RICK_DB_VERSION)


__version__ = get_version()
