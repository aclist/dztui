import logging
from typing import Literal, TYPE_CHECKING

from dzgui.const.enum import FilterMode
from dzgui.const.constants import EXPAND, NO_EXPAND, NO_FILL, NO_PADDING, SEARCH_ICON
from dzgui.model.servers import ServerModelManager
from dzgui.util.strings import all_maps
from dzgui.views.components.labels import BoldLabel

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib  # noqa E402

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


class ButtonGrid(Gtk.Grid):
    def __init__(self, controller: "Controller", defaults: dict) -> None:
        super().__init__(
            halign=Gtk.Align.CENTER, column_spacing=5, column_homogeneous=True
        )
        row = 1
        col = 0

        self.controller = controller
        self.emitter = controller.get_emitter()

        self.checks: list[Gtk.CheckButton] = []

        # TODO: use enumerated checks
        for check in defaults.keys():
            checkbox = Gtk.CheckButton(label=check)
            label = checkbox.get_children()
            label[0].set_ellipsize(Pango.EllipsizeMode.END)

            if defaults[check]:
                checkbox.set_active(True)

            col = col + 1
            if col > 3:
                row += 1
                col = 1
            self.attach(checkbox, col, row, 1, 1)
            checkbox.connect("toggled", self._on_check_toggled)
            self.checks.append(checkbox)

    def block_toggles(self, state: bool) -> None:
        for check in self.checks:
            self.controller.suppress_signal(
                self,
                check,
                "_on_check_toggled",
                state,
            )

    def reload_filters(self) -> None:
        checkboxes = self.checks
        self.block_toggles(True)
        filters = self.controller.get_enabled_filters()
        for check in checkboxes:
            label = check.get_label()
            state = filters[label]
            check.set_active(state)
        self.block_toggles(False)

    def _on_check_toggled(self, button: Gtk.CheckButton) -> None:
        label = button.get_label()
        state = button.get_active()
        logger.info(f"User toggled button '{label}' to {state}")
        self.emitter.emit("check_toggled", label, state)

    def get_checkboxes(self) -> list:
        return self.checks


class KeywordEntry(Gtk.Entry):
    def __init__(self, controller: "Controller") -> None:
        # TODO :strings
        super().__init__(placeholder_text="Filter by keyword")

        self.keyword = ""
        self.controller = controller
        self.emitter = controller.get_emitter()
        self.connect("activate", self._on_activated)
        self.connect("key-press-event", self._on_keypress)
        self.connect("icon-release", lambda *args: self.activate())

        self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, SEARCH_ICON)
        self.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)

    def _on_keypress(self, entry: Gtk.Entry, event: Gdk.EventKey) -> bool:
        match event.keyval:
            case Gdk.KEY_Up:
                return True
            case Gdk.KEY_Down:
                return True
            case Gdk.KEY_Escape:
                GLib.idle_add(self.restore_focus_to_treeview)
                return True
        return False

    def restore_focus_to_treeview(self) -> Literal[False]:
        view = self.controller.get_active_treeview()
        view.grab_focus()
        return False

    def _on_activated(self, entry: Gtk.Entry) -> None:
        # TODO: investigate this method
        # self.controller.mediator.window.set_keep_below(False)

        keyword = entry.get_text().lower()
        if keyword == self.keyword:
            return
        if keyword.isspace():
            return

        self.keyword = keyword
        # TODO: delegate to controller
        tv = self.controller.get_active_treeview()
        filter_man = tv.get_filter_man()
        filter_man.set_active_keyword(keyword)

        logger.info(f"User filtered by keyword '{keyword}'")

        ServerModelManager(
            self.controller, self.controller.get_active_treeview()
        ).refilter(FilterMode.KEYWORD)


