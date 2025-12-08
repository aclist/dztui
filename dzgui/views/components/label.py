import gi  # noqa E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class LeftLabel(Gtk.Label):
    def __init__(self, text: str, tooltip: str = ""):
        super().__init__(
            label=text,
            halign=Gtk.Align.START,
        )
        self.set_tooltip_text(tooltip)
        pass
