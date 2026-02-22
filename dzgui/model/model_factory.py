from dataclasses import dataclass
from typing import Any

from dzgui.const.enum import HELP_MENU_ROWS
from dzgui.util.redact import redact_log
from dzgui.util.strings import delimiter

import gi

gi.require_version("Gtk", "3.0")
from gi.repository.Gtk import ListStore  # noqa E402
from gi.repository import GObject  # noqa E402

GTYPE_TO_PYTHON = {
    GObject.type_from_name(GObject.type_name(ptype)): ptype
    for ptype in (int, float, str, bool, object)
}


@dataclass(slots=True, frozen=True)
class ServerCols:
    name: str
    _map: str
    perspective: str
    gametime: str
    players: int
    _max: int
    queue: int
    ip: str
    qport: int
    ping: int
    provider: str
    modded: bool


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
    name: GObject.TYPE_STRING  # str
    hidden: GObject.TYPE_PYOBJECT


class FastInsertListStore(ListStore):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _is_same_length(self, lists: list[list[Any]]) -> bool:
        first_len = len(lists[0])
        if not all(len(sublist) == first_len for sublist in lists):
            return False
        return True

    def _is_type_homogeneous(self, lists: list[list[Any]]) -> bool:
        transposed = zip(*lists)

        for column in transposed:
            first_type = type(column[0])
            if not all(type(item) is first_type for item in column):
                return False
        return True

    def extend(self, rows: list[list[Any]]) -> None:
        """
        Compared to calling append() directly, introduces negligible overhead,
        but guarantees type and length equivalence prior to insertion
        """
        n_cols = self.get_n_columns()
        expected_types = [
            GTYPE_TO_PYTHON[self.get_column_type(i)] for i in range(n_cols)
        ]
        if not self._is_same_length(rows):
            raise ValueError("Sublists are not of uniform length")
        if not self._is_type_homogeneous(rows):
            raise TypeError("Sublists are not type homogeneous")
        if not all(isinstance(a, b) for a, b in zip(rows[0], expected_types)):
            raise TypeError("Sublist types are not same as ListStore")
        if len(rows[0]) != n_cols:
            raise ValueError("Sublist column length is not same as ListStore")

        for row in rows:
            self.append(row)

    def append(self, row) -> None:
        """
        Optimized for speed, but makes no assurances about row homogeneity
        and may segfault if types and length are not identical to ListStore.
        For this reason, it is recommended to use the extend() method to insert
        an entire list of lists
        """
        total = len(row)
        i = len(self)
        tree_iter = self.insert_with_values(i, tuple(range(total)), row)
        return tree_iter


class ModelFactory:
    def __init__(self) -> None:
        pass

    def new_model_from_logfile(self, path: str) -> None:
        store = self.make_log_store()
        with open(path, "r") as f:
            lines = [line.split(delimiter) for line in f.read().splitlines()]
            for record in lines:
                # NOTE: strips PII and API keys
                clean = redact_log(record)
                store.append(clean)
        return store

    def new_model_from_class(self, cls: type) -> FastInsertListStore:
        store = FastInsertListStore(
            *[ftype for field, ftype in cls.__annotations__.items()]
        )
        return store

    def make_map_store(self) -> FastInsertListStore:
        return ListStore(str)

    def make_help_store(self) -> FastInsertListStore:
        store = self.new_model_from_class(MenuCols)
        rows = [[row.dict["label"], row] for row in HELP_MENU_ROWS]
        # for row in rows:HELP_MENU_ROWS:
        #    print(type(row) is object)
        store.extend(rows)
        # for row in HELP_MENU_ROWS:
        #    label = row.dict["label"]
        #    store.append([label, row])
        return store

    def make_mod_store(self) -> FastInsertListStore:
        return self.new_model_from_class(ModCols)

    def make_log_store(self) -> FastInsertListStore:
        return self.new_model_from_class(LogCols)

    def make_server_mod_store(self) -> FastInsertListStore:
        return self.new_model_from_class(ServerModCols)

    def make_server_store(self) -> FastInsertListStore:
        return self.new_model_from_class(ServerCols)
