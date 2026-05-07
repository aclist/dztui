import psutil
import subprocess
import shutil
import sys

from dzgui.const.constants import DAYZ_BINARY, STEAM_CMD
from dzgui.views.dialogs.early_alert import EarlyAlertDialog
from dzgui.util.strings import init

# TODO: move to util.proc


# TODO: simplify
def is_dayz_running(dialog: bool = False) -> bool | None:
    if dialog is False:
        return is_running(DAYZ_BINARY)
    if is_running(DAYZ_BINARY) is True:
        EarlyAlertDialog(init.is_dayz_running)
        sys.exit(1)


def is_steam_running(dialog: bool = False) -> bool | None:
    # TODO: check proc name of flatpak steam
    if dialog is False:
        return is_running(STEAM_CMD)
    if is_running(STEAM_CMD) is False:
        EarlyAlertDialog(init.is_steam_running)
        sys.exit(1)


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
        # TODO: convert wid from hexadecimal
        args = [cmd, "-a", "DZGUI"]
    elif cmd == "xdotool":
        args = [cmd, "search", "--onlyvisible", "--name", "DZGUI", "windowactivate"]
    subprocess.Popen([*args])
