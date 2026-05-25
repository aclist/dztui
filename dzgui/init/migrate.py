import shutil

from pathlib import Path
from dzgui.const.constants import LEGACY_CONFIG_PATH, LEGACY_COLS_PATH, LEGACY_IPS_PATH
from dzgui.config.convert import rc2json
from dzgui.util._json import read_json, write_json


def migrate_legacy_conf(config: Path) -> None:
    old_conf = Path.home() / LEGACY_CONFIG_PATH
    j = rc2json(old_conf)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(j)


def has_new_config(config: Path) -> bool:
    return config.exists()


def migrate_cols_file(res: Path) -> None:
    # NOTE: filename "dzg.columns.json" is API 7 spec
    old_res = Path.home() / LEGACY_COLS_PATH
    if old_res.is_file():
        j = read_json(old_res)
        cols = j["cols"]
        # NOTE: implies prior conversion
        if "View" in cols:
            return
        # NOTE: user may not have changed these widths in API 6
        try:
            cols["View"] = cols.pop("Perspective")
            cols["Max"] = cols.pop("Maximum")
        except Exception:
            pass
        write_json(j, res)


def copy_state_files(state_path: Path) -> None:
    home = Path.home()
    legacy = home / ".local/state/dzgui"
    to_copy = [
        "dzg.res.json",
        "dzg.notes.json",
        "dzg.history",
        "dzg.versions",
        "ips.csv",
        ".month",
    ]
    if state_path == legacy:
        # TODO: log this
        return
    for file in legacy.iterdir():
        if file.name in to_copy:
            shutil.copy(file, state_path / file.name)


def copy_ipdb(ips_path: Path) -> None:
    home = Path.home()
    legacy = home / LEGACY_IPS_PATH
    if ips_path == legacy:
        return
    if legacy.is_file() is False:
        return
    # TODO: ensure that month file is copied
    shutil.copy(legacy, ips_path)
