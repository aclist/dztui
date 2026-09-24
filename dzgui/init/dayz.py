import logging

from pathlib import Path

from dzgui.api.steam import get_app_path
from dzgui.config.query import lookup
from dzgui.const.constants import APPID_DAYZ, APP_NAME, APPNAME_DAYZ
from dzgui.const.enum import Preferences

from dzgui.strings.preconnect import resync


logger = logging.getLogger(APP_NAME)


class VDFSyncError(Exception):
    pass


def is_dayz_installed(config: Path) -> None:
    try:
        path = lookup(config, Preferences.DEFAULT)
        get_app_path(Path(path), APPID_DAYZ)
    except Exception as e:
        logger.critical(e)
        msg = resync.format(APPNAME_DAYZ)
        raise VDFSyncError(msg)
