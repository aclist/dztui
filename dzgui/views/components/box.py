from typing import Sequence

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa


class GenericBox(Gtk.Box):
    def __init__(self, orientation: Gtk.Orientation, spacing: int = 0) -> None:
        super().__init__(orientation=orientation, spacing=spacing)

    def extend(self, els: Sequence[Gtk.Widget]) -> None:
        for el in els:
            self.add(el)


class HBox(GenericBox):
    def __init__(self, spacing: int = 0) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)


class VBox(GenericBox):
    def __init__(self, spacing: int = 0) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)


class ShortHBox(HBox):
    def __init__(self, widget: Gtk.Widget) -> None:
        super().__init__(spacing=5)

        self.set_halign(Gtk.Align.START)
        self.pack_start(widget, expand=False, fill=False, padding=0)
