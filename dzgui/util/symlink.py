import logging
from pathlib import Path

from dzgui.api.mods import get_local_mod_path, get_local_mod_ids, _hash
from dzgui.const.constants import APPID_DAYZ, APPID_DAYZ_EXP, APP_NAME
from dzgui.const.enum import Preferences
from dzgui.config.query import lookup

import dzgui.api.pefile as PeFile

logger = logging.getLogger(APP_NAME)


def rebuild_symlinks(config: Path) -> None:
    # TODO: pass direct path as argument
    path = lookup(config, Preferences.DEFAULT)
    steam_path = Path(path)
    dayz_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ)
    # NOTE: unlink stale symlinks
    # TODO: expunge ephemeral (@C) links (possibility of name collisions)
    # if str(file)[:2] == "@C": file.unlink()
    for file in dayz_path.iterdir():
        if file.is_symlink() and file.exists() is False:
            file.unlink()
    workshop = get_local_mod_path(steam_path)
    # NOTE: create symlinks for missing mods
    for mod_id in get_local_mod_ids(steam_path):
        uid = str(mod_id)
        md5sum = _hash(str(uid))
        source = Path(dayz_path / md5sum)
        if source.exists() is False:
            source.symlink_to(workshop / uid)
    clone_symlinks(steam_path)


def create_custom_symlinks(
    steam_path: Path, custom_dir: Path, uids: list[str]
) -> list[str]:
    dayz_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ)
    links = []
    for uid in uids:
        md5sum = _hash(uid, use_custom=True)
        source = dayz_path.joinpath(md5sum)
        target = custom_dir.joinpath(uid)
        links.append(md5sum)
        if source.exists() is False:
            source.symlink_to(target)
    clone_symlinks(steam_path)
    return links


def clone_symlinks(steam_path: Path) -> None:
    """
    Shares symlinks between builds. Used after any symlink operation
    """
    try:
        dayz_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ)
        exp_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ_EXP)
    except Exception as e:
        logger.warning(e)
        return

    # TODO: test these two operations
    # use less time intensive logic like the above
    try:
        for file in exp_path.iterdir():
            if file.is_symlink():
                file.unlink()

        for file in dayz_path.iterdir():
            if file.is_symlink():
                uid = file.name
                Path(exp_path / uid).symlink_to(dayz_path / uid)
    except Exception as e:
        logger.critical(e)
