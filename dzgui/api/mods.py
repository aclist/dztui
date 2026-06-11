import hashlib
import logging
import re

from concurrent.futures import wait
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import dzgui.api.pefile as PeFile
from dzgui.api.servers import get_rules, fqip_to_record
from dzgui.const.constants import (
    APP_NAME,
    APPID_DAYZ,
    LIBRARYFOLDERS_PATH,
    WORKSHOP_PATH,
)

from dzgui.config.query import lookup
from dzgui.const.enum import Preferences

from typing import Any

logger = logging.getLogger(APP_NAME)


@dataclass
class ModMeta:
    protocol: str
    published_id: str
    name: str
    timestamp: str


def get_local_mod_ids(steam_path: Path) -> list[int]:
    workshop_path = get_local_mod_path(steam_path)
    mods = get_local_mods(workshop_path)
    return [int(mod.name) for mod in mods]


def get_local_mod_path(steam_path: Path) -> Path:
    p = PeFile.get_app_path(steam_path / Path(LIBRARYFOLDERS_PATH), APPID_DAYZ)
    workshop_path = p / WORKSHOP_PATH
    return workshop_path


def get_local_mods(workshop_path: Path) -> list[Path]:
    mods = [file for file in workshop_path.iterdir() if file.is_dir()]
    return mods

def is_mission(path: Path) -> bool:
    # TODO: parse integrity of other files
    file = path / "init.c"
    return file.exists()

def tokenize(file: str) -> dict[Any] | None:
    delimiter=r"\s*=\s*"
    modmeta = {}
    try:
        with open(file, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip().rstrip(";")
                if not line:
                    continue
                els = re.split(delimiter, line, maxsplit=1)
                if len(els) == 2:
                    key, value = els
                    print(value)
                    modmeta[key.strip()] = value.strip('"')
        return modmeta
    except Exception as e:
        logger.critical(e)
        return None

def get_mod_size(path: Path) -> float:
    s = 0
    for f in path.rglob("*"):
        s += f.stat().st_size
    size = round(s / (1024**2), 3)
    return size


def get_custom_mods(path: Path) -> list[Any]:
    mods = get_local_mods(path)
    # TODO: error handling
    return parse_mods(mods)


def parse_mods(mods: list[Path]) -> list[Any]:
    clean = []
    for mod in mods:
        mod_dir = mod.name
        symlink = _hash(mod_dir)
        meta = tokenize(mod)
        if meta is None:
            continue
        size = get_mod_size(mod)
        # NOTE: final col is cell renderer highlight toggle
        clean.append([meta["name"], symlink, mod_dir, size, False])
    clean.sort(key=lambda row: str(row[0]).casefold())
    return clean


def get_delimited_mods(steam_path: Path) -> list[Any]:
    workshop_path = get_local_mod_path(steam_path)
    mods = get_local_mods(workshop_path)
    return parse_mods(mods)


def get_missing_mods(local: list, remote: list) -> list:
    return [mod for mod in remote if mod not in local]


def _hash(uid: str, use_custom: bool = False) -> str:
    md5 = hashlib.md5()
    md5.update(uid.encode("ascii"))
    prefix = "@C" if use_custom else "@"
    return prefix + md5.hexdigest()[:8]


def remove_stale_signatures(config: Path, versions: Path) -> None:
    if versions.is_file() is False:
        logger.warning("Creating new version signatures file")
        versions.touch()
        return
    path = lookup(config, Preferences.DEFAULT)
    steam_path = Path(path)
    ids = get_local_mod_ids(steam_path)
    with open(versions, "r") as f:
        lines = f.readlines()
    for line in lines:
        uid = int(line.split(",")[0])
        if uid not in ids:
            lines.remove(line)
    with open(versions, "w") as f:
        for line in lines:
            f.write(line)


def find_stale_mods(config: Path) -> list[int]:
    def push_record(rec: str) -> list:
        record = fqip_to_record(rec)
        if record is None:
            return []
        try:
            mods = get_rules(record)
        except Exception:
            return []
        return [mod.workshop_id for mod in mods]

    steam = lookup(config, Preferences.DEFAULT)
    steam_path = Path(steam)

    local = get_local_mod_ids(steam_path)
    records = lookup(config, Preferences.IP_LIST)

    remote_mods = []

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(push_record, record) for record in records]
        wait(futures)
        for future in futures:
            res = future.result()
            remote_mods.extend(res)

    unique_mods = set(remote_mods)
    stale = [mod for mod in local if mod not in unique_mods]
    return stale


def get_mod_dir_size(path: Path) -> int:
    """
    This is not a guarantee of parity, as user may adjusted contents of local mods,
    so upstream epoch time is still used
    """
    size = 0
    for i in Path(path).iterdir():
        if i.is_file():
            size += i.stat().st_size
        elif i.is_dir():
            size += get_mod_dir_size(i)
    return size


def version_file_to_dict(file: Path) -> dict[str, str]:
    versions = file.read_text().splitlines()
    d: dict[str, str] = {}
    for version in versions:
        line = version.split(",")
        mod = line[0]
        stamp = line[1]
        d[mod] = stamp
    return d


def update_signatures(
    mods: list[tuple[str, str, int, int]], version_file: Path
) -> None:
    d = version_file_to_dict(version_file)
    for _title, mod, stamp, size in mods:
        d[mod] = str(stamp)
    versions: list[str] = []
    for k, v in d.items():
        row = ",".join([k, v])
        versions.append(row)

    with open(version_file, "w") as f:
        for version in versions:
            f.write(f"{version}\n")
