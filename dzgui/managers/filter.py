from typing import TYPE_CHECKING

from dzgui.model.model_factory import ModelFactory
from dzgui.util import strings
from dzgui.util.strings import all_maps

if TYPE_CHECKING:
    from dzgui.model.model_factory import FastInsertListStore


class FilterManager:
    def __init__(self) -> None:

        self.map_store = ModelFactory().make_map_store()

        # TODO: namespace under own file: strings.filters
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

        self.active_keyword = ""
        self.active_map = (0, all_maps)
        self.prior_map = all_maps

        self.filters: list
        self.enabled_filters = dict(self.default_filters)

    def set_prior_map(self, name: str) -> None:
        self.prior_map = name

    def get_active_map_name(self) -> str:
        return self.active_map[1]

    def get_active_map(self) -> int:
        return self.active_map

    def set_active_map(self, ind: int, name: str) -> None:
        self.active_map = (ind, name)

    def get_active_keyword(self) -> str:
        return self.active_keyword

    def set_active_keyword(self, word: str) -> None:
        self.active_keyword = word

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
        self.active_map = (0, all_maps)

    def append_map(self, row: list[str]) -> None:
        self.map_store.append(row)

    def set_unique_maps(self, maps: list) -> None:
        if maps is None:
            return
        if len(maps) < 1:
            return

        self.reinit_map_store()
        maps.sort()
        for m in maps:
            if m == "All maps":
                continue
            self.append_map([m])

    def get_unique_maps(self) -> list[str]:
        return [row[0] for row in self.map_store if row != "All maps"]

    def get_all_filters(self) -> tuple:
        map_name = self.get_active_map_name()
        enabled = self.get_filters()
        kw = self.get_active_keyword()
        filters = []
        filters.append(map_name)
        filters.append(kw)
        for filt in enabled:
            if enabled[filt] is False:
                filters.append(filt)
        return tuple(filters)
