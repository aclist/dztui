from typing import Any
from pathlib import Path

from dzgui.util._json import read_json

from dzgui.const.enum import Preferences

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


def get_config(path: Path) -> Any:
    # TODO: is this being called multiple times?
    try:
        json = read_json(path)
        return json
    except Exception as e:
        raise e


def get_favorites(path: Path) -> list[str]:
    try:
        conf = get_config(path)
    except Exception:
        pass
    return list(conf["ip_list"])


def enum_to_key(enum: Preferences) -> str:
    return str(enum.dict["key"])
