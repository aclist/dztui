import logging
import traceback

from typing import Any, TYPE_CHECKING

from dzgui.const.constants import STEAM_CMD, FLATPAK_RUN_CMD, FLATPAK_SANDBOX
from dzgui.const.enum import Preferences
from dzgui.views.dialogs.generic import ExceptionDialog
from dzgui.util._json import read_json, write_json

# import dzgui.api.servers as Servers
if TYPE_CHECKING:
    from dzgui.config.userprefs import UserPrefs

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, prefs: "UserPrefs") -> None:
        self.config = prefs.paths.config

    def lookup(self, enum: Preferences) -> Any:
        # if path.is_file() is False:
        #    raise ConfigFileError("Not a valid file")
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

    # TODO: drop/reroute
    def update_config(self, key: Preferences, value: str) -> None:
        self.write_config(key, value)
        # TODO: suppress signals
        # then reenable (or it spawns dialog twice)
        # TODO: do this on demand if/when in options page
        # self.mediator.grid.notebook.settings.populate_settings()
        return

    def get_config(self) -> dict:
        # TODO: is this being called twice?
        try:
            return read_json(self.config)
        except Exception as e:
            logger.critical(e)
            raise e

    def get_favorites(self) -> list[str]:
        return self.lookup(Preferences.IP_LIST)

    def is_in_favs(self, record: str) -> bool:
        favs = self.get_favorites()
        if record in favs:
            return True
        return False

    def enum_to_key(self, enum: Preferences) -> str:
        return enum.dict["key"]

    def get_client_index(client: str) -> int:
        if client == STEAM_CMD:
            return 0
        if client == FLATPAK_RUN_CMD:
            return 1
        if client == FLATPAK_SANDBOX:
            return 2

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

    def write_config(self, key: Preferences, value: str) -> None:
        try:
            real_key = self.enum_to_key(key)
            conf = self.get_config()
            conf[real_key] = value
            write_json(conf, self.config)
        except Exception as e:
            logger.critical(e)
            trace = traceback.format_exc()
            dialog = ExceptionDialog(self, trace)
            dialog.run()
            raise e
