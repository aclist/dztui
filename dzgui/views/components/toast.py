from typing import Literal
from dzgui.util import css

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa E402


class Toast(Gtk.EventBox):
    def __init__(self) -> None:
        super().__init__()

        self.label = Gtk.Label(hexpand=True)
        self.box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        self.box.add(self.label)
        self.add(self.box)
        self.box.set_size_request(200, 100)

        css.add_class(self.box, "toast-label")

    def set_text(self, text: str) -> None:
        self.label.set_text(text)

    def set_text_and_fade(self, text: str) -> None:
        self.set_text(text)
        self.pop()
        self._defer_fade()

    def fade_out(self) -> bool:
        if self.get_opacity() == 0:
            self.set_visible(False)
            self.set_opacity(1)
            return False
        self.set_opacity(self.get_opacity() - 0.03)
        return True

    def pop(self) -> None:
        self.set_visible(True)

    def _defer_fade(self) -> Literal[False]:
        GLib.timeout_add(30, self.fade_out)
        return False
