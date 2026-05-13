import psutil
import subprocess
import shutil

from dzgui.const.constants import (
    DAYZ_BINARY,
    STEAM_CMD,
    FLATPAK_APPID,
    FLATPAK_CMD,
    FLATPAK_RUN_CMD,
    FLATPAK_SANDBOX,
)


# TODO: move to util.proc
def is_dayz_running() -> bool:
    """Subprocesses spawned from Steam will not show up in regular process tree"""
    procs = []
    substring = DAYZ_BINARY
    for proc in psutil.process_iter():
        try:
            procs.append(proc.cmdline())
        except Exception:
            continue
    return any(substring in item for sublist in procs for item in sublist)


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


def foreground(cmd: str, pid: int) -> None:
    if cmd == "wmctrl":
        proc = subprocess.run(["wmctrl", "-ilp"], capture_output=True, text=True)
        lines = proc.stdout.splitlines()
        for line in lines:
            els = line.split(" ")
            if str(pid) in els:
                wid = els[0]
                break
        subprocess.run(["wmctrl", "-ia", wid])
    elif cmd == "xdotool":
        args = [cmd, "search", "--pid", str(pid)]
        proc = subprocess.run([*args], capture_output=True, text=True)
        lines = proc.stdout.splitlines()
        ## NOTE: some forked subprocesses may fail, so skip over them
        for line in lines:
            subprocess.run(
                ["xdotool", "windowactivate", line], stderr=subprocess.DEVNULL
            )
