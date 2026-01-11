import argparse
import logging
import os
import sys

from typing import TYPE_CHECKING

from dzgui.api.mods import remove_stale_signatures
from dzgui.config.ipdb import get_ipdb
from dzgui.config.userprefs import UserPrefs
from dzgui.config.xdg import get_xdg_paths, parse_filepaths
from dzgui.const.update import ALLOW_UPDATES
from dzgui.init.coords import get_local_coords
from dzgui.init.dayz import is_dayz_installed
from dzgui.init.flock import lock_acquire
from dzgui.init.migrate import (
    has_new_config,
    migrate_cols_file,
    migrate_legacy_conf,
    copy_state_files,
)
from dzgui.init.prefix import get_version
from dzgui.init.prereqs import has_steam_client
from dzgui.init.proc import is_dayz_running, is_steam_running
from dzgui.init.update import allow_updates, check_updates

from dzgui.util.map_count import get_map_count
from dzgui.util.deck import is_steam_deck, is_game_mode
from dzgui.util.localize import set_locale
from dzgui.util.symlink import rebuild_symlinks
from dzgui.util.strings import init, flags

from dzgui.views.base import App
from dzgui.views.dialogs.early_alert import EarlyAlertDialog

logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser(description=flags.description)

parser.add_argument("-v", "--version", action="store_true", help=flags.version)
parser.add_argument("-u", "--uninstall", action="store_true", help=flags.uninstall)
parser.add_argument("-d", "--developers", action="store_true", help=flags.developers)
args = parser.parse_args()

if TYPE_CHECKING:
    from pathlib import Path

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

def main() -> None:
    lock = lock_acquire()  # noqa

    if args.version is True:
        print(get_version())
        sys.exit(0)

    if args.uninstall is True:
        uninstall()
        sys.exit(0)

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

    if has_new_config(XDG.config) is False:
        migrate_legacy_conf(XDG.config)
        migrate_cols_file(XDG.columns)
        copy_state_files(xdg_paths["XDG_STATE_HOME"])

    _format = "%(asctime)s␞%(levelname)s␞%(filename)s::%(funcName)s::%(lineno)s␞%(message)s"
    logging.basicConfig(filename=XDG.debug, format=_format, level=logging.DEBUG)
    with open(XDG.debug, "w") as f:
        f.truncate(0)

    _is_steam_deck = is_steam_deck()
    _is_game_mode = is_game_mode() if _is_steam_deck else False
    if _is_game_mode:
        # NOTE: this may no longer be necessary on newer versions of SteamOS
        del os.environ["GTK_IM_MODULE"]

    # TODO: test spamming timeout
    allow = allow_updates(ALLOW_UPDATES)
    if allow is True:
        check_updates(version)

    if _is_steam_deck is False:
        # TODO: sudo escalation dialog
        count = get_map_count()
        # TODO: move into module
        if has_steam_client() is False:
            EarlyAlertDialog(init.requires_steam)

    is_dayz_installed(XDG.config)
    is_dayz_running()
    is_steam_running()

    rebuild_symlinks(XDG.config)
    remove_stale_signatures(XDG.config, XDG.version)

    # TODO: handle IP DB failure and use coords fallback
    get_ipdb(XDG.ips)
    local_coords = get_local_coords(XDG.ips)

    prefs = UserPrefs(
        _is_steam_deck,
        _is_game_mode,
        args.developers,
        local_coords,
        version,
        allow,
        XDG
    )
    print("All OK. Loading UI...")
    App(prefs)
