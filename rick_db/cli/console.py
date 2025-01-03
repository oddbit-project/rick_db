import sys
from typing import List, Union


class AnsiColor:
    """
    Simple ANSI color format decorator class

    Example:
        color = AnsiColor()
        msg = color.red('red message')
        print(msg)
        msg = color.light_blue('light blue message')
        print(msg)
        msg = color.green('green message')
        print(msg)
        msg = color.green('green message on white background', 'white')
        print(msg)
        msg = color.green('bold green message on white background', 'white', 'bold')
        print(msg)
        msg = color.green('underline bold green message on white background', 'white', ['bold', 'underline'])
        print(msg)
    """

    fg_colors = {
        "black": 30,
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenta": 35,
        "cyan": 36,
        "white": 37,
        "light_black": 90,
        "light_red": 91,
        "light_green": 92,
        "light_yellow": 93,
        "light_blue": 94,
        "light_magenta": 95,
        "light_cyan": 96,
        "light_white": 97,
    }

    bg_colors = {
        "black": 40,
        "red": 41,
        "green": 42,
        "yellow": 43,
        "blue": 44,
        "magenta": 45,
        "cyan": 46,
        "white": 47,
        "light_black": 100,
        "light_red": 101,
        "light_green": 102,
        "light_yellow": 103,
        "light_blue": 104,
        "light_magenta": 105,
        "light_cyan": 106,
        "light_white": 107,
    }
    attrs = {"bold": 1, "dim": 2, "underline": 4, "reversed": 7}

    def __getattr__(self, item):
        if item not in AnsiColor.fg_colors.keys():
            raise RuntimeError("Invalid color name '{}'".format(item))

        # wrapper function to build the final ansi string
        def _result(msg, bg_color=None, attr: Union[List, str] = None):
            result = "\033[" + str(AnsiColor.fg_colors[item]) + "m"
            if bg_color:
                if bg_color not in AnsiColor.bg_colors.keys():
                    raise RuntimeError("Invalid background color '{}'".format(bg_color))
                result += "\033[" + str(AnsiColor.bg_colors[bg_color]) + "m"

            if attr:
                if type(attr) is str:
                    attr = [attr]
                for a in attr:
                    if a not in AnsiColor.attrs.keys():
                        raise RuntimeError("Invalid color attribute '{}'".format(a))
                    result += "\033[" + str(AnsiColor.attrs[a]) + "m"

            return result + msg + "\033[0m"

        return _result


class ConsoleWriter:
    def __init__(self, stdout=sys.stdout, stderr=sys.stderr, colorizer=AnsiColor()):
        self.stdout = stdout
        self.stderr = stderr
        self.colorizer = colorizer

    def header(self, message, eol=True):
        self.write(self.colorizer.white(message, attr="bold"), eol)

    def success(self, message, eol=True):
        self.write(self.colorizer.green(message), eol)

    def warn(self, message, eol=True):
        self.write(self.colorizer.yellow(message), eol)

    def error(self, message, eol=True):
        self.write_error(self.colorizer.red(message), eol)

    def write(self, message, eol=True):
        self.stdout.write(message)
        if eol:
            self.stdout.write("\n")

    def write_error(self, message, eol=True):
        self.stderr.write(message)
        if eol:
            self.stderr.write("\n")
