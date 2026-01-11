from typing import TYPE_CHECKING

from dzgui.api.servers import validate_ip
from dzgui.util.css import add_class, remove_class
from dzgui.util.strings import connect_panel
from dzgui.views.components.buttons import AddButton, ClipboardButton, SteamConnectButton
from dzgui.views.components.labels import BoldLabel

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

COLS = 1
ROWS = 1

class LanPanel(Gtk.Frame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        # TODO: hide lan panel on other tabs
        # TODO: strings
        label = BoldLabel("LAN query port")
        self.set_label_widget(label)

        radio1 = Gtk.RadioButton.new_with_label(None, "Default port (27016)")
        radio2 = Gtk.RadioButton.new_with_label_from_widget(radio1, "Custom port")

        self.entry = Gtk.Entry(placeholder_text="Enter the query port (1-65535)", sensitive=False, hexpand=True)
        self.button = Gtk.Button(label="Scan")
        radio1.connect("toggled", self._on_radio_toggled)

        self.grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        self.grid.attach(radio1, 0, 0, COLS, ROWS)
        # TODO: expression to attach in a line
        self.grid.attach_next_to(radio2, radio1, Gtk.PositionType.RIGHT, COLS, ROWS)
        self.grid.attach_next_to(self.entry, radio2, Gtk.PositionType.RIGHT, COLS, ROWS)
        self.grid.attach_next_to(self.button, self.entry, Gtk.PositionType.RIGHT, COLS, ROWS)

        self.add(self.grid)

    def _on_radio_toggled(self, button: Gtk.RadioButton) -> None:
        self.entry.set_sensitive(not button.get_active())
        # TODO: validate custom port entry

class AddPanel(Gtk.Frame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        label = BoldLabel("Connect")
        self.set_label_widget(label)

        self.add_server = AddButton()
        self.conn_server = SteamConnectButton()
        self.conn_server.set_sensitive(False)
        self.add_server.set_sensitive(False)

        self.entry = Gtk.Entry(
            placeholder_text=connect_panel.placeholder,
            hexpand=True,
            tooltip_text=connect_panel.entry_tooltip
        )
        self.entry.connect("key-press-event", self._on_entry_keypress)
        self.entry.connect("changed", self._on_text_changed)

        self.grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        self.grid.attach(self.entry, 0, 0, COLS, ROWS)

        els = (
            (self.add_server, self.entry, Gtk.PositionType.RIGHT, COLS, ROWS),
            (self.conn_server, self.add_server, Gtk.PositionType.RIGHT, COLS, ROWS),
        )

        for el, sibling, pos, h_span, v_span in els:
            self.grid.attach_next_to(el, sibling, pos, h_span, v_span)

        self.add(self.grid)

    def mark_valid(self) -> None:
        self.conn_server.set_sensitive(True)
        self.add_server.set_sensitive(True)
        remove_class(self.entry, self.classname)

    def mark_invalid(self) -> None:
        self.conn_server.set_sensitive(False)
        self.add_server.set_sensitive(False)
        add_class(self.entry, self.classname)

    def _on_text_changed(self, entry: Gtk.Entry) -> None:
        # TODO: on submission, strip whitespace and newlines
        text = entry.get_text()
        if len(text) < 1:
            self.conn_server.set_sensitive(False)
            self.add_server.set_sensitive(False)
            remove_class(entry, self.classname)
            return
        try:
            validate_ip(text)
            self.mark_valid()
        except Exception:
            if text.isdigit():
                self.mark_valid()
            else:
                self.mark_invalid()

    def _on_entry_keypress(self, entry: Gtk.Entry, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            # NOTE: unselect text
            entry.select_region(0, 0)
            self.controller.grab_active_treeview()


class ConnectPanel(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.classname = "invalid-entry"
        self.controller = controller

        user_fav, self.fav_ip = self.controller.get_favorite()

        server_name = f"{user_fav} ({self.fav_ip})" if user_fav is not None else connect_panel.no_fav
        self.fav_label = Gtk.Label(label=server_name, track_visited_links=False, halign=Gtk.Align.START, hexpand=True)
        scrollable_label = Gtk.ScrolledWindow()
        scrollable_label.add(self.fav_label)

        self.fav_button = SteamConnectButton()
        self.fav_edit = Gtk.Button(label=connect_panel.edit)
        if server_name is None:
            self.fav_button.set_sensitive(False)

        self.lan = LanPanel(self.controller)
        self.add_panel = AddPanel(self.controller)

        label = BoldLabel("Favorite server")
        frame = Gtk.Frame(margin_top=10, margin_bottom=5, label_widget=label)
        b = ClipboardButton(self.controller, self.get_fav_ip())

        # FIXME: height of connect buttons is not equivalent
        grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        grid.attach(scrollable_label, 0, 0, 3, ROWS)
        grid.attach_next_to(b, scrollable_label, Gtk.PositionType.RIGHT, COLS, ROWS)
        grid.attach_next_to(self.fav_button, b, Gtk.PositionType.RIGHT, COLS, ROWS)
        frame.add(grid)

        for el in self.lan, frame, self.add_panel:
            self.add(el)

    def get_fav_ip(self) -> str:
        return self.fav_ip

    def set_fav_label(self, text: str) -> None:
        # TODO: called by controller when changing fav
        self.fav_label.set_text(text)

