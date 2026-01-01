from typing import TYPE_CHECKING

from dzgui.util.strings import connect_panel
from dzgui.views.components.buttons import WebButton
from dzgui.views.components.labels import BoldLabel

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

class ConnectPanel(Gtk.Frame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        COLS = 1
        ROWS = 1
        self.controller = controller

        self.entry = Gtk.Entry(
            placeholder_text=connect_panel.placeholder,
            hexpand=True,
            tooltip_text=connect_panel.entry_tooltip
        )

        # TODO: get ip as well?
        user_fav = self.controller.get_favorite_label()

        server_name = user_fav if user_fav is not None else connect_panel.no_fav
        scrollable_label = Gtk.ScrolledWindow()
        label = Gtk.Label(label=server_name, halign=Gtk.Align.START)
        scrollable_label.add(label)

        self.fav_button = Gtk.Button(label=connect_panel.connect,
            tooltip_text=connect_panel.connect_tooltip
        )
        self.fav_edit = Gtk.Button(label=connect_panel.edit)
        self.edit_server = WebButton(label="EDIT")

        self.conn_server= Gtk.Button(label=connect_panel.connect,
            tooltip_text=connect_panel.connect_tooltip
        )
        self.add_server = Gtk.Button(label=connect_panel.add,
            tooltip_text=connect_panel.add_tooltip
        )

        self.conn_server.set_sensitive(False)
        self.add_server.set_sensitive(False)
        if server_name is None:
            self.fav_button.set_sensitive(False)

        add_label = BoldLabel(connect_panel.add_con)
        conn_label = BoldLabel(connect_panel.favorite)

        self.grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        self.grid.attach(conn_label, 0, 0, COLS, ROWS)

        els = (
            (scrollable_label, conn_label, Gtk.PositionType.RIGHT, 3, ROWS),
            (self.fav_button, scrollable_label, Gtk.PositionType.RIGHT, COLS, ROWS),
            (add_label, conn_label, Gtk.PositionType.BOTTOM, COLS, ROWS),
            (self.entry, scrollable_label, Gtk.PositionType.BOTTOM, COLS, ROWS),
            (self.add_server, self.fav_button, Gtk.PositionType.BOTTOM, COLS, ROWS),
            (self.conn_server, self.add_server, Gtk.PositionType.RIGHT, COLS, ROWS),
        )

        for el, sibling, pos, h_span, v_span in els:
            self.grid.attach_next_to(el, sibling, pos, h_span, v_span)

        self.add(self.grid)
