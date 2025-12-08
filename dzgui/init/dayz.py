import logging
import sys

from pathlib import Path

from dzgui.config.query import lookup
from dzgui.const.constants import LIBRARYFOLDERS_PATH, APPID_DAYZ
from dzgui.const.enum import Preferences
from dzgui.views.dialogs.early_alert import EarlyAlertDialog

import dzgui.api.pefile as PeFile

logger = logging.getLogger(__name__)

def is_dayz_installed(config: Path) -> None:
    try:
        path = lookup(config, Preferences.DEFAULT)
        PeFile.get_app_path(Path(path) / LIBRARYFOLDERS_PATH, APPID_DAYZ)
    except Exception as e:
        logger.critical(e)
        EarlyAlertDialog(e)
        sys.exit(1)
