import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class Icon(Gtk.Image):
    def __init__(self, name: str, l_margin=0):
        super().__init__(icon_name=name,
            icon_size=Gtk.IconSize.BUTTON,
            margin_start=l_margin
        )
