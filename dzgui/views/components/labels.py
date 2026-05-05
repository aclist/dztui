from dzgui.util.format import embolden

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402


class BoldLabel(Gtk.Label):
    def __init__(self, text: str):
        super().__init__()

        label = embolden(text)
        self.set_markup(label)


class LeftLabel(Gtk.Label):
    def __init__(self, text: str, tooltip: str = ""):
        super().__init__(
            label=text,
            halign=Gtk.Align.START,
        )
        self.set_tooltip_text(tooltip)


class IconLabel(Gtk.Box):
    def __init__(self, text: str, label: str) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_start=10
        )
        self.label = Gtk.Label(label=text, halign=Gtk.Align.START, margin_bottom=2)
        self.icon = Gtk.Image.new_from_icon_name(label, Gtk.IconSize.BUTTON)
        for el in self.icon, self.label:
            self.add(el)
