from dzgui.util import strings, css, open_links

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa

class HeadingFrame(Gtk.Box):
    def __init__(self, widget: Gtk.Widget, heading: str) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        label = Gtk.Label(label=heading)
        label.set_halign(Gtk.Align.START)
        # TODO: rename selector
        css.add_class(label, "settings-subheading")

        frame = Gtk.Frame(hexpand=True)
        frame.add(widget)
        frame.set_label_widget(label)

        self.add(frame)
