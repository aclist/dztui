from typing import TYPE_CHECKING

from dzgui.util.strings import connect_panel, fav_panel, lan_panel
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

        label = BoldLabel(lan_panel.heading)
        self.set_label_widget(label)

        self.radio1 = Gtk.RadioButton.new_with_label(None, lan_panel.default_button)
        radio2 = Gtk.RadioButton.new_with_label_from_widget(
            self.radio1, lan_panel.custom_button
        )

        self.entry = PortEntry(controller)
        self.scan = Gtk.Button(label=lan_panel.scan_button)
        self.scan.connect("clicked", self._on_scan_clicked)
        # TODO: strings
        self.early_abort = Gtk.CheckButton("Stop scanning on first hit")
        self.early_abort.set_active(True)
        self.early_abort.set_tooltip_text(
            "Unless you have multiple DayZ servers on your LAN,\nleave this checked to get results faster"
        )

        self.entry.connect("string_validated", self._on_port_validated)
        self.emitter.connect(
            "request_lan_entry_focus", lambda _: self.entry.grab_focus()
        )
        self.radio1.connect("toggled", self._on_radio_toggled)

        self.grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        self.grid.attach(self.radio1, 0, 0, COLS, ROWS)
        self.grid.attach_next_to(
            radio2, self.radio1, Gtk.PositionType.RIGHT, COLS, ROWS
        )
        self.grid.attach_next_to(self.entry, radio2, Gtk.PositionType.RIGHT, COLS, ROWS)
        self.grid.attach_next_to(
            self.scan, self.entry, Gtk.PositionType.RIGHT, COLS, ROWS
        )
        self.grid.attach_next_to(
            self.early_abort, self.scan, Gtk.PositionType.RIGHT, COLS, ROWS
        )

        self.add(self.grid)

        self.entry.set_sensitive(False)

    def _on_scan_clicked(self, button: Gtk.Button) -> None:
        if self.radio1.get_active():
            port = 27016
        else:
            port = self.entry.get_text()
        abort = self.early_abort.get_active()
        self.controller.dump_lan(int(port), abort)

    def _on_radio_toggled(self, button: Gtk.RadioButton) -> None:
        state = button.get_active()
        self.entry.set_sensitive(not state)
        if state:
            self.scan.set_sensitive(True)
        elif len(self.entry.get_text()) < 1:
            self.scan.set_sensitive(False)

    def _on_port_validated(self, entry: Gtk.Entry, state: bool) -> None:
        self.scan.set_sensitive(state)


class FavPanel(Gtk.Frame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        label = BoldLabel(fav_panel.heading)
        self.set_label_widget(label)

        self.controller = controller
        emitter = self.controller.get_emitter()
        emitter.connect("fav_server_changed", self._on_fav_server_changed)

        self.server_name, self.server_ip = self.controller.get_favorite()
        server_name = (
            f"{self.server_name} ({self.server_ip})"
            if self.server_name is not None
            else connect_panel.no_fav
        )
        self.fav_label = Gtk.Label(
            label=server_name,
            track_visited_links=False,
            halign=Gtk.Align.START,
            hexpand=True,
        )
        # NOTE: disable vscrollbar to prevent layout jumping behavior
        scrollable_label = Gtk.ScrolledWindow(vscrollbar_policy=Gtk.PolicyType.NEVER)
        scrollable_label.add(self.fav_label)

        self.fav_button = SteamConnectButton()
        if server_name is None:
            self.fav_button.set_sensitive(False)
        copy = ClipboardButton(self.controller, self.get_fav_ip)

        grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        grid.attach(scrollable_label, 0, 0, 3, ROWS)
        grid.attach_next_to(copy, scrollable_label, Gtk.PositionType.RIGHT, COLS, ROWS)
        grid.attach_next_to(self.fav_button, copy, Gtk.PositionType.RIGHT, COLS, ROWS)

        self.add(grid)

    def get_fav_ip(self) -> str:
        return self.server_ip

    from dzgui.api.servers import Record

    def _on_fav_server_changed(
        self, emitter: "Emitter", name: str, record: str
    ) -> None:
        self.server_name = name
        self.server_ip = record
        self.fav_label.set_text(f"{name} ({record})")


class AddPanel(Gtk.Frame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        self.controller = controller
        self.emitter = controller.get_emitter()
        self.classname = "invalid-entry"

        label = BoldLabel("Connect")
        self.set_label_widget(label)

        self.add_server = AddButton()
        self.conn_server = SteamConnectButton()
        self.conn_server.set_sensitive(False)
        self.add_server.set_sensitive(False)

        self.entry = IpEntry(controller)
        self.entry.connect("string_validated", self._on_ip_validated)
        self.emitter.connect(
            "request_ip_entry_focus", lambda _: self.entry.grab_focus()
        )

        self.grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        self.grid.attach(self.entry, 0, 0, COLS, ROWS)
        self.grid.attach_next_to(
            self.add_server, self.entry, Gtk.PositionType.RIGHT, COLS, ROWS
        )
        self.grid.attach_next_to(
            self.conn_server, self.add_server, Gtk.PositionType.RIGHT, COLS, ROWS
        )

        self.add(self.grid)

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

    def _on_lan_tab_toggled(self, emitter: "Emitter", state: bool) -> None:
        self.lan.set_visible(state)
