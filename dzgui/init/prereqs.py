import logging
import shutil
import subprocess

from dzgui.const.constants import STEAM_CMD, FLATPAK_APPID, FLATPAK_CMD

logger = logging.getLogger(__name__)


def has_steam_client() -> bool:
    if shutil.which(STEAM_CMD):
        return True
    if not shutil.which(FLATPAK_CMD):
        return False
    try:
        res = subprocess.run(
            [FLATPAK_CMD, "list"],
            capture_output=True,
            text=True,
            check=True
        )
        if FLATPAK_APPID in res.stdout:
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        logger.critical(e)
        return False
