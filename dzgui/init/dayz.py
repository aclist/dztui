import logging

from pathlib import Path

from dzgui.config.query import lookup
from dzgui.const.constants import APPID_DAYZ, APP_NAME, LIBRARYFOLDERS_PATH
from dzgui.const.enum import Preferences

import dzgui.api.pefile as PeFile

logger = logging.getLogger(APP_NAME)


def is_dayz_installed(config: Path) -> None:
    try:
        path = lookup(config, Preferences.DEFAULT)
        PeFile.get_app_path(Path(path) / LIBRARYFOLDERS_PATH, APPID_DAYZ)
    except Exception as e:
        logger.critical(e)
        raise e
