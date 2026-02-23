from typing import TYPE_CHECKING

from dzgui.model.model_factory import ModelFactory
from dzgui.util import strings
from dzgui.util.strings import all_maps

if TYPE_CHECKING:
    from dzgui.model.model_factory import FastInsertListStore


# TODO: rename class to MetaManager
class MapManager:
    def __init__(self) -> None:

        self.map_store = ModelFactory().make_map_store()
        self.prior_map: str
        self.selected_map = all_maps

        # TODO: namespace under strings.filters
        self.default_filters = {
            strings.filter_1pp: True,
            strings.filter_day: True,
            strings.filter_empty: False,
            strings.filter_3pp: True,
            strings.filter_night: True,
            strings.filter_full: False,
            strings.filter_lowpop: True,
            strings.filter_nonascii: False,
            strings.filter_duplicate: False,
            strings.filter_official: True,
            strings.filter_unofficial: True,
            strings.filter_modded: True,
        }
        self.active_map = 0
        self.filters: list
        self.enabled_filters = dict(self.default_filters)

    def reinit_filters(self) -> None:
        self.enabled_filters = dict(self.default_filters)

    def get_active_map(self) -> int:
        return self.active_map

    def set_active_map(self, ind: int) -> None:
        self.active_map = ind

    def get_default_filters(self) -> dict:
        """Deep copy of defaults"""
        return dict(self.default_filters)

    def get_filters(self) -> dict:
        return self.enabled_filters

    def set_filter(self, label: str, state: bool) -> None:
        self.enabled_filters[label] = state

    def get_map_store(self) -> "FastInsertListStore":
        return self.map_store

    def reinit_map_store(self) -> None:
        model = ModelFactory().make_map_store()
        model.append([all_maps])
        self.map_store = model
        self.selected_map = all_maps

    def get_prior_map(self) -> str:
        return self.prior_map

    def get_selected_map(self) -> str:
        return self.selected_map

    def set_selected_map(self, selection: str) -> str:
        self.prior_map = self.selected_map
        self.selected_map = selection

    def append_map(self, row: list[str]) -> None:
        self.map_store.append(row)

    def clear_map_store(self) -> None:
        self.map_store.clear()

    def set_unique_maps(self, maps: list) -> None:
        if maps is None:
            return
        if len(maps) < 1:
            return

        self.reinit_map_store()
        for m in maps:
            self.append_map([m])

    # when switching views, just grab the map store, active keyword, active map, and selected checks
    # for that view and apply them to filter panel outside of thread
    # initialize proxyman with access to filterman
