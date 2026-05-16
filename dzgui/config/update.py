from pathlib import Path

from dzgui.const.enum import Preferences
from dzgui.config.query import get_config, enum_to_key
from dzgui.util._json import write_json

# TODO: drop deprecated


# TEST: parametrize writing config values and checking config output in test
def toggle_config(path: Path, key: Preferences) -> None:
    real_key = enum_to_key(key)
    try:
        conf = get_config(path)
        cur_val = conf[real_key]
        conf[real_key] = not cur_val
        write_json(conf, path)
    except Exception as e:
        raise e


def write_config(path: Path, key: Preferences, value: str) -> None:
    real_key = enum_to_key(key)
    try:
        conf = get_config(path)
        conf[real_key] = value
        write_json(conf, path)
    except Exception as e:
        raise e
