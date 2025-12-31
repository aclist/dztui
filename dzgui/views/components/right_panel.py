import gi  # noqa E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from dzgui.const.enum import Preferences
from dzgui.views.components.buttonbox import ButtonBox
from dzgui.views.components.filter_panel import FilterPanel
from dzgui.views.components.icon import Icon
from dzgui.const.constants import NO_EXPAND, NO_FILL, EXPAND, FILL, INPUT_KEYBOARD
from dzgui.util import strings

# TODO: refactor depends on ServerTreeView
class RightPanel(Gtk.Box):
    def __init__(self, appnav, controller):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)

        self.AppNav = appnav
        self.AppNav.right_panel = self
        self.controller = controller

        self.button_vbox = ButtonBox(controller)
        self.filters_vbox = FilterPanel(appnav, controller)

        for el in self.button_vbox, self.filters_vbox:
            padding = 0
            self.pack_start(el, NO_EXPAND, NO_FILL, padding)

        self.ping = Gtk.Button(
            label=strings.ping_servers,
            margin_top=10,
            margin_start=80,
            margin_end=80,
            tooltip_text=strings.ping_tooltip,
        )
        self.ping.connect("clicked", self._on_ping_clicked)

        # TODO: drop after adding context menu row
        self.debug_toggle = Gtk.ToggleButton(
            label=strings.debug_mode,
            margin_top=10,
            margin_start=80,
            margin_end=80,
            tooltip_text=strings.debug_tooltip,
        )

        if controller.query_config(Preferences.DEBUG) == True:
            self.debug_toggle.set_active(True)
        self.debug_toggle.connect("toggled", self._on_debug_toggled)

        i = Icon(INPUT_KEYBOARD)
        i.set_margin_start(5)
        self.question = Gtk.Button(
            label=strings.keys_button,
            margin_start=80,
            margin_end=80,
            tooltip_text=strings.keys_tooltip,
            image = i,
        )
        self.question.set_image_position(Gtk.PositionType.RIGHT)
        self.question.connect("clicked", self._on_question_clicked)

        for el in self.ping, self.debug_toggle, self.question:
            padding = 0
            self.pack_start(el, NO_EXPAND, FILL, padding)

    def enable_ping_button(self, state: bool) -> None:
        self.ping.set_visible(state)

    def reinit_maps(self, rows: list) -> None:
        self.controller.reinit_map_store()
        # TODO: communicate with controller
        #controller.clear_map_store()
        #map_store.append(["All maps"])
        self.selected = "All maps"
        self.filters_vbox.set_unique_maps(rows)

    def toggle_debug(self) -> None:
        if type(self.AppNav.window.get_focus()) is Gtk.Entry:
            return
        state = self.debug_toggle.get_active()
        self.debug_toggle.set_active(not state)

    def _on_debug_toggled(self, button: Gtk.Button) -> None:
        state = button.get_active()
        grid = self.AppNav.grid
        self.controller.toggle_debug_mode()

    def _on_ping_clicked(self, button: Gtk.Button) -> None:
        # TODO
        block_signals()

        def _update_pings():
            # TODO
            rows = ModelManager.get_filtered()
            with ThreadPoolExecutor(100) as executor:
                futures = [
                    executor.submit(Servers.ping, i, row)
                    for i, row in enumerate(rows)
                ]
                wait(futures)
                for future in futures:
                    res = future.result()
                    path = Gtk.TreePath.new_from_indices([res.iteration])
                    temp_model[path][9] = res.ping
                    ModelManager.ping_cache[res.addr] = res.ping
            self.AppNav.treeview.set_model(temp_model)
            self.AppNav.treeview.wait_dialog.destroy()
            self.AppNav.treeview.enable_ping_column(True)
            self.AppNav.treeview.grab_focus()
            self.AppNav.right_panel.ping.set_sensitive(False)

            # TODO:
            unblock_signals()

        temp_model = self.AppNav.treeview.get_model()
        self.AppNav.treeview.set_model(None)
        self.AppNav.treeview.wait_dialog = GenericDialog("Pinging servers", Popup.WAIT)
        self.AppNav.treeview.wait_dialog.show_all()
        thread = threading.Thread(target=_update_pings, args=())
        thread.start()

    def _on_question_clicked(self, button: Gtk.Button) -> None:
        self.AppNav.grid.notebook.toggle_keybindings()

    def focus_button_box(self) -> None:
        self.button_vbox.buttons[0].grab_focus()
