import json
import logging
import os
import requests
import subprocess
from typing import Union
from warnings import deprecated

from shlex import shlex
from pathlib import Path

from dzgui.init.prereqs import has_steam_client
from dzgui.const.constants import (
    APPID_DAYZ,
    APP_NAME,
    DEBIAN_STEAM_PATH,
    DEFAULT_STEAM_PATH,
    FLATPAK_STEAM_PATH,
    UBUNTU_STEAM_PATH,
    REQUEST_TIMEOUT,
    VDF_PATH,
)
from dzgui.const.endpoints import SUB_ENDPOINT, STEAM_PUBLISHED_FILES, UNSUB_ENDPOINT
from dzgui.strings import wizard
from dzgui.util.bash import concat_bash_args


logger = logging.getLogger(APP_NAME)


def get_steam_paths() -> list[tuple[Path, str]]:
    paths = []
    if has_steam_client():
        HOME = Path.home()
        env = os.environ.get("XDG_DATA_HOME")
        if env is not None:
            XDG_DATA_HOME = env
        else:
            XDG_DATA_HOME = DEFAULT_STEAM_PATH

        DEFAULT_PATH = HOME.joinpath(XDG_DATA_HOME)
        FLATPAK_PATH = HOME.joinpath(FLATPAK_STEAM_PATH)
        UBUNTU_PATH = HOME.joinpath(UBUNTU_STEAM_PATH)
        DEBIAN_PATH = HOME.joinpath(DEBIAN_STEAM_PATH)

        human = {
            DEFAULT_PATH: wizard.desc_default_path,
            FLATPAK_PATH: wizard.desc_flatpak_path,
            UBUNTU_PATH: wizard.desc_ubuntu_path,
            DEBIAN_PATH: wizard.desc_debian_path,
        }

        for path in DEFAULT_PATH, FLATPAK_PATH, UBUNTU_PATH, DEBIAN_PATH:
            if path.joinpath(VDF_PATH).is_file():
                paths.append((path, human[path]))
    return paths


def concat_mods(mods: list[str]) -> str:
    # TODO: circular import workaround
    from dzgui.api.mods import _hash

    hashes = []
    for mod in mods:
        md5sum = _hash(mod)
        hashes.append(md5sum)
    return ";".join(hashes)


def get_local_signatures(version_file: Path) -> dict[str, int]:
    hashes: dict[str, int] = {}
    lines = version_file.read_text().splitlines()
    for line in lines:
        data = line.split(",")
        _id = data[0]
        mod_hash = int(data[1])
        hashes[_id] = mod_hash
    return hashes


def get_needs_update(
    version_file: Path, remote_hashes: list[tuple[str, str, int, int]]
) -> list[tuple[str, str, int, int]]:
    local_stamps = get_local_signatures(version_file)
    needs_update: list[tuple[str, str, int, int]] = []
    for title, _id, stamp, size in remote_hashes:
        if _id not in local_stamps:
            needs_update.append((title, _id, stamp, size))
        elif stamp != local_stamps[_id]:
            needs_update.append((title, _id, stamp, size))
        else:
            continue
    return needs_update


def get_remote_signatures(mods: list[str]) -> list[tuple[str, str, int, int]]:
    """
    Attempts to continue connecting even if signatures are empty
    """
    payload: dict[str, str | int] = {}
    payload["itemcount"] = len(mods)
    for i, mod in enumerate(mods):
        payload[f"publishedfileids[{i}]"] = mod
    try:
        r = requests.post(STEAM_PUBLISHED_FILES, payload)
    except Exception as e:
        logger.critical(e)
        return []
    if r.status_code != 200:
        return []

    hashes: list[tuple[str, str, int, int]] = []
    j = r.json()
    rows = j["response"]["publishedfiledetails"]
    for row in rows:
        title = str(row["title"])
        _id = str(row["publishedfileid"])
        time = int(row["time_updated"])
        size = int(row["file_size"])
        hashes.append((title, _id, time, size))
    return hashes


