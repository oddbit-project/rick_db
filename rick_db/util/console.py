import sys


class ConsoleWriter:
    BLUE = "\033[94m{content}\033[0m"
    GREEN = "\033[92m{content}\033[0m"
    AMBAR = "\033[93m{content}\033[0m"
    RED = "\033[91m{content}\033[0m"
    BOLD = "\033[1m{content}\033[0m"

    def title(self, message, eol=True):
        self._out(self.BOLD, message, eol)

    def info(self, message, eol=True):
        self._out(self.BLUE, message, eol)

    def ok(self, message, eol=True):
        self._out(self.GREEN, message, eol)

    def warn(self, message, eol=True):
        self._err(self.AMBAR, message, eol)

    def error(self, message, eol=True):
        self._err(self.RED, message, eol)

    def write(self, message, eol=True):
        if eol:
            sys.stdout.write(f"{message}\n")
        else:
            sys.stdout.write(f"{message}")

    def _out(self, color: str, message: str, eol=True):
        if eol:
            sys.stdout.write(color.format(content=message) + "\n")
        else:
            sys.stdout.write(color.format(content=message))

    def _err(self, color: str, message: str, eol=True):
        if eol:
            sys.stderr.write(color.format(content=message) + "\n")
        else:
            sys.stderr.write(color.format(content=message))
