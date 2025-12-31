import re

from dzgui.util.localize import number
from dzgui.util.strings import no_mods, no_servers, distance_suffix

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk # noqa E402


def format_pango(text: str) -> str:
    medium = '<span size="medium"><b>'
    large = '<span size="large"><b>'
    xlarge = '<span size="x-large"><b>'
    text = re.sub("^# ", xlarge, text, flags=re.M)
    text = re.sub("^## ", large, text, flags=re.M)
    text = re.sub("^### ", medium, text, flags=re.M)
    text = re.sub(r"(<span size=.*)", r"\1</b></span>", text)
    return text


def pluralize(plural: str, count: int) -> str:
    suffix = plural[-2:]
    if suffix == "es":
        base = plural[:-2]
        return f"{base}{'es'[:2*count ^ 2]}"
    else:
        base = plural[:-1]
        return f"{base}{'s'[:count ^ 1]}"


def format_hyperlinks(text: str) -> str:
    def href(string: str) -> str:
        return f'<a href="{string}">{string}</a>'

    reg = r"\s(www\.*?)"
    text = re.sub(reg, " http://" + r"\1", text)
    reg2 = r"(http.*?)([ ,\r\n]|$)"
    text = re.sub(reg2, href(r"\1") + r"\2", text)
    return text


def format_mods(size: int, mods: int) -> str:
    if mods == 0:
        return no_mods
    l_size = number(size)
    plural = pluralize("mods", mods)
    return f"Found {mods:n} {plural} taking up {l_size} MiB"


def format_player_count(model: Gtk.TreeModel | None) -> str:
    players = 0
    hits: int
    status: str
    if model is None or len(model) == 0:
        return no_servers
    else:
        hits = len(model)
        for row in model:
            players += row[4]
    players_pretty = pluralize("players", players)
    hits_pretty = pluralize("matches", hits)
    suffix = distance_suffix
    status = f"Found {hits:n} {hits_pretty} with {players:n} {players_pretty}"
    return f"{status} | {suffix}"


def embolden(text: str) -> str:
    return f"<b>{text}</b>"
