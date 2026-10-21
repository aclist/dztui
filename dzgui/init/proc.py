import psutil
import subprocess
import shutil
import logging

from dzgui.const.constants import (
    APP_NAME,
    STEAM_CMD,
    FLATPAK_APPID,
    FLATPAK_CMD,
    FLATPAK_RUN_CMD,
    FLATPAK_SANDBOX,
    FLATPAK_ROOT_PATH,
    FLATPAK_STEAM_PATH,
)

logger = logging.getLogger(APP_NAME)


def is_steam_running(cmd: str) -> bool:
    if cmd in (FLATPAK_RUN_CMD, FLATPAK_SANDBOX):
        return is_flatpak_steam_running()
    elif cmd == STEAM_CMD:
        return is_native_steam_running()
    else:
        raise TypeError("Not a valid Steam client selection")


def is_flatpak_steam_running() -> bool:
    if has_cmd(FLATPAK_CMD) is False:
        return False
    proc = subprocess.check_output(
        [FLATPAK_CMD, "ps", "--columns=application"], text=True
    )
    lines = proc.splitlines()
    if FLATPAK_APPID in lines:
        return True
    return False


def is_native_steam_running() -> bool:
    if has_cmd(STEAM_CMD) is False:
        return False
    procs = [p.cmdline() for p in psutil.process_iter(["pid", "name"]) if STEAM_CMD in p.info["name"]]
    steam_procs = [p for p in procs if not any(FLATPAK_ROOT_PATH in sub for sub in p)]
    return bool(steam_procs)


def has_cmd(cmd: str) -> bool:
    if shutil.which(cmd) is not None:
        return True
    return False


def path_to_steam_cmd(path: str) -> str:
    cmd = FLATPAK_RUN_CMD if FLATPAK_STEAM_PATH in path else STEAM_CMD
    return cmd
