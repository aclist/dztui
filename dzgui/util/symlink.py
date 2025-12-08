import hashlib
import logging
from pathlib import Path

from dzgui.api.mods import get_local_mod_path, get_local_mod_ids, _hash
from dzgui.const.constants import APPID_DAYZ, APPID_DAYZ_EXP
from dzgui.const.enum import Preferences
from dzgui.config.query import lookup

import dzgui.api.pefile as PeFile

logger = logging.getLogger(__name__)

def rebuild_symlinks(config: Path) -> None:
    path = lookup(config, Preferences.DEFAULT)
    steam_path = Path(path)

    dayz_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ)
    for file in dayz_path.iterdir():
        if file.is_symlink():
            file.unlink()
    workshop = get_local_mod_path(steam_path)
    for uid in get_local_mod_ids(steam_path):
        uid = str(uid)
        md5sum = _hash(str(uid))
        Path(dayz_path / md5sum).symlink_to(workshop / uid)


def clone_symlinks(config: Path) -> None:
    """
    Used after any symlink operation
    """
    path = lookup(config, Preferences.DEFAULT)
    steam_path = Path(path)
    try:
        dayz_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ)
        exp_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ_EXP)
    except Exception as e:
        logger.critical(e)
        return

    # TODO: test these two operations
    for file in exp_path.iterdir():
        if file.is_symlink():
            file.unlink()

    for file in dayz_path.iterdir():
        if file.is_symlink():
            uid = file.name
            Path(exp_path / uid).symlink_to(dayz_path / uid)
