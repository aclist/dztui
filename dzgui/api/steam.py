import logging
import os
import psutil
import requests
import subprocess
import vdf  # type: ignore

from pathlib import Path
from typing import Any, Union
from warnings import deprecated

from dzgui.api.acf import ACF
from dzgui.init.prereqs import has_steam_client
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APP_NAME,
    DAYZ_BINARY,
    DEBIAN_STEAM_PATH,
    DEFAULT_STEAM_PATH,
    FLATPAK_STEAM_PATH,
    LIBRARYFOLDERS_PATH,
    UBUNTU_STEAM_PATH,
    REQUEST_TIMEOUT,
    VDF_PATH,
)
from dzgui.const.endpoints import (
    APP_DETAILS,
    SUB_ENDPOINT,
    STEAM_PUBLISHED_FILES,
    UNSUB_ENDPOINT,
)
from dzgui.strings import wizard
from dzgui.util.bash import concat_bash_args

logger = logging.getLogger(APP_NAME)


class AppNotInstalledError(Exception):
    """App not present in user's libraryfolders"""

    pass


class AppMovedError(Exception):
    """VDF points to a nonexistent location on disk"""

    pass


class VDFLoadError(Exception):
    """Malformed VDF or JSON conversion"""

    pass


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
        # NOTE: not a valid published file
        if row["result"] == 9:
            continue
        title = str(row["title"])
        _id = str(row["publishedfileid"])
        time = int(row["time_updated"])
        size = int(row["file_size"])
        hashes.append((title, _id, time, size))
    return hashes


def connect_debug(client: str, addr: str, appid: int, name: str, mods: list[str]) -> str:
    concat = concat_mods(mods)
    client_args = concat_bash_args(client)
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
    client_args.extend(params)
    return " ".join(client_args)

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


def find_loginusers(path: Path) -> Path:
    return path / "config" / "loginusers.vdf"


def find_user_id(path: Path) -> str | None:
    resolved_path = find_loginusers(path)
    try:
        with open(resolved_path, "r") as f:
            v = vdf.load(f)
            # NOTE: beta client
            # /package/beta
            if len(v["users"]) == 1:
                return str(list(v["users"].keys())[0])
            for user in v["users"]:
                if v["users"][user]["MostRecent"] == "1":
                    return str(user)
            return None
    except Exception as e:
        logger.debug(e)
        return None


def find_user_id_32(path: Path) -> int:
    uid = find_user_id(path)
    if uid is None:
        raise ValueError("Failed to parse a valid Steam32 ID")
    return int(uid) & 0xFFFFFFFF


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


@deprecated("Use subscribe()")
def enqueue_mod(client: str, mod: str, appid: int) -> None:
    client_args = concat_bash_args(client)
    subprocess.Popen([*client_args, "+workshop_download_item", str(appid), mod])


@deprecated("Cf. https://github.com/ValveSoftware/steam-for-linux/issues/9672")
def get_registry() -> Any | None:
    home = os.getenv("HOME")
    try:
        with open(f"{home}/.steam/registry.vdf") as f:
            registry = vdf.load(f)
        return registry
    except Exception as e:
        logger.critical(e)
        return None


def _is_dayz_running() -> bool:
    registry = get_registry()
    if registry is None:
        return False
    apps = registry["Registry"]["HKCU"]["Software"]["Valve"]["Steam"]["apps"].items()
    for app in apps:
        k, v = app
        if k in (APPID_DAYZ, APPID_DAYZ_EXP):
            try:
                state = v["Running"]
                # NOTE: 0 denotes False
                return bool(int(state))
            except Exception as e:
                logger.critical(e)
                return False
    return False


def _get_running_app() -> int | None:
    registry = get_registry()
    if registry is None:
        return None
    try:
        return int(
            registry["Registry"]["HKCU"]["Software"]["Valve"]["Steam"]["RunningAppID"]
        )
    except Exception:
        return None


def get_running_app() -> int | None:
    PROC_NAME = "steam"
    SUBPROC_NAME = "reaper"
    FLAG = "AppId"
    # NOTE: may cause conflicts if multiple apps are running
    try:
        for proc in psutil.process_iter():
            if proc.name() == PROC_NAME:
                subprocs = proc.children()
                filtered = (proc for proc in subprocs if proc.name() == SUBPROC_NAME)
                try:
                    proc = next(filtered)
                except StopIteration:
                    return None
                args = proc.cmdline()
                appid = (row for row in args if FLAG in row)
                try:
                    return int(next(appid).split("=")[1])
                except StopIteration:
                    return None
    except Exception as e:
        logger.debug(e)
    return None


def get_app_allows_downloads(path: Path, appid: int) -> bool:
    try:
        root_path = get_app_path(path, appid)
        acf = root_path.joinpath(f"steamapps/appmanifest_{appid}.acf")
        flag = ACF(acf).get_allows_downloads()
    except AppNotInstalledError:
        flag = 0
    match flag:
        # NOTE: adheres to global client setting
        case 0:
            return get_client_allows_downloads(path)
        # NOTE: always allow
        case 1:
            return True
        # NOTE: never allow
        case 2:
            return False
        # NOTE: no other known values at this time, fallback (assume permits)
        case _:
            return True


def get_config(path: Path) -> Path:
    return path.joinpath("config/config.vdf")


def get_client_allows_downloads(path: Path) -> bool:
    config = get_config(path)
    try:
        with open(config) as f:
            settings = vdf.load(f)
            # NOTE: "1" denotes "allow"
            allow = bool(
                int(
                    settings["InstallConfigStore"]["Software"]["Valve"]["Steam"][
                        "AllowDownloadsDuringGameplay"
                    ]
                )
            )
            return allow
    except Exception as e:
        logger.critical(e)
        return True


def is_dayz_running() -> bool:
    """Subprocesses spawned from Steam will not show up in regular process tree"""
    procs = []
    substring = DAYZ_BINARY
    for proc in psutil.process_iter():
        try:
            procs.append(proc.cmdline())
        except Exception as e:
            logger.warning(e)
            continue
    return any(substring in item for sublist in procs for item in sublist)


def get_app_path(folders_path: Path, appid: int) -> Path:
    app_path = None

    try:
        with open(folders_path / LIBRARYFOLDERS_PATH) as f:
            folders = vdf.load(f)
    except Exception:
        raise VDFLoadError("Failed to parse libraryfolders")

    for obj in folders["libraryfolders"]:
        if str(appid) in folders["libraryfolders"][obj]["apps"]:
            app_path = folders["libraryfolders"][obj]["path"]
            if Path(app_path).exists():
                break

    if app_path is None:
        raise AppNotInstalledError(
            f"Failed to find a libraryfolder for the appid {appid}"
        )
    if Path(app_path).exists() is False:
        raise AppMovedError(
            f"The location '{app_path}' pointed to by '{appid}' no longer exists and may have been changed on the disk."
        )

    return Path(app_path)


def get_app_name(appid: int) -> str | None:
    payload = {"appids": [appid]}
    res = requests.get(APP_DETAILS, params=payload)
    if res.status_code != 200:
        return None
    try:
        return str(res.json()[str(appid)]["data"]["name"])
    except Exception as e:
        logger.debug(e)
        return None
