from dataclasses import dataclass

from dzgui.const.enum import HELP_MENU_ROWS
from dzgui.util.redact import redact_log
from dzgui.util.strings import delimiter
from dzgui.views.dialogs.generic import ExceptionDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository.Gtk import ListStore  # noqa E402
from gi.repository import GObject  # noqa E402


@dataclass(slots=True, frozen=True)
class ModCols:
    name: str
    symlink: str
    directory: str
    size: float
    color: bool


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


class FastInsertListStore(ListStore):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def append(self, row) -> None:
        total = len(row)
        i = len(self)
        tree_iter = self.insert_with_values(i, tuple(range(0, total)), row)
        return tree_iter


class ModelFactory:
    def __init__(self) -> None:
        pass

    def new_model_from_logfile(self, path: str) -> None:
        store = self.make_log_store()
        with open(path, "r") as f:
            lines = [line.split(delimiter) for line in f.read().splitlines()]
            for record in lines:
                # NOTE: strip PII and API keys
                clean = redact_log(record)
                store.append(clean)
        return store

    def new_model_from_class(self, cls: type) -> FastInsertListStore:
        store = FastInsertListStore(
            *[ftype for field, ftype in cls.__annotations__.items()]
        )
        return store

    def make_map_store(self) -> ListStore:
        return ListStore(str)

    def make_help_store(self) -> ListStore:
        store = self.new_model_from_class(MenuCols)
        for row in HELP_MENU_ROWS:
            label = row.dict["label"]
            store.append([label, row])
        return store

    def make_mod_store(self) -> ListStore:
        return self.new_model_from_class(ModCols)

    def make_log_store(self) -> ListStore:
        return self.new_model_from_class(LogCols)

    def make_server_mod_store(self) -> ListStore:
        return self.new_model_from_class(ServerModCols)
