import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk # noqa E402

from dzgui.views.components.web_button import WebButton

class ConnectPanel(Gtk.Grid):
    def __init__(self) -> None:
        super().__init__(vexpand=False, margin=20)

        self.label = Gtk.Label(label="Connect by IP/ID")
        self.label2 = Gtk.Label(label="Favorite server")
        # TODO: embold function
        self.label2.set_markup("<b>Favorite server</b>")
        sep = Gtk.Separator()
        self.entry1 = Gtk.Entry(placeholder_text="Enter IP or Battlemetrics ID", hexpand=False)
        self.entry2 = Gtk.Entry()
        self.fav = Gtk.Label("MY favorite server")
        self.favedit = Gtk.Button("Edit")
        self.edit = WebButton(label="EDIT")
        self.favbutton = Gtk.Button(label="Connect")

        self.attach(self.label, 0, 0, 3, 1)
        button = Gtk.Button(label="Connect")
        self.attach_next_to(self.entry1, self.label, Gtk.PositionType.BOTTOM, 3, 1)
        self.attach_next_to(button, self.entry1, Gtk.PositionType.RIGHT, 3, 1)

        self.attach_next_to(sep, self.entry1, Gtk.PositionType.BOTTOM, 3, 1)
        self.attach_next_to(self.label2, sep, Gtk.PositionType.BOTTOM, 3, 1)
        self.attach_next_to(self.fav, self.label2, Gtk.PositionType.BOTTOM, 3, 1)
        self.attach_next_to(self.edit, self.fav, Gtk.PositionType.RIGHT, 3, 1)
        self.attach_next_to(self.favbutton, self.edit, Gtk.PositionType.RIGHT, 3, 1)
