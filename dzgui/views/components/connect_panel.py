from dzgui.views.components.web_button import WebButton

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk # noqa E402


class ConnectPanel(Gtk.Frame):
    def __init__(self) -> None:
        super().__init__(margin_top=10, margin_bottom=5)

        self.label = Gtk.Label(label="Add/connect")
        self.label2 = Gtk.Label(label="Favorite server")

        # TODO: embold function
        #self.label2.set_markup("<b>Favorite server</b>")

        self.label2.set_markup("<b>Favorite server</b>")
        self.entry1 = Gtk.Entry(placeholder_text="Enter IP or Battlemetrics ID", hexpand=False)
        self.entry2 = Gtk.Entry()
        self.fav = Gtk.Label(label="MY favorite server very long title")
        self.favedit = Gtk.Button("Edit")
        self.edit = WebButton(label="EDIT")
        self.favbutton = Gtk.Button(label="Connect")

        # TODO: dedent
        long = """IP: Format as IP:Query port, e.g.\n192.168.1.1:27016\n
        Battlemetrics: numeric server ID
        """

        # TODO: add tooltips to all buttons
        self.entry1.set_tooltip_text(long)

        self.con = Gtk.Button(label="Connect")
        self.addb = Gtk.Button(label="Add")

        self.grid = Gtk.Grid(margin=10, vexpand=False, column_spacing=15, row_spacing=5)
        self.grid.attach(self.label2, 0, 0, 3, 1)
        button = Gtk.Button(label="Connect")
        self.grid.attach_next_to(self.fav, self.label2, Gtk.PositionType.RIGHT, 3, 1)
        self.grid.attach_next_to(self.favbutton, self.fav, Gtk.PositionType.RIGHT, 3, 1)
        self.grid.attach_next_to(self.label, self.label2, Gtk.PositionType.BOTTOM, 3, 1)
        self.grid.attach_next_to(self.entry1, self.label, Gtk.PositionType.RIGHT, 3, 1)
        self.grid.attach_next_to(self.addb, self.entry1, Gtk.PositionType.RIGHT, 3, 1)
        self.grid.attach_next_to(self.con, self.addb, Gtk.PositionType.RIGHT, 3, 1)

        self.add(self.grid)
