import logging
from typing import Literal, TYPE_CHECKING

from dzgui.const.enum import FilterMode
from dzgui.const.constants import EXPAND, NO_EXPAND, NO_FILL, NO_PADDING, SEARCH_ICON
from dzgui.util import strings
from dzgui.util.margins import set_surrounding_margins
from dzgui.views.components.labels import BoldLabel

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib  # noqa E402

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


class FilterPanel(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(spacing=6, vexpand=False)

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

        self.controller = controller
        self.controller.register_widget("filters", self)
        self.emitter = self.controller.get_emitter()

        self.map_store = self.controller.get_map_store()

        self.checks = []
        self.maps_hr = []

        self.enabled_filters = dict(self.default_filters)
        self.keyword_filter = ""
        self.selected_map: str = strings.all_maps
        self.prior_map: str = strings.all_maps

        button_grid = Gtk.Grid(
            halign=Gtk.Align.CENTER, column_spacing=5, column_homogeneous=True
        )
        row = 1
        col = 0
        # TODO: use enumerated checks
        for check in self.default_filters.keys():
            checkbox = Gtk.CheckButton(label=check)
            label = checkbox.get_children()
            label[0].set_ellipsize(Pango.EllipsizeMode.END)

            if self.default_filters[check]:
                checkbox.set_active(True)

            col = col + 1
            if col > 3:
                row += 1
                col = 1
            button_grid.attach(checkbox, col, row, 1, 1)

            checkbox.connect("toggled", self._on_check_toggled)
            self.checks.append(checkbox)

        self.connect("button-release-event", self._on_button_release)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        set_surrounding_margins(self, 10)
        self.set_margin_top(1)

        # TODO: strings
        self.filters_label = BoldLabel("Filters")

        self.keyword_entry = Gtk.Entry()
        # TODO :strings
        self.keyword_entry.set_placeholder_text("Filter by keyword")
        self.keyword_entry.connect("activate", self._on_keyword_activated)
        self.keyword_entry.connect("key-press-event", self._on_keyword_keypress)
        self.keyword_entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, SEARCH_ICON
        )
        self.keyword_entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.keyword_entry.connect(
            "icon-release", lambda *args: self.keyword_entry.activate()
        )

        self.emitter.connect(
            "request_keyword_focus", lambda _: self.keyword_entry.grab_focus()
        )
        self.emitter.connect(
            "request_maps_focus", lambda _: self.maps_entry.grab_focus()
        )
        self.emitter.connect("check_button_pressed", self.toggle_check_by_key)

        completion = Gtk.EntryCompletion(inline_completion=True)
        completion.set_text_column(0)
        completion.set_minimum_key_length(1)
        completion.connect("match_selected", self._on_completer_match)

        renderer_text = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        self.maps_combo = Gtk.ComboBox.new_with_model_and_entry(self.map_store)
        self.maps_combo.set_entry_text_column(0)

        self.maps_entry = self.maps_combo.get_child()
        self.maps_entry.set_completion(completion)
        self.maps_entry.set_placeholder_text("Filter by map")
        self.maps_entry.connect("changed", self._on_map_completion, True)
        self.maps_entry.connect("key-press-event", self._on_map_entry_keypress)

        self.maps_combo.pack_start(renderer_text, EXPAND)
        self.maps_combo.connect("changed", self._on_map_changed)
        self.maps_combo.connect("key-press-event", self._on_combo_keypress)

        for el in self.filters_label, self.keyword_entry, self.maps_combo, button_grid:
            self.pack_start(el, NO_EXPAND, NO_FILL, NO_PADDING)

    def set_unique_maps(self, maps: list) -> None:
        if maps is None:
            return
        if len(maps) < 1:
            return
        u_maps = set([row[1] for row in maps])
        u_maps = sorted(u_maps)
        self.controller.append_map([strings.all_maps])
        self.selected_map = strings.all_maps
        for m in u_maps:
            self.controller.append_map([m])
            self.maps_hr.append(m)
        self.maps_combo.set_active(0)

    def get_filters(self) -> tuple:
        filters = []
        filters.append(self.selected_map)
        filters.append(self.keyword_filter)
        for k in self.enabled_filters:
            if not self.enabled_filters[k]:
                filters.append(k)
        return tuple(filters)

    # TODO: should be used when switching ServerTab contexts
    # use signals here
    # def reinit_panel(self) -> None:
    #    self.keyword_entry.set_text("")
    #    self.keyword_filter = ""
    #    self.reinit_filters()
    #    self.set_visible(False)
    #    sel_panel = self.controller.mediator.grid.sel_panel
    #    if sel_panel.is_visible():
    #        sel_panel.set_visible(False)

    # TODO: change filters on a per-tab basis
    def reinit_filters(self) -> None:
        self.enabled_filters = dict(self.default_filters)
        for check in self.checks:
            label = check.get_label()
            state = self.default_filters[label]
            check.set_active(state)

    def _on_map_entry_keypress(self, entry: Gtk.Entry, event: Gdk.EventKey) -> None:
        # TODO: use activated() signal
        match event.keyval:
            case Gdk.KEY_Return:
                text = entry.get_text()
                if text is None:
                    return
                """
                If entry is exact match for value in liststore,
                trigger map change function
                """
                for i in enumerate(self.map_store):  # type: ignore
                    if text == i[1][0]:
                        self.maps_combo.set_active(i[0])
                        self._on_map_changed(self.maps_combo)
            case Gdk.KEY_Escape:
                GLib.idle_add(self.restore_focus_to_treeview)
                """
                This is a workaround for widget.grab_remove()
                Sets cursor position to start of line when unfocusing
                """
                text = self.maps_entry.get_text()
                self.maps_entry.set_position(len(text))
            case _:
                return

    def _on_completer_match(
        self,
        completion: Gtk.EntryCompletion,
        model: Gtk.ListStore,
        it: Gtk.TreeIter,
    ) -> None:
        self.maps_combo.set_active_iter(it)

    def _on_map_completion(self, entry, editable):
        text = entry.get_text()
        completion = entry.get_completion()
        if len(text) >= completion.get_minimum_key_length():
            completion.set_model(self.map_store)

    def restore_focus_to_treeview(self) -> Literal[False]:
        view = self.controller.get_active_treeview()
        view.grab_focus()
        return False

    def _on_keyword_keypress(self, entry: Gtk.Entry, event: Gdk.EventKey) -> bool:
        match event.keyval:
            case Gdk.KEY_Up:
                return True
            case Gdk.KEY_Down:
                return True
            case Gdk.KEY_Escape:
                GLib.idle_add(self.restore_focus_to_treeview)
                return True
        return False

    def _on_combo_keypress(self, combo: Gtk.ComboBox, event: Gdk.EventKey) -> bool:
        match event.keyval:
            case Gdk.KEY_Down:
                self.maps_combo.popup()
                return True
            case _:
                return False

    def set_prior_map(self, mapname: str) -> None:
        self.prior_map = mapname

    def get_prior_map(self) -> str:
        return self.prior_map

    def get_selected_map(self) -> str:
        return self.selected_map

    def get_keyword_filter(self) -> str:
        return self.keyword_filter

    def _on_keyword_activated(self, entry: Gtk.Entry) -> None:
        # TODO:
        self.controller.mediator.window.set_keep_below(False)
        keyword = entry.get_text().lower()
        if keyword == self.keyword_filter:
            return
        if keyword.isspace():
            return
        logger.info(f"User filtered by keyword '{keyword}'")
        self.keyword_filter = keyword
        self.controller.refilter_model(FilterMode.KEYWORD, keyword)

    def _on_button_release(self, window, button) -> Literal[True]:
        return True

    def get_active_combo(self) -> int:
        return self.maps_combo.get_active()

    def set_active_combo(self, row: int) -> None:
        self.maps_combo.set_active(row)

    def toggle_check_by_key(
        self, emitter: "Emitter", keyval: int
    ) -> None | Literal[False]:
        mappings = {
            Gdk.KEY_1: 0,
            Gdk.KEY_2: 1,
            Gdk.KEY_3: 2,
            Gdk.KEY_4: 3,
            Gdk.KEY_5: 4,
            Gdk.KEY_6: 5,
            Gdk.KEY_7: 6,
            Gdk.KEY_8: 7,
            Gdk.KEY_9: 8,
            Gdk.KEY_0: 9,
            Gdk.KEY_minus: 10,
            Gdk.KEY_backslash: 11,
        }
        if keyval not in mappings:
            return False
        index = mappings[keyval]
        self.toggle_check(index)

    def toggle_check(self, digit: int) -> None:
        check = self.checks[digit]
        state = check.get_active()
        check.set_active(not state)

    def _on_check_toggled(self, button: Gtk.CheckButton) -> None:
        # treeview = self.controller.get_active_treeview()
        label = button.get_label()
        state = button.get_active()
        logger.info(f"User toggled button '{label}' to {state}")
        if state:
            mode = FilterMode.TOGGLE_ON
        else:
            mode = FilterMode.TOGGLE_OFF

        self.enabled_filters[label] = state
        self.controller.refilter_model(mode, label)

    def _on_map_changed(self, combo: Gtk.ComboBox) -> None:
        old_sel = self.selected_map
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter is None:
            return
        selection = model[tree_iter][0]
        if selection == old_sel:
            return
        if not selection:
            return
        logger.info(f"User selected map '{selection}'")
        self.prior_map = self.selected_map
        self.selected_map = selection
        self.maps_entry.set_text(selection)
        self.controller.refilter_model(FilterMode.MAP)
