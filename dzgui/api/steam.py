import json
import logging
import requests
import subprocess

from shlex import shlex
from pathlib import Path

from dzgui.const.constants import APP_NAME
from dzgui.const.endpoints import STEAM_PUBLISHED_FILES


logger = logging.getLogger(APP_NAME)


def concat_mods(mods: list[str]) -> str:
    from dzgui.util.symlink import _hash

    hashes = []
    for mod in mods:
        md5sum = _hash(mod)
        hashes.append(md5sum)
    return ";".join(hashes)


def get_local_signatures(version_file: Path) -> dict[str, int]:
    hashes: dict[str, int] = {}
    lines = version_file.read_text().splitlines()
    for line in lines:
        line = line.split(",")
        _id = line[0]
        _hash = int(line[1])
        hashes[_id] = _hash
    return hashes


def enqueue_mod(mod: str, appid: int) -> None:
    args = [
        "steam",
        f"steam://url/CommunityFilePage/{mod}+workshop_download_item",
        str(appid),
        mod,
    ]
    subprocess.Popen(["/usr/bin/env", "bash", *args])


def get_needs_update(
    version_file: Path, remote_hashes: list[tuple[str, str, int, int]]
) -> list[tuple[str, str, int, int]]:
    local_hashes = get_local_signatures(version_file)
    needs_update: list[tuple[str, str]] = []
    for title, _id, _hash, size in remote_hashes:
        if _id not in local_hashes:
            needs_update.append((title, _id, _hash, size))
        elif _hash != local_hashes[_id]:
            needs_update.append((title, _id, _hash, size))
        else:
            continue
    return needs_update


def get_remote_signatures(mods: list[str]) -> list[tuple[str, str, int, int]]:
    """
    Attempts to continue connecting even if signatures are empty
    """
    payload: dict[str, str] = {}
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

    hashes: list[tuple[str, int, int]] = []
    j = r.json()
    rows = j["response"]["publishedfiledetails"]
    for row in rows:
        title = row["title"]
        _id = row["publishedfileid"]
        time = row["time_updated"]
        size = int(row["file_size"])
        hashes.append((title, _id, time, size))
    return hashes


# TODO:: set config to name=user, use official server and no mods,
# ensure that formatted string is identical to fixture with same hash
def connect(addr: str, appid: int, name: str, mods: list[str]) -> None:
    concat = concat_mods(mods)
    params = [
        "steam",
        "-applaunch",
        appid,
        f"-connect={addr}",
        "-nolauncher",
        "-nosplash",
        "-skipintro",
        f"-name={name}",
        f"-mod={concat}",
    ]
    proc = subprocess.Popen([*params])
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
    def _istr(indent: int, string: str):
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
                jbuf += _istr(indent, tok + ": " + ntok)
                ntok = lex.get_token()
                lex.push_token(ntok)
                if ntok != "}":
                    jbuf += ","
                jbuf += "\n"


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
