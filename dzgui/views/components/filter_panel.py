import logging
from typing import Literal, TYPE_CHECKING

from dzgui.const.enum import FilterMode
from dzgui.const.constants import EXPAND, NO_EXPAND, NO_FILL, NO_PADDING, SEARCH_ICON
from dzgui.util.margins import set_surrounding_margins
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
        if keyword == self.controller.get_keyword():
            return
        if keyword.isspace():
            return

        logger.info(f"User filtered by keyword '{keyword}'")
        self.emitter.emit("keyword_set", keyword)
        self.controller.refilter_model(FilterMode.KEYWORD, keyword)


class FilterPanel(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(spacing=6, vexpand=False, orientation=Gtk.Orientation.VERTICAL)

        self.controller = controller
        self.controller.register_widget("filters", self)
        self.emitter = self.controller.get_emitter()

        # self.selected_map: str = strings.all_maps
        # self.prior_map: str = strings.all_maps
        # self.set_orientation(Gtk.Orientation.VERTICAL)

        # TODO: initialize to empty
        map_man = self.controller.get_map_man()
        defaults = map_man.get_default_filters()
        self.map_store = map_man.get_map_store()
        self.enabled_filters = defaults

        self.keyword_entry = KeywordEntry(self.controller)
        self.button_grid = ButtonGrid(self.controller, defaults)

        # TODO: unintended legacy behavior?
        self.connect("button-release-event", lambda *args: True)
        set_surrounding_margins(self, 10)
        self.set_margin_top(1)

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

        # FIXME: should be a property of treeview's meta manager
        self.active_map = 0

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
        for i, row in enumerate(model):
            if text == row[0]:
                self.maps_combo.set_active(i)
                self._on_map_changed(self.maps_combo)
                self.controller.set_active_map(i)

    def _on_maps_loaded(self, emitter: "Emitter", store: Gtk.ListStore) -> None:
        self.maps_combo.set_model(store)
        ind = self.controller.get_active_map()
        self.maps_combo.set_active(ind)
        self.button_grid.reload_filters()

    # TODO: move into metamanager
    def get_filters(self) -> tuple:
        selected = self.controller.get_selected_map()
        enabled = self.controller.get_enabled_filters()
        filters = []
        filters.append(selected)
        filters.append(self.controller.get_keyword())
        for filt in enabled:
            if enabled[filt] is False:
                filters.append(filt)
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
        ind = self.get_active_combo()
        self.controller.set_active_map(ind)

    def restore_focus_to_treeview(self) -> Literal[False]:
        view = self.controller.get_active_treeview()
        view.grab_focus()
        return False

    def _on_combo_keypress(self, combo: Gtk.ComboBox, event: Gdk.EventKey) -> bool:
        match event.keyval:
            case Gdk.KEY_Down:
                self.maps_combo.popup()
                return True
            case _:
                return False

    def get_active_combo(self) -> int:
        return self.maps_combo.get_active()

    def set_active_combo(self, row: int) -> None:
        self.maps_combo.set_active(row)

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
        old_sel = self.controller.get_selected_map()
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter is None:
            return
        selection = model[tree_iter][0]
        if selection == old_sel:
            return
        if not selection:
            return
        self.maps_entry.set_text(selection)
        logger.info(f"User selected map '{selection}'")
        self.emitter.emit("map_selection_changed", selection)
