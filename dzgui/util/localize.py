import os
import locale

def number(num: int | float) -> str:
    spec = ""
    if type(num) is int:
        spec = "%d"
    if type(num) is float:
        spec = "%.2f"
    return locale.format_string(spec, num, grouping=True)


def set_locale():
    locale.setlocale(locale.LC_ALL, "")
    user_loc = loc if (loc := os.getenv("LC_CTYPE")) else "en_US.UTF-8"
    locale.setlocale(locale.LC_NUMERIC, loc)
