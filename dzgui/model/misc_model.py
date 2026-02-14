from dataclasses import dataclass
from dzgui.const.enum import HELP_MENU_ROWS

import gi

gi.require_version("Gtk", "3.0")
from gi.repository.Gtk import ListStore  # noqa E402
from gi.repository import GObject, Gtk  # noqa E402


@dataclass(slots=True, frozen=True)
class ModCols:
    name: str
    symlink: str
    directory: str
    size: float
    color: str


@dataclass(slots=True, frozen=True)
class LogCols:
    timestamp: str
    flag: str
    traceback: str
    msg: str


@dataclass(slots=True, frozen=True)
class ServerModCols:
    name: str
    uid: GObject.TYPE_INT64
    installed: str


@dataclass(slots=True, frozen=True)
class MenuCols:
    name: str
    hidden: GObject.TYPE_PYOBJECT


class ModelManager:
    """
    Manager for miscellaneous ListStores
    """

    def __init__(self) -> None:

        self.map_store = ListStore(str)
        self.help_store = self.new_model_from_class(MenuCols)
        self.log_store = self.new_model_from_class(LogCols)
        # FIXME: needs to be generated on demand
        self.modlist_store = self.new_model_from_class(ServerModCols)

        for row in HELP_MENU_ROWS:
            label = row.dict["label"]
            self.help_store.append([label, row])

    def new_model_from_class(self, cls: type) -> ListStore:
        store = ListStore(*[ftype for field, ftype in cls.__annotations__.items()])
        return store

    def get_map_store(self) -> ListStore:
        return self.map_store

    def get_help_store(self) -> ListStore:
        return self.help_store

    def new_mod_store(self) -> ListStore:
        return self.new_model_from_class(ModCols)

    def get_log_store(self) -> ListStore:
        return self.log_store

    def get_modlist_store(self) -> ListStore:
        return self.modlist_store

    def set_all_maps(self) -> None:
        self.map_store.clear()
        self.map_store.append(["All maps"])

    def append_map(self, row: list) -> None:
        self.map_store.append(row)
