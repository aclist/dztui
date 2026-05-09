import psutil
import subprocess
import shutil
import sys

from dzgui.const.constants import (
    DAYZ_BINARY,
    STEAM_CMD,
    FLATPAK_APPID,
    FLATPAK_RUN_CMD,
    FLATPAK_SANDBOX,
)
from dzgui.views.dialogs.early_alert import EarlyAlertDialog
from dzgui.util.strings import init

# TODO: move to util.proc
def is_dayz_running() -> bool:
    return is_running(DAYZ_BINARY)


def is_steam_running(cmd: str) -> bool:
    if cmd == STEAM_CMD:
        if has_cmd(STEAM_CMD) is False:
            return False
        return is_running(STEAM_CMD)
    elif cmd == FLATPAK_RUN_CMD or FLATPAK_SANDBOX:
        return is_flatpak_steam_running()
    else:
        raise TypeError("Not a valid Steam client selection")


def is_flatpak_steam_running() -> bool:
    if has_cmd(FLATPAK_CMD) is False:
        return False
    proc = subprocess.check_output([FLATPAK_CMD, "ps"], capture_output=True, text=True)
    lines = proc.stdout.splitlines()
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


def foreground(cmd: str, pid: int) -> None:
    if cmd == "wmctrl":
        proc = subprocess.check_output(
            ["wmctrl", "-ilp"], capture_output=True, text=True
        )
        lines = proc.splitlines()
        for line in lines:
            els = line.split(" ")
            if str(pid) in els:
                wid = els[0]
                break
        subprocess.run(["wmctrl", "-ia", wid])
    elif cmd == "xdotool":
        args = [cmd, "search", "--pid", str(pid)]
        proc = subprocess.check_output([*args], stderr=subprocess.DEVNULL)
        lines = proc.splitlines()
        ## NOTE: some forked subprocesses may fail, so skip over them
        for line in lines:
            subprocess.run(
                ["xdotool", "windowactivate", line], stderr=subprocess.DEVNULL
            )
