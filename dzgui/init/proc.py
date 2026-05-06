import psutil
import sys

from dzgui.const.constants import DAYZ_BINARY, STEAM_CMD
from dzgui.views.dialogs.early_alert import EarlyAlertDialog
from dzgui.util.strings import init


# TODO: simplify
def is_dayz_running(dialog: bool = False) -> None:
    if dialog is False:
        return is_running(DAYZ_BINARY)
    if is_running(DAYZ_BINARY) is True:
        EarlyAlertDialog(init.is_dayz_running)
        sys.exit(1)


def is_steam_running(dialog: bool = False) -> None:
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
