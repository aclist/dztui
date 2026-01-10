from typing import TYPE_CHECKING

from dzgui.api.servers import validate_ip
from dzgui.const.constants import NO_EXPAND, NO_FILL, NO_PADDING
from dzgui.util.css import add_class, remove_class
from dzgui.util.strings import connect_panel
from dzgui.views.components.buttons import AddButton, ClipboardButton, IconTextButton, SteamConnectButton, WebButton
from dzgui.views.components.labels import BoldLabel

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

class LanPanel(Gtk.Frame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        # TODO: use grid, more column spacing
        # TODO: hide lan panel on other tabs
        hbox = Gtk.Box(margin=10, spacing=5, halign=Gtk.Align.START)
        # TODO: strings
        label = BoldLabel("LAN query port")
        self.set_label_widget(label)
        radio1 = Gtk.RadioButton.new_with_label(None, "Default port (27016)")
        radio2 = Gtk.RadioButton.new_from_widget(radio1)
        radio2.set_label("Custom port")
        self.entry = Gtk.Entry(placeholder_text="Query port")
        self.button = Gtk.Button(label="Scan")
        radio1.connect("toggled", self._on_radio_toggled)
        #hbox.pack_start(label, NO_EXPAND, NO_FILL, NO_PADDING)
        hbox.pack_start(radio1, NO_EXPAND, NO_FILL, NO_PADDING)
        hbox.pack_start(radio2, NO_EXPAND, NO_FILL, NO_PADDING)
        hbox.pack_start(self.entry, NO_EXPAND, NO_FILL, NO_PADDING)
        hbox.pack_start(self.button, NO_EXPAND, NO_FILL, NO_PADDING)
        self.entry.set_sensitive(False)
        self.button.set_sensitive(False)
        self.add(hbox)

    def _on_radio_toggled(self, button: Gtk.RadioButton) -> None:
        for el in self.entry, self.button:
            el.set_sensitive(not button.get_active())

class ConnectPanel(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        COLS = 1
        ROWS = 1
        self.classname = "invalid-entry"
        self.controller = controller

        self.entry = Gtk.Entry(
            placeholder_text=connect_panel.placeholder,
            hexpand=True,
            tooltip_text=connect_panel.entry_tooltip
        )
        self.entry.connect("key-press-event", self._on_entry_keypress)
        self.entry.connect("changed", self._on_text_changed)

        user_fav, user_ip = self.controller.get_favorite()

        server_name = f"{user_fav} ({user_ip})" if user_fav is not None else connect_panel.no_fav
        self.fav_label = Gtk.Label(label=server_name, track_visited_links=False, halign=Gtk.Align.START, hexpand=True)
        scrollable_label = Gtk.ScrolledWindow()
        scrollable_label.add(self.fav_label)

        self.fav_button = SteamConnectButton()
        self.fav_edit = Gtk.Button(label=connect_panel.edit)

        self.add_server = AddButton()
        self.conn_server = SteamConnectButton()

        self.conn_server.set_sensitive(False)
        self.add_server.set_sensitive(False)
        if server_name is None:
            self.fav_button.set_sensitive(False)

        add_label = BoldLabel(connect_panel.add_con)
        conn_label = BoldLabel(connect_panel.favorite)

        self.grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        #self.grid.attach(conn_label, 0, 0, COLS, ROWS)
        self.grid.attach(self.entry, 0, 0, COLS, ROWS)

        els = (
                #(scrollable_label, conn_label, Gtk.PositionType.RIGHT, 3, ROWS),
                #(self.fav_button, scrollable_label, Gtk.PositionType.RIGHT, COLS, ROWS),
                #(add_label, conn_label, Gtk.PositionType.BOTTOM, COLS, ROWS),
                #(self.entry, scrollable_label, Gtk.PositionType.BOTTOM, COLS, ROWS),
            (self.add_server, self.entry, Gtk.PositionType.RIGHT, COLS, ROWS),
            (self.conn_server, self.add_server, Gtk.PositionType.RIGHT, COLS, ROWS),
        )

        for el, sibling, pos, h_span, v_span in els:
            self.grid.attach_next_to(el, sibling, pos, h_span, v_span)

        self.lan = LanPanel(self.controller)
        self.add(self.lan)

        label = BoldLabel("Favorite server")
        frame = Gtk.Frame(margin_top=10, margin_bottom=5, label_widget=label)
        b = ClipboardButton()
        b.set_tooltip_text("Copy IP to clipboard")
        b.connect("clicked", self._on_ip_clicked, user_ip)
        grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        grid.attach(scrollable_label, 0, 0, 3, ROWS)
        grid.attach_next_to(b, scrollable_label, Gtk.PositionType.RIGHT, COLS, ROWS)
        grid.attach_next_to(self.fav_button, b, Gtk.PositionType.RIGHT, COLS, ROWS)
        frame.add(grid)
        self.add(frame)

        label = BoldLabel("Connect")
        frame = Gtk.Frame(margin_top=10, margin_bottom=5, label_widget=label)
        frame.add(self.grid)
        self.add(frame)

        self.lan.set_visible(False)

    def _on_ip_clicked(self, button: Gtk.Button, ip: str) -> None:
        self.controller.copy_clipboard(ip)

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

    def set_fav_label(self, text: str) -> None:
        # TODO: called by controller when changing fav
        # TODO: href logic
        self.fav_label.set_text(text)

    def _on_entry_keypress(self, entry: Gtk.Entry, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            # NOTE: unselect text
            entry.select_region(0, 0)
            self.controller.grab_active_treeview()
