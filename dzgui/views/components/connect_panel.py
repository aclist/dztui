from typing import TYPE_CHECKING

from dzgui.const.constants import UDP_PORT
from dzgui.model.servers import ServerModelManager
from dzgui.strings import connect_panel
from dzgui.util.keys import is_ctrl_mask
from dzgui.views.components.buttons import (
    AddButton,
    ClipboardButton,
    SteamConnectButton,
)
from dzgui.views.components.entry import IpEntry, PortEntry
from dzgui.views.components.labels import BoldLabel

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller, Emitter

COLS = 1
ROWS = 1


class LanPanel(Gtk.Frame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        self.controller = controller
        self.emitter = controller.get_emitter()

        label = BoldLabel(connect_panel.lan_heading)
        self.set_label_widget(label)

        self.default_radio = Gtk.RadioButton.new_with_label(
            None, connect_panel.lan_default_button
        )
        self.custom_radio = Gtk.RadioButton.new_with_label_from_widget(
            self.default_radio, connect_panel.lan_custom_button
        )

        self.entry = PortEntry(controller)
        self.scan = Gtk.Button(label=connect_panel.lan_scan_button)
        self.scan.connect("clicked", self._on_scan_clicked)

        # TODO: strings
        self.early_abort = Gtk.CheckButton(label=connect_panel.lan_checkbox)
        self.early_abort.set_active(True)
        self.early_abort.set_tooltip_text(connect_panel.lan_abort_tooltip)

        self.entry.connect("activate", self._on_entry_activated)
        self.entry.connect("string_validated", self._on_port_validated)
        self.entry.connect("key-release-event", self._on_lan_keypress)
        self.emitter.connect("request_custom_port_focus", self._on_custom_port_binding)
        self.emitter.connect(
            "request_default_port_focus", lambda _: self.default_radio.set_active(True)
        )
        self.default_radio.connect("toggled", self._on_radio_toggled)

        self.grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        self.grid.attach(self.default_radio, 0, 0, COLS, ROWS)
        self.grid.attach_next_to(
            self.custom_radio, self.default_radio, Gtk.PositionType.RIGHT, COLS, ROWS
        )
        self.grid.attach_next_to(
            self.entry, self.custom_radio, Gtk.PositionType.RIGHT, COLS, ROWS
        )
        self.grid.attach_next_to(
            self.scan, self.entry, Gtk.PositionType.RIGHT, COLS, ROWS
        )
        self.grid.attach_next_to(
            self.early_abort, self.scan, Gtk.PositionType.RIGHT, COLS, ROWS
        )

        self.add(self.grid)

        self.entry.set_sensitive(False)

    def _on_lan_keypress(self, widget: Gtk.Entry, event: Gdk.EventKey) -> bool:
        if is_ctrl_mask(event):
            if event.keyval == Gdk.KEY_d:
                self.default_radio.set_active(True)
                self.controller.grab_active_treeview()
                return True
        return False

    def _on_custom_port_binding(self, emitter: "Emitter") -> None:
        self.custom_radio.set_active(True)
        self.entry.grab_focus()

    def _on_entry_activated(self, entry: Gtk.Entry) -> None:
        if self.entry.get_text() == "":
            return
        self.scan_ports()

    def _on_scan_clicked(self, button: Gtk.Button) -> None:
        self.scan_ports()

    def scan_ports(self) -> None:
        if self.default_radio.get_active():
            port = UDP_PORT
        else:
            port = int(self.entry.get_text())
        abort = self.early_abort.get_active()
        smm = ServerModelManager(self.controller, self.controller.get_active_treeview())
        smm.dump_lan(port, abort)

    def _on_radio_toggled(self, button: Gtk.RadioButton) -> None:
        state = button.get_active()
        self.entry.set_sensitive(not state)
        if state:
            self.scan.set_sensitive(True)
        else:
            self.entry.grab_focus()
            if len(self.entry.get_text()) < 1:
                self.scan.set_sensitive(False)

    def _on_port_validated(self, entry: Gtk.Entry, state: bool) -> None:
        self.scan.set_sensitive(state)


class FavPanel(Gtk.Frame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        label = BoldLabel(connect_panel.fav_heading)
        self.set_label_widget(label)

        self.controller = controller
        emitter = self.controller.get_emitter()
        emitter.connect("fav_server_changed", self._on_fav_server_changed)

        self.server_name = ""
        self.server_ip = ""

        favorite = self.controller.get_config_man().get_favorite()
        if favorite is None:
            server_name = connect_panel.favs_empty
        else:
            self.server_name, self.server_ip = favorite
            server_name = f"{self.server_name} ({self.server_ip})"

        self.fav_label = Gtk.Label(
            label=server_name,
            track_visited_links=False,
            halign=Gtk.Align.START,
            hexpand=True,
        )

        self.fav_button = SteamConnectButton()
        self.fav_button.connect("clicked", self._on_connect_clicked)
        self.copy_button = ClipboardButton(self.controller, self.get_fav_ip)
        if favorite is None:
            self.toggle_buttons(False)

        # NOTE: disable vscrollbar to prevent layout jumping behavior
        scrollable_label = Gtk.ScrolledWindow(vscrollbar_policy=Gtk.PolicyType.NEVER)
        scrollable_label.add(self.fav_label)

        grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        grid.attach(scrollable_label, 0, 0, 3, ROWS)
        grid.attach_next_to(
            self.copy_button, scrollable_label, Gtk.PositionType.RIGHT, COLS, ROWS
        )
        grid.attach_next_to(
            self.fav_button, self.copy_button, Gtk.PositionType.RIGHT, COLS, ROWS
        )

        self.add(grid)

    def toggle_buttons(self, state: bool) -> None:
        for button in self.fav_button, self.copy_button:
            button.set_sensitive(state)

    def _on_connect_clicked(self, button: Gtk.Button) -> None:
        self.controller.connect_by_str(self.server_ip)

    def get_fav_ip(self) -> str:
        return self.server_ip

    def _on_fav_server_changed(
        self, emitter: "Emitter", name: str, record: str
    ) -> None:
        self.server_name = name
        self.server_ip = record
        self.fav_label.set_text(f"{name} ({record})")
        if self.server_name != "":
            self.toggle_buttons(True)


class AddPanel(Gtk.Frame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        self.controller = controller
        self.emitter = controller.get_emitter()
        self.classname = "invalid-entry"

        label = BoldLabel("Connect")
        self.set_label_widget(label)

        self.add_server = AddButton()
        self.add_server.connect("clicked", self._on_add_clicked)

        self.conn_server = SteamConnectButton()
        self.conn_server.connect("clicked", self._on_connect_clicked)
        self.conn_server.set_sensitive(False)
        self.add_server.set_sensitive(False)

        self.entry = IpEntry(controller)
        self.entry.connect("activate", self._on_activate)
        self.entry.connect("string_validated", self._on_ip_validated)
        self.emitter.connect(
            "request_ip_entry_focus", lambda _: self.entry.grab_focus()
        )
        self.emitter.connect("already_saved_server", self._on_duplicate_server)

        self.grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        self.grid.attach(self.entry, 0, 0, COLS, ROWS)
        self.grid.attach_next_to(
            self.add_server, self.entry, Gtk.PositionType.RIGHT, COLS, ROWS
        )
        self.grid.attach_next_to(
            self.conn_server, self.add_server, Gtk.PositionType.RIGHT, COLS, ROWS
        )

        self.add(self.grid)

        self.pop = Gtk.Popover()
        self.pop_label = Gtk.Label(
            label=connect_panel.add_popover,
            margin_start=10,
            margin_end=10,
        )
        self.pop.add(self.pop_label)
        # NOTE: render once to draw text in bubble
        self.pop.show_all()
        self.pop.set_margin_start(10)
        self.pop.set_relative_to(self.entry)
        self.pop.popdown()

    def _on_duplicate_server(self, emitter: "Emitter") -> None:
        self.pop.popup()

    def _on_connect_clicked(self, button: Gtk.Button) -> None:
        addr = self.entry.get_text()
        self.controller.connect_by_str(addr)

    def _add_server(self) -> None:
        addr = self.entry.get_text()
        self.controller.add_by_str(addr)

    def _on_activate(self, entry: Gtk.Entry) -> None:
        # NOTE: default action is to add a record, not connect
        self.add_server.emit("clicked")

    def _on_add_clicked(self, button: Gtk.Button) -> None:
        self._add_server()

    def _on_ip_validated(self, entry: Gtk.Entry, state: bool) -> None:
        self.conn_server.set_sensitive(state)
        self.add_server.set_sensitive(state)


class ConnectPanel(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.controller = controller
        emitter = self.controller.get_emitter()
        emitter.connect("lan_tab_toggled", self._on_lan_tab_toggled)

        self.lan = LanPanel(controller)
        self.fav = FavPanel(controller)
        self.add_panel = AddPanel(controller)

        for el in self.lan, self.fav, self.add_panel:
            self.add(el)

    def set_lan_visible(self, state: bool) -> None:
        self.lan.set_visible(state)

    def _on_lan_tab_toggled(self, emitter: "Emitter", state: bool) -> None:
        self.set_lan_visible(state)
