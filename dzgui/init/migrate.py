import shutil
import sys

from pathlib import Path
from dzgui.const.constants import LEGACY_CONFIG_PATH, LEGACY_COLS_PATH, LEGACY_IPS_PATH
from dzgui.config.convert import rc2json
from dzgui.util._json import read_json, write_json


def migrate_legacy_conf(config: Path) -> None:
    old_conf = Path.home() / LEGACY_CONFIG_PATH
    if old_conf.is_file():
        j = rc2json(old_conf)
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(j)
    else:
        print("Unimplemented. You must have a working dztuirc.")
        sys.exit(1)


def has_new_config(config: Path) -> bool:
    return config.exists()


def migrate_cols_file(res: Path) -> None:
    old_res = Path.home() / LEGACY_COLS_PATH
    if old_res.is_file():
        j = read_json(old_res)
        cols = j["cols"]
        if "View" in cols:
            return
        cols["View"] = cols.pop("Perspective")
        cols["Max"] = cols.pop("Maximum")
        write_json(j, res)


def copy_state_files(state_path: Path) -> None:
    home = Path.home()
    legacy = home / ".local/state/dzgui"
    if state_path == legacy:
        # TODO: log this
        return
    for file in legacy.iterdir():
        shutil.copy(file, state_path / file.name)


def copy_ipdb(ips_path: Path) -> None:
    home = Path.home()
    legacy = home / LEGACY_IPS_PATH
    if ips_path == legacy:
        return
    if legacy.is_file() is False:
        return
    shutil.copy(legacy, ips_path)
