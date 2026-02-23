import re

from typing import Optional, TYPE_CHECKING

from dzgui.const.enum import FilterMode
from dzgui.model.model_factory import ModelFactory
from dzgui.util import strings

import gi

gi.require_version("Gtk", "3.0")
from gi.repository.Gtk import ListStore  # noqa E402
from gi.repository import GObject, GLib  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


class FilteredModelManager:
    """
    Manages access to cached ListStore resources and
    performs filtering on behalf of atomic TreeViews,
    which share the same column structure.

    A FilteredModelManager is attached to each ServerTreeView.

    Raw data is cached before being packed into a ListStore, see get_control()
    Filtration creates a proxy of the TreeView's model, see get_proxy_model()
    """

    def __init__(self, controller: "Controller") -> None:
        self.controller = controller
        self.emitter = controller.get_emitter()
        self.emitter.connect("keyword_set", self._on_keyword_set)

        self.filter_cache = {}
        self.ping_cache: dict[str, int] = {}

        self.proxy_model: ListStore = None

        self.control_model: list = None
        self.filtered: list = None
        self.success = True

        self.keyword_filter = ""

    def get_keyword_filter(self) -> str:
        return self.keyword_filter

    def _on_keyword_set(self, emitter: "Emitter", keyword: str) -> None:
        self.keyword_filter = keyword

    def append_row(self, row: list) -> None:
        self.proxy_model.append(row)

    def clear_proxy_model(self) -> None:
        self.proxy_model.clear()

    def get_proxy_model(self) -> ListStore:
        return self.proxy_model

    def new_model_from_class(self, cls: type) -> ListStore:
        store = ListStore(*[ftype for field, ftype in cls.__annotations__.items()])
        return store

    def filter(self, mode: FilterMode, *args, **kwargs) -> None:
        """
        Native Gtk.TreeView.refilter() method was not performant enough
        when running in the main loop with 40k+ records
        """
        filters = self.controller.get_filters()

        if filters in self.filter_cache:
            cache = self.filter_cache[filters]
            self.set_proxy_model(cache[0])
            self.set_filtered(cache[1])
            return

        match mode:
            case FilterMode.INITIAL:
                rows = self.filter_initial(filters)

            case FilterMode.MAP:
                prior_map = self.controller.get_prior_map()

                if prior_map == strings.all_maps:
                    rows = self.filter_map(filters)
                else:
                    rows = self.filter_toggle_on(filters, *args)

            case FilterMode.KEYWORD:
                rows = self.filter_toggle_on(filters, *args)

            case FilterMode.TOGGLE_OFF:
                for f in filters[2:]:
                    self.set_filtered(self.filter_toggle_off(filters, f))
                rows = self.filtered

            case FilterMode.TOGGLE_ON:
                rows = self.filter_toggle_on(filters, *args)

        # TODO: unimplemented
        # just write pings into control model instead
        # if mode is not FilterMode.INITIAL:
        #    for row in rows:
        #        if row[7] in self.ping_cache:
        #            row[9] = self.ping_cache[row[7]]

        # NOTE: this ListStore manipulation must remain local to the thread
        clone = ModelFactory().make_server_store()
        if len(rows) > 0:
            rows = self.sort_rows(rows)
            clone.extend(rows)

        self.set_cache(filters, clone, rows)
        self.set_proxy_model(clone)
        return clone

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
        sel_map = self.controller.get_selected_map()

        if sel_map == strings.all_maps:
            return rows

        rows = [row for row in rows if row[1] == sel_map]
        return rows

    def filter_keyword(self, filters: tuple) -> list:
        keyword = self.keyword_filter
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
            strings.filter_official: strings.filter_unofficial,
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
                seen = set()
                final = []
                for row in rows:
                    if row[0] not in seen:
                        seen.add(row[0])
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

    def set_cache(self, filters: tuple, model: ListStore | None, rows: list) -> None:
        self.filter_cache[filters] = (model, rows)

    def resync_model(self, addr: str, qport: int) -> None:
        """
        Handle in-situ updates to model during
        row deletion/insertion actions. Skipped for ephemeral
        actions like player count/ping updates
        """
        for row in self.control_model:
            if row[7] == addr and row[8] == qport:
                self.control_model.remove(row)

        self.wipe_cache()
        filters = self.controller.get_filters()
        refiltered = self.filter_toggle_on(filters)
        self.set_filtered(refiltered)

    def convert_model_to_list(self, model: ListStore) -> list:
        return [[el for el in row] for row in model]

    def set_filtered(self, rows: Optional[list]) -> None:
        if rows is None:
            rows = []
        self.filtered = rows

    def get_filtered(self) -> list:
        return self.filtered

    def set_proxy_model(self, model: ListStore | None) -> None:
        """
        ListStore representation of the raw model after filtration
        """
        self.proxy_model = model

    def set_control(self, rows: list) -> None:
        """
        Raw data model prior to filtration
        """
        self.control_model = rows

    def get_control(self) -> list:
        return self.control_model

    # @deprecated("Legacy code")
    # def set_success(self, result: bool) -> None:
    #    self.success = result

    # @deprecated("Legacy code")
    # def get_success(self) -> bool:
    #    return self.success

    # NOTE: used when adding/removing rows in-situ in the proxy model
    # and syncing changes to control model, but ignored for player count/ping updates
    # cf. remove_from_history(), remove_server()
    # NOTE: this can most likely be simplified for v7
    def wipe_cache(self, full=False) -> None:
        # self.set_success(True)
        self.filtered = None
        self.filter_cache = {}
        self.ping_cache = {}
        # if full:
        # self.control_model = None
