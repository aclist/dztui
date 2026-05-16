import argparse
import logging
import os
import sys
import warnings

from typing import TYPE_CHECKING

from dzgui.api.mods import remove_stale_signatures
from dzgui.const.constants import APP_NAME
from dzgui.const.enum import Preferences
from dzgui.config.ipdb import get_ipdb
from dzgui.config.query import lookup
from dzgui.config.userprefs import UserPrefs
from dzgui.config.xdg import get_xdg_paths, parse_filepaths
from dzgui.init.coords import get_local_coords
from dzgui.init.dayz import is_dayz_installed
from dzgui.init.flock import lock_acquire
from dzgui.init.migrate import (
    has_new_config,
    # migrate_cols_file,
    # copy_state_files,
)
from dzgui.init.prefix import get_version
from dzgui.init.prereqs import has_steam_client
from dzgui.strings import boot
from dzgui.init.update import check_updates

# from dzgui.util.map_count import get_map_count
from dzgui.util.deck import is_steam_deck, is_game_mode
from dzgui.util.localize import set_locale
from dzgui.util.symlink import rebuild_symlinks
from dzgui.util.strings import init, flags

from dzgui.views.base import App
from dzgui.views.dialogs.wizard import SetupWizard
from dzgui.views.dialogs.early_alert import EarlyAlertDialog

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(APP_NAME)

parser = argparse.ArgumentParser(description=flags.description)
parser.add_argument("-v", "--version", action="store_true", help=flags.version)
parser.add_argument("-u", "--uninstall", action="store_true", help=flags.uninstall)
parser.add_argument("-d", "--debug", action="store_true", help=flags.debug)
args = parser.parse_args()


# TODO: profile load time
def make_parents(path: "Path") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def uninstall() -> None:
    # TODO: uninstall data files (-u)
    # -u removes state, log, freedesktop
    # XDG_SHARE_HOME/dzgui
    # XDG_STATE_HOME/dzgui
    # XDG_DATA_HOME/dzgui
    pass


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


def main() -> None:
    lock = lock_acquire()  # noqa

    if args.version is True:
        print(get_version())
        sys.exit(0)
    if args.uninstall is True:
        uninstall()
        sys.exit(0)
    if args.debug is True:
        warnings.filterwarnings("default", category=DeprecationWarning)

    version = get_version()
    set_locale()

    # NOTE: consider aborting this check if steam deck
    xdg_paths = get_xdg_paths()
    XDG = parse_filepaths(xdg_paths)

    if XDG.resolution.parent.is_dir() is False:
        make_parents(XDG.resolution)

    # TODO: test
    if XDG.debug.is_file() is False:
        make_parents(XDG.debug)

    _is_steam_deck = is_steam_deck()
    _is_game_mode = is_game_mode() if _is_steam_deck else False
    if _is_game_mode:
        # NOTE: this may no longer be necessary on newer versions of SteamOS
        del os.environ["GTK_IM_MODULE"]

    if has_new_config(XDG.config) is False:
        # TODO: add logging inside wizard
        # TODO: copy notes file, version file, etc.
        # migrate_cols_file(XDG.columns)
        # copy_state_files(xdg_paths["XDG_STATE_HOME"])
        SetupWizard(version, _is_steam_deck, XDG.config)
        return

    setup_logger(XDG.debug)
    with open(XDG.debug, "w") as f:
        f.truncate(0)

    update_available = check_updates(version)

    if _is_steam_deck is False:
        # TODO: sudo escalation dialog
        # count = get_map_count()
        # TODO: move into module
        if has_steam_client() is False:
            EarlyAlertDialog(init.requires_steam)

    # NOTE: clear versions file of unlinked mods
    rebuild_symlinks(XDG.config)
    remove_stale_signatures(XDG.config, XDG.version)

    is_dayz_installed(XDG.config)
    # TODO: handle IP DB failure and use coords fallback
    get_ipdb(XDG.ips)
    local_coords = get_local_coords(XDG.ips)
    use_miles = lookup(XDG.config, Preferences.DIST)

    prefs = UserPrefs(
        is_steam_deck=_is_steam_deck,
        is_game_mode=_is_game_mode,
        is_debug=args.debug,
        coords=local_coords,
        version=version,
        paths=XDG,
        update_available=update_available,
        use_miles=use_miles,
    )
    # TODO: drop allow updates
    print(boot.all_ok)
    App(prefs)
