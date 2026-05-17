import locale


def number(num: int | float) -> str:
    spec = ""
    if type(num) is int:
        spec = "%d"
    if type(num) is float:
        spec = "%.2f"
    return locale.format_string(spec, num, grouping=True)


def set_locale() -> None:
    locale.setlocale(locale.LC_ALL, "")
