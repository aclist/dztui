import dayzquery
import hashlib
import logging
import re
import shlex

from dataclasses import dataclass
from pathlib import Path

import dzgui.api.pefile as PeFile
from dzgui.api.servers import Record, get_rules
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    LIBRARYFOLDERS_PATH,
    WORKSHOP_PATH,
)

from dzgui.util.strings import checkmark
from dzgui.config.query import lookup
from dzgui.const.enum import Preferences

from typing import Any

logger = logging.getLogger(__name__)

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
    p = PeFile.get_app_path(steam_path / LIBRARYFOLDERS_PATH, APPID_DAYZ)
    workshop_path = p / WORKSHOP_PATH
    return workshop_path

def get_local_mods(workshop_path: Path) -> list[Path]:
    mods = [file for file in workshop_path.iterdir() if file.is_dir()]
    return mods


# TODO: TEST: mock bad meta files with fixtures and remove them
def parse_meta(file: Path) -> ModMeta:
    mod = file / "meta.cpp"
    if mod.exists() is False:
        return None
    with open(file / "meta.cpp", "r") as f:
        st = f.read()
        lex = shlex.shlex(st)
        lex.whitespace += "=;"
        v = []
        while True:
            tok = lex.get_token()
            if not tok:
                break
            if tok == "protocol" or tok == "publishedid":
                ntok = lex.get_token()
            elif tok == "timestamp":
                # some malformed .NET tick conversions result in numbers < 0
                ntok = lex.get_token()
                if ntok == "-":
                    ntok += str(lex.get_token())
            elif tok == "name":
                ntok = lex.get_token().split('"')[1]
            v.append(ntok)
        meta = ModMeta(*v)
        return meta


def get_mod_size(path: Path) -> float:
    s = 0
    for f in path.rglob("*"):
        s += f.stat().st_size
    size = round(s / (1024 * 1024), 3)
    return size


def get_delimited_mods(steam_path: Path) -> list[Any]:
    workshop_path = get_local_mod_path(steam_path)
    mods = get_local_mods(workshop_path)
    clean = []
    for mod in mods:
        mod_dir = mod.name
        symlink = _hash(mod_dir)
        # FIXME: malformed .cpp files could break this
        # mention that mods may be downloading
        meta = parse_meta(mod)
        if meta is None:
            continue
        size = get_mod_size(mod)
        clean.append([meta.name, symlink, mod_dir, size])
    clean.sort(key=lambda row: row[0])
    return clean


def get_missing_mods(local: list, remote: list) -> list:
    return [mod for mod in remote if mod not in local]


def get_server_modlist(server: Record, steam: Path) -> list:
    try:
        rules = dayzquery.dayz_rules((server.ip, server.qport))
    except Exception as e:
        raise e
    remote_mods = [[mod.name, mod.workshop_id] for mod in rules.mods]
    remote_mods.sort(key=lambda row: row[0])
    local_mods = get_local_mod_ids(steam)
    for mod in remote_mods:
        if mod[1] in local_mods:
            mod.append(checkmark)
        else:
            mod.append("")
    return remote_mods


def _hash(uid: str) -> str:
    md5 = hashlib.md5()
    md5.update(uid.encode("ascii"))
    return "@" + md5.hexdigest()[:8]


def remove_stale_signatures(config: Path, versions: Path) -> None:
    if versions.is_file() is False:
        logger.warning("No mod signatures file found")
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
    steam = lookup(config, Preferences.DEFAULT)
    steam_path = Path(steam)

    local = get_local_mod_ids(steam_path)
    servers = lookup(config, Preferences.IP_LIST)

    all_mods = []
    for server in servers:
        split = server.split(":")
        ip = split[0]
        gport = split[1]
        qport = split[2]

        mods = get_rules(ip, qport)
        all_mods += mods

    stale = []
    for mod in local:
        if mod not in all_mods:
            stale.append(mod)
    return stale
