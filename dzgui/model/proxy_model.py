import re

from typing import Any, TYPE_CHECKING, Union
from warnings import deprecated

from dzgui.const.enum import FilterMode
from dzgui.model.model_factory import ModelFactory
from dzgui.util import strings

if TYPE_CHECKING:
    from dzgui.managers.filter import FilterManager
    from dzgui.model.model_factory import FastInsertListStore
    from dzgui.api.servers import Record
    from dzgui.model.servers import NewPlayerCount


class ProxyModelManager:
    """
    Manages access to cached FastInsertListStore resources and
    performs filtering on behalf of atomic TreeViews,
    which share the same column structure.

    A ProxyModelManager is attached to each ServerTreeView.

    Raw data is cached before being packed into a FastInsertListStore, see get_control()
    Filtration creates a proxy of the TreeView's model, see get_proxy_model()
    """

    def __init__(self, filter_man: "FilterManager") -> None:
        self.filter_cache: dict[tuple[str], tuple["FastInsertListStore", list[Any]]] = (
            {}
        )

        self.proxy_model: "FastInsertListStore"
        self.filter_man = filter_man

        self.control_model: (
            list[tuple[str, str, str, str, int, int, int, str, int, int, str, bool]]
            | None
        ) = None
        self.filtered: list[
            tuple[str, str, str, str, int, int, int, str, int, int, str, bool]
        ] = []
        self.success = True

    def has_control_model(self) -> bool:
        if self.control_model is None:
            return False
        return True

    def append_row(self, row: list) -> None:
        self.proxy_model.append(row)

    def append_row_to_control(
        self, row: tuple[str, str, str, str, int, int, int, str, int, int, str, bool]
    ) -> None:
        if self.control_model is None:
            raise AttributeError("Trying to add rows to a non-existent model")
        self.control_model.append(row)
        self.filter(FilterMode.INITIAL, skip_cache=True)

    def update_playercount(self, playercount: "NewPlayerCount") -> None:
        treeiter = playercount.treeiter
        self.proxy_model[treeiter][4] = playercount.players
        self.proxy_model[treeiter][6] = playercount.queue

    # TODO: use dataclass for record rows
    def append_row_to_history(
        self,
        history: tuple[str, str, str, str, int, int, int, str, int, int, str, bool],
    ) -> None:
        addr = history[7]
        qport = history[8]

        if self.control_model is None:
            raise AttributeError("Trying to append row to empty model")
        found = False
        for i, row in enumerate(self.control_model):
            if addr == row[7] and qport == row[8]:
                item = self.control_model.pop(i)
                self.control_model.append(item)
                found = True
                break

        if found is False:
            self.control_model.append(history)
        if len(self.control_model) == 11:
            del self.control_model[0]

        self.filter(FilterMode.INITIAL, skip_cache=True)

    def remove_row_from_control(self, record: "Record") -> None:
        if self.control_model is None:
            return
        addr = f"{record.ip}:{record.gameport}"
        qport = record.qport
        for row in self.control_model:
            if addr == row[7] and qport == row[8]:
                self.control_model.remove(row)
                break
        self.wipe_cache()
        self.filter(FilterMode.INITIAL, skip_cache=True)

    def clear_proxy_model(self) -> None:
        self.proxy_model.clear()

    def get_proxy_model(self) -> Union["FastInsertListStore", None]:
        if hasattr(self, "proxy_model"):
            return self.proxy_model
        return None

    def filter(
        self, mode: FilterMode, skip_cache: bool = False
    ) -> Union["FastInsertListStore", None]:
        """
        Native Gtk.TreeView.refilter() method was not performant enough
        when running in the main loop with 40k+ records

        skip_cache: used when updating a record on Saved Servers/History and forcing a refilter
        """
        # TODO: filter cache: return a dataclass object with clearly enumerated map, keyword, and filter values
        # instead of just a serial list of strings
        filters = self.filter_man.get_all_filters()

        if skip_cache is False:
            if filters in self.filter_cache:
                cache = self.filter_cache[filters]
                self.set_proxy_model(cache[0])
                self.set_filtered(cache[1])
                return None

        match mode:
            case FilterMode.INITIAL:
                rows = self.filter_initial(filters)
            case FilterMode.TOGGLE_ON:
                rows = self.filter_toggle_on(filters)
            case FilterMode.TOGGLE_OFF:
                for f in filters[2:]:
                    self.set_filtered(self.filter_toggle_off(filters, f))
                rows = self.filtered

        # NOTE: FastInsertListStore manipulation must remain local to the thread
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
        sel_map = self.filter_man.get_active_map_name()

        if sel_map == strings.all_maps:
            return rows

        rows = [row for row in rows if row[1] == sel_map]
        return rows

    def filter_keyword(self, filters: tuple) -> list:
        keyword = self.filter_man.get_active_keyword()
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

    def filter_toggle_on(self, filters: tuple) -> list:
        """Effectively applies all filters"""
        self.set_filtered(self.control_model)
        self.set_filtered(self.filter_map(filters))
        self.set_filtered(self.filter_keyword(filters))

        for f in filters[2:]:
            self.set_filtered(self.filter_toggle_off(filters, f))
        return self.filtered

    def set_cache(
        self, filters: tuple, model: "FastInsertListStore", rows: list
    ) -> None:
        self.filter_cache[filters] = (model, rows)

    @deprecated("Currently unused")
    # def convert_model_to_list(self, model: "FastInsertListStore") -> list:
    #    return [[el for el in row] for row in model]

    def set_filtered(self, rows: list | None) -> None:
        if rows is None:
            self.filtered = []
        else:
            self.filtered = rows

    def get_filtered(self) -> list:
        return self.filtered

    def set_proxy_model(self, model: "FastInsertListStore") -> None:
        """
        FastInsertListStore representation of the raw model after filtration
        """
        self.proxy_model = model

    def set_control(self, rows: list) -> None:
        """
        Raw data model prior to filtration
        """
        self.control_model = rows

    def get_control(self) -> list[Any]:
        if self.control_model is None:
            raise AttributeError(
                "Expected a populated control model, but it is Nonetype"
            )
        return self.control_model

    def wipe_cache(self, full: bool = False) -> None:
        self.filtered = []
        self.filter_cache = {}

    def push(self, data: list[Any]) -> None:
        self.wipe_cache()
        self.set_control(data)
        self.filter(FilterMode.INITIAL)