# TODO: set config to name=user, use official server and no mods,
# ensure that formatted string is identical to fixture with same hash
def connect(client: str, addr: str, appid: int, name: str, mods: list[str]) -> int:
    concat = concat_mods(mods)
    client_args = concat_bash_args(client)
    # TODO: test flatpak arg expansion
    params = [
        "-applaunch",
        str(appid),
        f"-connect={addr}",
        "-nolauncher",
        "-nosplash",
        "-skipintro",
        f"-name={name}",
        f"-mod={concat}",
    ]
    proc = subprocess.run([*client_args, *params])
    return proc.returncode


def load_to_menu(client: str, appid: int, name: str, mods: list[str]) -> int:
    """Loads to the menu screen with the selected mods; used for AFK/pre-joining"""
    concat = concat_mods(mods)
    client_args = concat_bash_args(client)
    params = [
        "-applaunch",
        str(appid),
        "-nolauncher",
        "-nosplash",
        "-skipintro",
        f"-name={name}",
        f"-mod={concat}",
    ]
    proc = subprocess.run([*client_args, *params])
    return proc.returncode


def launch_offline(
    client: str, appid: int, name: str, mods: list[str], mission: str
) -> int:
    """Launch offline with specific mods/missions"""
    symlinks = ";".join(mods)
    client_args = concat_bash_args(client)
    params = [
        "-applaunch",
        str(appid),
        "-nolauncher",
        "-nosplash",
        "-skipintro",
        f"-name={name}",
        f"-mod={symlinks}",
    ]
    if len(mission) > 0:
        arg = f"-mission={mission}"
        params.append(arg)
    proc = subprocess.run([*client_args, *params])
    return proc.returncode


def find_user_id(path: Path) -> str | None:
    resolved_path = path / "config" / "loginusers.vdf"
    try:
        vdf = vdf2json(resolved_path)
        j = json.loads(vdf)
        for user in j["users"]:
            if j["users"][user]["MostRecent"] == "1":
                return str(user)
        return None
    except Exception as e:
        logger.warn(e)
        return None


def vdf2json(path: Path) -> str:
    def _istr(indent: int, string: str) -> str:
        return (indent * "  ") + string

    jbuf = "{\n"
    indent = 1

    with open(path, "r") as f:
        st = f.read()
    lex = shlex(st)

    while True:
        tok = lex.get_token()
        if not tok:
            return jbuf + "}\n"
        if tok == "}":
            indent -= 1
            jbuf += _istr(indent, "}")
            ntok = lex.get_token()
            if ntok is not None:
                lex.push_token(ntok)
            if ntok and ntok != "}":
                jbuf += ","
            jbuf += "\n"
        else:
            ntok = lex.get_token()
            if ntok == "{":
                jbuf += _istr(indent, tok + ": {\n")
                indent += 1
            else:
                if ntok is not None:
                    jbuf += _istr(indent, tok + ": " + ntok)
                    ntok = lex.get_token()
                    if ntok is not None:
                        lex.push_token(ntok)
                    if ntok != "}":
                        jbuf += ","
                    jbuf += "\n"


def update_workshop(key: str, mod: int, endpoint: str) -> None:
    payload: dict[str, Union[int, str]] = {
        "publishedfileid": mod,
        "appid": APPID_DAYZ,
        "key": key,
        "list_type": 1,
        "notify_client": 1,
    }
    try:
        res = requests.post(endpoint, params=payload, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
    except Exception as e:
        logger.critical(e)


def subscribe(key: str, mod: int) -> None:
    update_workshop(key, mod, SUB_ENDPOINT)


def unsubscribe(key: str, mod: int) -> None:
    update_workshop(key, mod, UNSUB_ENDPOINT)


def gen_shortcut() -> None:
    # TODO:
    """
    during setup, prompt user to select matching user id from loginusers
    show user account name, select outer steam id
    steam/userdata/<steamid_32>/config/shortcuts.vdf
    """
    # STEAMID_MAGIC = 76561197960265728
    # STEAMID_64 - STEAMID_MAGIC = STEAMID32
    # or get right-most 32 bits
    # STEAMID_64 & 0xFFFFFFFF
    pass


@deprecated("Use subscribe()")
def enqueue_mod(client: str, mod: str, appid: int) -> None:
    client_args = concat_bash_args(client)
    subprocess.Popen([*client_args, "+workshop_download_item", str(appid), mod])
