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
)

logger = logging.getLogger(APP_NAME)


def is_steam_running(cmd: str) -> bool:
    if cmd == STEAM_CMD:
        if has_cmd(STEAM_CMD) is False:
            return False
        return is_running(STEAM_CMD)
    elif cmd == FLATPAK_RUN_CMD or FLATPAK_SANDBOX:
        return is_flatpak_steam_running()
    else:
        raise TypeError("Not a valid Steam client selection")


# CHORE: test alternate clients
# TODO: has_flatpak_steam
def is_flatpak_steam_running() -> bool:
    if has_cmd(FLATPAK_CMD) is False:
        return False
    proc = subprocess.check_output([FLATPAK_CMD, "ps"], text=True)
    lines = proc.splitlines()
    if FLATPAK_APPID in lines:
        return True
    return False


def is_running(proc: str) -> bool:
    for process in psutil.process_iter(["pid", "name"]):
        if process.info["name"] == proc:
            return True
    return False


def has_cmd(cmd: str) -> bool:
    if shutil.which(cmd) is not None:
        return True
    return False
