from typing import Optional, TYPE_CHECKING

from dzgui.views.components.buttonbox import ButtonBox
from dzgui.views.components.filter_panel import FilterPanel
from dzgui.views.components.mod_panel import ModSelectionPanel
from dzgui.views.components.buttons import RefreshButton, KeysButton
from dzgui.const.constants import NO_EXPAND, NO_FILL, FILL, NO_PADDING

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


class RightPanel(Gtk.Box):
    def __init__(self, controller: "Controller"):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)

        self.controller = controller
        self.controller.register_widget("right_panel", self)

        emitter = controller.get_emitter()
        emitter.connect("request_button_box_focus", self.focus_button_box)

        self.button_vbox = ButtonBox(controller)
        self.filters_vbox = FilterPanel(controller)
        self.sel_panel = ModSelectionPanel(controller)

        self.refresh_button = RefreshButton(controller)
        self.keys = KeysButton(controller)

        for el in self.button_vbox, self.keys, self.filters_vbox, self.refresh_button:
            self.pack_start(el, NO_EXPAND, FILL, NO_PADDING)

        self.pack_start(self.sel_panel, NO_EXPAND, NO_FILL, NO_PADDING)

    # TODO: move to filter panel
    def reinit_maps(self, rows: list) -> None:
        self.controller.reinit_map_store()
        # TODO: communicate with controller
        # self.controller.clear_map_store()
        # map_store.append(["All maps"])
        self.selected = "All maps"
        self.filters_vbox.set_unique_maps(rows)

    # TODO: reference
    # def _on_ping_clicked(self, button: Gtk.Button) -> None:
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

    def focus_button_box(self, emitter: Optional["Emitter"] = None) -> None:
        self.button_vbox.buttons[0].grab_focus()
