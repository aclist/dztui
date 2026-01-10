from typing import Literal, TYPE_CHECKING

import gi  # noqa E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from dzgui.const.enum import Preferences
from dzgui.views.components.buttonbox import ButtonBox
from dzgui.views.components.filter_panel import FilterPanel
from dzgui.views.components.mod_panel import ModSelectionPanel
from dzgui.views.components.buttons import RefreshButton, KeysButton
from dzgui.const.constants import NO_EXPAND, NO_FILL, EXPAND, FILL, INPUT_KEYBOARD, NO_PADDING
from dzgui.util.strings import refresh_tooltip, refresh, keys_button, keys_tooltip

if TYPE_CHECKING:
    from GLib import SOURCE_REMOVE

# TODO: refactor depends on ServerTreeView
class RightPanel(Gtk.Box):
    def __init__(self, controller):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)

        self.time = 30

        self.controller = controller
        self.controller.register_widget("right_panel", self)

        self.button_vbox = ButtonBox(controller)
        self.filters_vbox = FilterPanel(controller)
        self.sel_panel = ModSelectionPanel(controller)

        self.refresh_button = RefreshButton()
        # TODO: consolidate into class
        self.refresh_button.set_tooltip_text(refresh_tooltip)
        self.refresh_button.set_focus_on_click(False)
        self.refresh_button.connect("clicked", self._on_refresh_clicked)

        self.keys = KeysButton(keys_button)
        self.keys.set_focus_on_click(False)
        self.keys.set_tooltip_text(keys_tooltip)
        self.keys.connect("clicked", self._on_keys_clicked)

        for el in self.button_vbox, self.keys, self.filters_vbox, self.refresh_button:
            self.pack_start(el, NO_EXPAND, FILL, NO_PADDING)

        self.pack_start(self.sel_panel, NO_EXPAND, NO_FILL, NO_PADDING)

    # TODO: move to filter panel
    def reinit_maps(self, rows: list) -> None:
        self.controller.reinit_map_store()
        # TODO: communicate with controller
        #controller.clear_map_store()
        #map_store.append(["All maps"])
        self.selected = "All maps"
        self.filters_vbox.set_unique_maps(rows)

    def decrement(self) -> "SOURCE_REMOVE" | Literal[True]:
        self.time -= 1
        if self.time == 0:
            self.time = 30
            self.refresh_button.set_label(refresh)
            self.refresh_button.set_sensitive(True)
            return GLib.SOURCE_REMOVE
        self.refresh_button.set_label(f"{refresh} ({str(self.time)})")
        return True

    def _on_refresh_clicked(self, button: RefreshButton) -> None:
        # TODO: could be internal to refresh button class
        self.refresh_button.set_sensitive(False)
        self.refresh_button.set_label(f"{refresh} ({str(self.time)})")
        GLib.timeout_add_seconds(1, self.decrement)
        self.controller.refresh_tree()

    # TODO: reference
    #def _on_ping_clicked(self, button: Gtk.Button) -> None:
    #    block_signals()
    #    def _update_pings():
    #        # TODO
    #        rows = ModelManager.get_filtered()
    #        with ThreadPoolExecutor(100) as executor:
    #            futures = [
    #                executor.submit(Servers.ping, i, row)
    #                for i, row in enumerate(rows)
    #            ]
    #            wait(futures)
    #            for future in futures:
    #                res = future.result()
    #                path = Gtk.TreePath.new_from_indices([res.iteration])
    #                temp_model[path][9] = res.ping
    #                ModelManager.ping_cache[res.addr] = res.ping
    #        # TODO: drop/rewrite
    #        treeview.set_model(temp_model)
    #        treeview.wait_dialog.destroy()
    #        treeview.grab_focus()

    #        # TODO:
    #        unblock_signals()

    #    temp_model = self.AppNav.treeview.get_model()
    #    treeview.set_model(None)
    #    treeview.wait_dialog = GenericDialog("Pinging servers", Popup.WAIT)
    #    treeview.wait_dialog.show_all()
    #    thread = threading.Thread(target=_update_pings, args=())
    #    thread.start()

    def _on_keys_clicked(self, button: Gtk.Button) -> None:
        self.controller.open_keybindings()

    def focus_button_box(self) -> None:
        self.button_vbox.buttons[0].grab_focus()
