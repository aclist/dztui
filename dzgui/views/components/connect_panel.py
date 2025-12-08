import gi  # noqa E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

class ConnectPanel(Gtk.Grid):
    def __init__(self):
        super().__init__()

        self.label = Gtk.Label(label="Connect by IP/ID")
        self.label2 = Gtk.Label(label="Save server by IP/ID")
        self.entry1 = Gtk.Entry()
        self.entry2 = Gtk.Entry()

        self.attach(self.label, 0, 0, 3, 1)
        self.attach_next_to(self.entry1, self.label, Gtk.PositionType.BOTTOM, 3, 1)
        self.attach_next_to(self.label2, self.entry1, Gtk.PositionType.BOTTOM, 3, 1)
        self.attach_next_to(self.entry2, self.label2, Gtk.PositionType.BOTTOM, 3, 1)
