import logging
import shutil
import subprocess

from dzgui.const.constants import APP_NAME, FLATPAK_APPID, FLATPAK_CMD, STEAM_CMD
from dzgui.init.proc import is_sandboxed

logger = logging.getLogger(APP_NAME)


def has_flatpak_client() -> bool:
    if is_sandboxed:
        return True
    try:
        res = subprocess.run(
            [FLATPAK_CMD, "list", "--columns=application"],
            capture_output=True,
            text=True,
            check=True,
        )
        if FLATPAK_APPID in res.stdout:
            return True
        else:
            return False
    except Exception as e:
        logger.critical(e)
        return False


def has_steam_client() -> bool:
    if shutil.which(STEAM_CMD):
        return True
    return False


def has_any_client() -> bool:
    if shutil.which(STEAM_CMD):
        return True
    if not shutil.which(FLATPAK_CMD):
        return False
    return has_flatpak_client()
