from typing import Self
from dzgui.util import css

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa


# TODO: subclass Gtk.Frame directly
class HeadingFrame(Gtk.Box):
    def __init__(self, heading: str = "") -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.label = Gtk.Label(label=heading)
        self.label.set_halign(Gtk.Align.START)
        css.add_class(self.label, "settings-subheading")

        self.frame = Gtk.Frame(hexpand=True)
        self.frame.set_label_widget(self.label)

        self.add(self.frame)

    @classmethod
    def new_with_widget_and_label(cls, widget: Gtk.Widget, label: str) -> Self:
        n = cls()
        n.frame.add(widget)
        n.label.set_label(label)
        return n
