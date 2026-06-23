import logging
import os
from typing import TYPE_CHECKING


from dzgui.const.constants import APP_NAME
from dzgui.const.enum import Preferences
from dzgui.config.query import lookup
from dzgui.config.userprefs import UserPrefs
from dzgui.config.xdg import get_xdg_paths, parse_filepaths
from dzgui.init.migrate import (
    has_new_config,
    copy_state_files,
    migrate_cols_file,
)
from dzgui.init.prereqs import has_steam_client
from dzgui.strings import boot

# from dzgui.util.map_count import get_map_count
from dzgui.util.deck import is_steam_deck, is_game_mode
from dzgui.util.localize import set_locale
from dzgui.util.strings import init

from dzgui.views.base import App
from dzgui.views.dialogs.boot import BootWindow
from dzgui.views.dialogs.early_alert import EarlyAlertDialog
from dzgui.views.dialogs.wizard import SetupWizard

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(APP_NAME)

# TODO: profile load time
def make_parents(path: "Path") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def setup_logger(log_path: "Path") -> None:
    _format = (
        "%(asctime)s␞%(levelname)s␞%(filename)s::%(funcName)s::%(lineno)s␞%(message)s"
    )
    fh = logging.FileHandler(log_path)
    formatter = logging.Formatter(_format)
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)

def load_gui(version: str, is_debug: bool) -> None:
    set_locale()
    # NOTE: consider aborting this check if steam deck
    xdg_paths = get_xdg_paths()
    XDG = parse_filepaths(xdg_paths)

    if XDG.resolution.parent.is_dir() is False:
        make_parents(XDG.resolution)

    if XDG.debug.is_file() is False:
        make_parents(XDG.debug)

    _is_steam_deck = is_steam_deck()
    _is_game_mode = is_game_mode() if _is_steam_deck else False
    if _is_game_mode:
        # NOTE: this may no longer be necessary on newer versions of SteamOS
        del os.environ["GTK_IM_MODULE"]

    if has_new_config(XDG.config) is False:
        migrate_cols_file(XDG.columns)
        copy_state_files(xdg_paths["XDG_STATE_HOME"])
        # TODO: add logging inside wizard
        SetupWizard(_is_steam_deck, XDG.config)

    # NOTE: implies that setup wizard failed or was closed
    if has_new_config(XDG.config) is False:
        return

    setup_logger(XDG.debug)
    with open(XDG.debug, "w") as f:
        f.truncate(0)

    if _is_steam_deck is False:
        # TODO: sudo escalation dialog
        # count = get_map_count()
        # TODO: move into module
        if has_steam_client() is False:
            EarlyAlertDialog(init.requires_steam)

    bootwin = BootWindow(XDG, version)
    local_coords, latest_release = bootwin.get_results()

    use_miles = lookup(XDG.config, Preferences.DIST)
    prefs = UserPrefs(
        is_steam_deck=_is_steam_deck,
        is_game_mode=_is_game_mode,
        is_debug=is_debug,
        coords=local_coords,
        version=version,
        paths=XDG,
        latest_release=latest_release,
        use_miles=use_miles,
    )
    print(boot.all_ok)
    App(prefs)