class FilterPanel(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(
            spacing=6,
            vexpand=False,
            orientation=Gtk.Orientation.VERTICAL,
            margin_top=1,
            margin_bottom=10,
            margin_left=10,
            margin_right=10,
        )

        self.controller = controller
        self.controller.register_widget("filters", self)
        self.emitter = self.controller.get_emitter()

        self.sel_map = all_maps

        filter_man = self.controller.get_filter_man()
        defaults = filter_man.get_default_filters()
        self.map_store = filter_man.get_map_store()
        self.enabled_filters = defaults

        self.keyword_entry = KeywordEntry(self.controller)
        self.button_grid = ButtonGrid(self.controller, defaults)

        # TODO: strings
        self.filters_label = BoldLabel("Filters")

        self.emitter.connect(
            "request_keyword_focus", lambda _: self.keyword_entry.grab_focus()
        )
        self.emitter.connect(
            "request_maps_focus", lambda _: self.maps_entry.grab_focus()
        )
        self.emitter.connect("check_button_pressed", self.toggle_check_by_key)
        self.emitter.connect("load_maps", self._on_maps_loaded)

        # TODO: break into MapsCombo class
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
        self.maps_entry.connect("activate", self._on_maps_activated)

        self.maps_combo.pack_start(renderer_text, EXPAND)
        self.maps_combo.connect("changed", self._on_map_changed)
        self.maps_combo.connect("key-press-event", self._on_combo_keypress)

        for el in (
            self.filters_label,
            self.keyword_entry,
            self.maps_combo,
            self.button_grid,
        ):
            self.pack_start(el, NO_EXPAND, NO_FILL, NO_PADDING)

    def _on_maps_activated(self, entry: Gtk.Entry) -> None:
        text = entry.get_text()
        model = self.maps_combo.get_model()
        if text is None:
            return
        if text == self.sel_map:
            return
        for i, row in enumerate(model):
            if text == row[0]:
                self.maps_combo.set_active(i)

    # TODO: use same sort of signal to reinitialize keyword and checks
    def _on_maps_loaded(self, emitter: "Emitter", store: Gtk.ListStore) -> None:
        self.maps_combo.set_model(store)
        tv = self.controller.get_active_treeview()
        ind, name = tv.filter_man.get_active_map()
        # NOTE: setting active index triggers a 'changed' signal on self.maps_combo
        self.block_map_change_propagation = True
        self.maps_combo.set_active(ind)
        self.button_grid.reload_filters()

    # TODO: this chiefly applies when clicking refresh button, etc.
    # and setting filters to default state
    # def reinit_filters(self) -> None:
    #    self.enabled_filters = dict(self.default_filters)
    #    for check in self.checks:
    #        label = check.get_label()
    #        state = self.default_filters[label]
    #        check.set_active(state)

    def _on_map_entry_keypress(self, entry: Gtk.Entry, event: Gdk.EventKey) -> None:
        match event.keyval:
            case Gdk.KEY_Escape:
                GLib.idle_add(self.restore_focus_to_treeview)
                """
                This is a workaround for widget.grab_remove()
                Sets cursor position to start of line when unfocusing
                """
                text = self.maps_entry.get_text()
                self.maps_entry.set_position(len(text))
            case _:
                return False

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
        store = self.controller.get_map_store()
        if len(text) >= completion.get_minimum_key_length():
            completion.set_model(store)
        # ind = self.get_active_combo()
        # self.controller.set_active_map(ind)

    def restore_focus_to_treeview(self) -> Literal[False]:
        view = self.controller.get_active_treeview()
        view.grab_focus()
        return False

    def _on_combo_keypress(self, combo: Gtk.ComboBox, event: Gdk.EventKey) -> bool:
        match event.keyval:
            case Gdk.KEY_Down | Gdk.KEY_Up:
                self.maps_combo.popup()
                return True
            case _:
                return False

    def toggle_check_by_key(self, emitter: "Emitter", keyval: int) -> bool:
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
        return True

    def toggle_check(self, digit: int) -> None:
        checks = self.button_grid.get_checkboxes()
        check = checks[digit]
        state = check.get_active()
        check.set_active(not state)

    def _on_map_changed(self, combo: Gtk.ComboBox) -> None:
        ind = combo.get_active()
        if ind < 0:
            return
        name = self.maps_entry.get_text()
        self.prior_map = self.sel_map
        self.sel_map = name

        # TODO: abstraction into controller:
        # pass ind, name
        tv = self.controller.get_active_treeview()
        filter_man = tv.get_filter_man()
        filter_man.set_prior_map(name)
        filter_man.set_active_map(ind, name)

        if self.block_map_change_propagation:
            self.block_map_change_propagation = False
            return
        self.emitter.emit("map_selection_changed", name)
