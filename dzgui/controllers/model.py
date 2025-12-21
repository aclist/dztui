import re
from dataclasses import dataclass
from typing import Self

from dzgui.const.enum import FilterMode, HELP_MENU_ROWS
from dzgui.util import strings

import gi
gi.require_version("Gtk", "3.0")
from gi.repository.Gtk import ListStore  # noqa E402
from gi.repository import GObject, GLib  # noqa E402

@dataclass
@dataclass(slots=True, frozen=True)
class ServerColumns:
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
    Manages access to cached ListStore resources and
    performs filtering on behalf of TreeViews.

    Methods are not thread-safe in themselves.
    """
    def __init__(self) -> None:
        self.filter_cache: tuple
        self.ping_cache: dict[str, int] = {}

        self.map_store = ListStore(str)
        #self.row_store = self.new_model_from_class(MenuCols)
        self.help_store = self.new_model_from_class(MenuCols)

        self.mod_store = self.new_model_from_class(ModCols)
        self.log_store = self.new_model_from_class(LogCols)
        self.modlist_store = self.new_model_from_class(ServerModCols)

        self.server_store = self.new_model()
        self.saved_store = self.new_model()
        self.recent_store = self.new_model()
        self.lan_store = self.new_model()

        for row in HELP_MENU_ROWS:
            label = row.dict["label"]
            self.help_store.append([label, row])

        self.control_model = None
        self.filtered = None
        self.success = True

    def __new__(cls) -> Self:
        if not hasattr(cls, "instance"):
            cls.instance = super(ModelManager, cls).__new__(cls)
        return cls.instance

    def get_recent_store(self) -> ListStore:
        return self.recent_store

    def get_lan_store(self) -> ListStore:
        return self.lan_store

    def get_saved_store(self) -> ListStore:
        return self.saved_store

    def get_server_store(self) -> ListStore:
        return self.server_store

    def new_model_from_class(self, cls: type) -> ListStore:
        store = ListStore(*[ftype for field, ftype in cls.__annotations__.items()])
        return store

    def get_map_store(self) -> ListStore:
        return self.map_store

    #def get_row_store(self) -> ListStore:
    #    return self.row_store

    def get_help_store(self) -> ListStore:
        return self.help_store

    def get_mod_store(self) -> ListStore:
        return self.mod_store

    def get_modlist_store(self) -> ListStore:
        return self.modlist_store

    def get_log_store(self) -> ListStore:
        return self.log_store

    def filter(self, mode: FilterMode, *args, **kwargs) -> None:
        """
        Native Gtk.TreeView.refilter() method was not performant enough
        when running in the main loop with 40k+ records
        """
        filters = AppNav.right_panel.filters_vbox.get_filters()

        if filters in self.filter_cache:
            cache = self.filter_cache[filters]
            self.set_store(cache[0])
            self.set_filtered(cache[1])
            GLib.idle_add(AppNav.treeview._filter_cleanup)
            return

        match mode:
            case FilterMode.INITIAL:
                rows = self.filter_initial(filters)

            case FilterMode.MAP:
                panel = AppNav.right_panel.filters_vbox
                prior_map = panel.get_prior_map()

                if prior_map == "All maps":
                    rows = self.filter_map(filters)
                else:
                    AppNav.right_panel.ping.set_sensitive(True)
                    rows = self.filter_toggle_on(filters, *args)

            case FilterMode.KEYWORD:
                AppNav.right_panel.ping.set_sensitive(True)
                rows = self.filter_toggle_on(filters, *args)

            case FilterMode.TOGGLE_OFF:
                for f in filters[2:]:
                    self.set_filtered(self.filter_toggle_off(filters, f))
                rows = self.filtered

            case FilterMode.TOGGLE_ON:
                AppNav.right_panel.ping.set_sensitive(True)
                rows = self.filter_toggle_on(filters, *args)

        if mode is not FilterMode.INITIAL:
            for row in rows:
                if row[7] in self.ping_cache:
                    row[9] = self.ping_cache[row[7]]

        if len(rows) > 0:
            clone = self.new_model()
            rows = self.sort_rows(rows)
            for row in rows:
                clone.append(row)
        else:
            clone = None

        self.set_cache(filters, clone, rows)
        self.set_store(clone)
        GLib.idle_add(AppNav.treeview._filter_cleanup)

    def sort_rows(self, rows: list) -> list:
        rows.sort(key=lambda x: re.sub(r"[^A-Za-z0-9]+", "", x[0].lower()))
        return rows

    def filter_initial(self, filters: tuple) -> list:
        """
        Simply culls the control model of any disabled filters
        """
        self.set_filtered(self.control_model)
        for f in filters[2:]:
            self.set_filtered(self.filter_toggle_off(filters, f))
        return self.filtered

    def filter_map(self, filters: tuple) -> list:
        """
        Multi-filtration for any context starts by narrowing by map
        """
        rows = self.filtered
        panel = AppNav.right_panel.filters_vbox
        sel_map = panel.get_selected_map()

        if sel_map == "All maps":
            return rows

        rows = [row for row in rows if row[1] == sel_map]
        return rows

    def filter_keyword(self, filters: tuple) -> list:
        keyword = AppNav.right_panel.filters_vbox.get_keyword_filter()
        rows = self.filtered

        if keyword == "":
            return rows

        filtered = [
            row
            for row in rows
            if keyword in row[0].lower()
            or keyword in row[1].lower()
            or keyword in row[7].lower()
        ]
        return filtered

    def filter_toggle_off(self, filters: tuple, filter_type: str) -> list:
        """
        Sub-filtration of the current model
        """
        pairs = {
            strings.filter_3pp: strings.filter_1pp,
            strings.filter_day: strings.filter_night,
            strings.filter_official: strings.filter_unofficial
        }
        for k, v in pairs.items():
            if k in filters and v in filters:
                self.set_filtered(None)
                return []

        rows = self.filtered
        match filter_type:
            case strings.filter_3pp:
                rows = [row for row in rows if row[2] != strings.filter_3pp]
            case strings.filter_1pp:
                rows = [row for row in rows if row[2] != strings.filter_1pp]
            case strings.filter_official:
                rows = [row for row in rows if row[10] != strings.filter_official]
            case strings.filter_unofficial:
                rows = [row for row in rows if row[10] != strings.filter_unofficial]
            case strings.filter_empty:
                rows = [row for row in rows if row[4] != 0]
            case strings.filter_full:
                rows = [row for row in rows if row[4] != row[5]]
            case strings.filter_duplicate:
                seen = []
                final = []
                for row in rows:
                    if row[0] in seen:
                        continue
                    seen.append(row[0])
                    final.append(row)
                rows = final
            case strings.filter_day:
                reg = r"([0][0-9]|[1][0-6])"
                rows = [row for row in rows if not re.match(reg, row[3])]
            case strings.filter_night:
                reg = r"([0][0-4]|[1][8]|[2][0-3])"
                rows = [row for row in rows if not re.match(reg, row[3])]
            case strings.filter_nonascii:
                rows = [row for row in rows if row[0].isascii()]
            case strings.filter_lowpop:
                rows = [row for row in rows if (row[4] / row[5] * 100) > 30]
            case strings.filter_modded:
                rows = [row for row in rows if not row[11]]
        return rows

    def filter_toggle_on(self, filters: tuple, *args: str) -> list:
        """Effectively applies all filters"""
        self.set_filtered(self.control_model)
        self.set_filtered(self.filter_map(filters))
        self.set_filtered(self.filter_keyword(filters))

        for f in filters[2:]:
            self.set_filtered(self.filter_toggle_off(filters, f))
        return self.filtered

    def set_cache(
        self, filters: tuple, model: ListStore | None, rows: list
    ) -> None:
        self.filter_cache[filters] = (model, rows)

    def new_model(self) -> ListStore:
        store = self.new_model_from_class(ServerColumns)
        return store

    def resync_model(self, addr: str, qport: int) -> None:
        """
        Handle in-situ updates to model during
        row deletion actions. Skipped for ephemeral
        actions like player count/ping updates
        """
        for row in self.control_model:
            if row[7] == addr and row[8] == qport:
                self.control_model.remove(row)

        self.wipe_cache()
        filters = AppNav.right_panel.filters_vbox.get_filters()
        refiltered = self.filter_toggle_on(filters)
        self.set_filtered(refiltered)
        self.set_success(True)
        GLib.idle_add(AppNav.treeview._filter_cleanup)

    def convert_model_to_list(self, model: ListStore) -> list:
        return [[el for el in row] for row in model]

    def set_filtered(self, rows: list | None) -> None:
        if rows is None:
            rows = []
        self.filtered = rows

    def get_filtered(self) -> list:
        return self.filtered

    def set_store(self, model: ListStore | None) -> None:
        self.store = model

    def get_store(self) -> ListStore | None:
        return self.store

    def set_control(self, rows: list) -> None:
        self.control_model = rows

    def set_success(self, result: bool) -> None:
        self.success = result

    def get_success(self) -> bool:
        return self.success

    def wipe_cache(self, full=False) -> None:
        self.success = True
        self.filtered = None
        self.filter_cache = {}
        self.ping_cache = {}
        if full:
            self.control_model = None

    def set_all_maps(self) -> None:
        self.map_store.clear()
        self.map_store.append(["All maps"])

    def append_map(self, row: list) -> None:
        self.map_store.append(row)
