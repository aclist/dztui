from typing import Any
from pathlib import Path

from dzgui.util._json import read_json

from dzgui.const.enum import Preferences
from dzgui.const.constants import STEAM_CMD, FLATPAK_RUN_CMD, FLATPAK_SANDBOX


class ConfigFileError(Exception):
    pass


def lookup(path: Path, enum: Preferences) -> Any:
    if path.is_file() is False:
        raise ConfigFileError("Not a valid file")

    key = enum_to_key(enum)
    config = get_config(path)
    try:
        return config[key]
    except KeyError:
        return None


def get_config(path: Path) -> dict:
    # TODO: is this being called twice?
    try:
        json = read_json(path)
    except Exception as e:
        raise e
    return json


def get_favorites(path: Path) -> list[str]:
    try:
        conf = get_config(path)
    except Exception:
        pass
    return conf["ip_list"]


def is_in_favs(record: str, path: Path) -> bool:
    favs = get_favorites(path)
    if record in favs:
        return True
    return False


def enum_to_key(enum: Preferences) -> str:
    return enum.dict["key"]


def get_client_index(client: str) -> int:
    if client == STEAM_CMD:
        return 0
    elif client == FLATPAK_RUN_CMD:
        return 1
    elif client == FLATPAK_SANDBOX:
        return 2
    else:
        return 0
