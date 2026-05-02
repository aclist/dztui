import logging
import traceback

from typing import Any, TYPE_CHECKING

from dzgui.const.constants import (
    APP_NAME,
    FLATPAK_RUN_CMD,
    FLATPAK_SANDBOX,
    STEAM_CMD,
    WINDOW_DEFAULT_X,
    WINDOW_DEFAULT_Y,
)
from dzgui.api.probe import test_steam_api, test_bm_api
from dzgui.const.enum import Preferences
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.views.dialogs.generic import ExceptionDialog
from dzgui.util._json import read_json, write_json

import gi

gi.require_version("Gtk", "3.0")
from gi.repository.Gtk import main_quit  # noqa E402

# import dzgui.api.servers as Servers
if TYPE_CHECKING:
    from dzgui.config.userprefs import UserPrefs
    from dzgui.controllers.mc import Controller
    from dzgui.views.base import OuterWindow
    from dzgui.views.trees.tree_servers import ServerTreeView

logger = logging.getLogger(APP_NAME)


class ConfigManager:
    def __init__(self, prefs: "UserPrefs", controller: "Controller") -> None:
        self.prefs = prefs
        self.config = prefs.paths.config
        self.controller = controller
        self.emitter = controller.get_emitter()
        self.thread_man = ThreadingManager(controller)

    def lookup(self, enum: Preferences) -> Any:
        key = self.enum_to_key(enum)
        config = self.get_config()
        try:
            return config[key]
        except KeyError:
            return None

    def add_saved_server(self, record: str) -> None:
        ips = self.lookup(Preferences.IP_LIST)
        ips.append(record)
        self.update_config(Preferences.IP_LIST, ips)

    def update_history_file(self, records: list[Any]) -> None:
        with open(self.prefs.paths.history, "w") as f:
            for record in records:
                addr = f"{record[7]}:{record[8]}"
                f.write(f"{addr}\n")

    def remove_saved_server(self, record: str) -> None:
        ips = self.lookup(Preferences.IP_LIST)
        ips.remove(record)
        self.update_config(Preferences.IP_LIST, ips)

    # TODO: drop/reroute
    def update_config(self, key: Preferences, value: str) -> None:
        self.write_config(key, value)
        # TODO: suppress signals
        # then reenable (or it spawns dialog twice)
        # TODO: do this on demand if/when in options page
        # self.mediator.grid.notebook.settings.populate_settings()

    def get_config(self) -> Any:
        # TODO: is this being called twice?
        try:
            return read_json(self.config)
        except Exception as e:
            logger.critical(e)
            raise e

    # TODO: strings
    @call_on_thread("Checking api")
    def update_api_key(self, key: Preferences, text: str) -> None:
        if key is Preferences.STEAM:
            res = test_steam_api(text)
        else:
            res = test_bm_api(text)
        if res is True:
            self.update_config(key, text)
        else:
            self.thread_man.set_cleanup_func(
                StoredFunc(lambda: self.emitter.emit("api_change_failed"))
            )
        return

    def get_favorites(self) -> list[str]:
        return list(self.lookup(Preferences.IP_LIST))

    def get_favorite(self) -> tuple[str, str] | None:
        fav = str(self.lookup(Preferences.FAV_LBL))
        if len(fav) < 1:
            return None
        ip = str(self.lookup(Preferences.FAV_SRV))
        addr = ip.split(":")
        return fav, f"{addr[0]}:{addr[2]}"

    def is_in_favs(self, record: str) -> bool:
        favs = self.get_favorites()
        if record in favs:
            return True
        return False

    def enum_to_key(self, enum: Preferences) -> str:
        return str(enum.dict["key"])

    def get_client_index(self, client: str) -> int:
        if client == STEAM_CMD:
            return 0
        if client == FLATPAK_RUN_CMD:
            return 1
        if client == FLATPAK_SANDBOX:
            return 2
        return 0

    def toggle_config(self, key: Preferences) -> None:
        try:
            real_key = self.enum_to_key(key)
            _json = self.get_config()
            cur_val = not _json[real_key]
            _json[real_key] = cur_val
            write_json(_json, self.config)
        except Exception as e:
            logger.critical(e)
            raise e

    def set_fav(self, name: str, record: str) -> None:
        try:
            self.write_config(Preferences.FAV_LBL, name)
            self.write_config(Preferences.FAV_SRV, record)
        except Exception:
            return

    def write_config(self, key: Preferences, value: str) -> None:
        try:
            real_key = self.enum_to_key(key)
            conf = self.get_config()
            conf[real_key] = value
            write_json(conf, self.config)
        except Exception as e:
            logger.critical(e)
            trace = traceback.format_exc()
            dialog = ExceptionDialog(self.controller, trace)
            dialog.run()
            raise e

    def save_res_and_quit(self, tv: "ServerTreeView", window: "OuterWindow") -> None:
        columns = tv.get_columns()
        columns_file = self.prefs.paths.columns
        try:
            data = read_json(columns_file)
        except Exception as e:
            logger.critical(e)
            data = {"cols": {}}

        for column in columns:
            title = column.get_title()
            size = column.get_width()
            data["cols"][title] = size

        try:
            write_json(data, columns_file)
        except Exception as e:
            logger.critical(e)

        logger.info("Normal user exit")
        if window.props.is_maximized:
            main_quit()
            return

        w, h = window.get_size()
        data = {"res": {"width": w, "height": h}}

        res_path = self.prefs.paths.resolution
        try:
            write_json(data, res_path)
        except Exception as e:
            logger.critical(e)

        main_quit()

    def set_resolution(self, window: "OuterWindow") -> None:
        if self.prefs.is_game_mode:
            window.fullscreen()
            return
        elif self.lookup(Preferences.WINDOW) is True:
            window.fullscreen()

        try:
            data = read_json(self.prefs.paths.resolution)
            valid_json = True
        except Exception as e:
            valid_json = False
            logger.critical(e)

        if valid_json:
            res = data["res"]
            w, h = res["width"], res["height"]
            logger.info(f"Restoring window size to {w},{h}")
            window.set_default_size(w, h)
        else:
            w = WINDOW_DEFAULT_X
            h = WINDOW_DEFAULT_Y
            logger.info(f"Using default window size {w},{h}")
            window.set_default_size(w, h)
