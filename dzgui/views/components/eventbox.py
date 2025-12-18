from dzgui.const.constants import HELP_BUBBLE

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa E402

class InfoEventBox(Gtk.EventBox):
    def __init__(self, text: str, parent: Gtk.Widget):
        super().__init__(margin_start=10)

        self.parent = parent
        self.text = text

        self.icon = Gtk.Image.new_from_icon_name(
            HELP_BUBBLE, Gtk.IconSize.LARGE_TOOLBAR
        )
        self.icon.set_opacity(0.8)
        box = Gtk.Box()
        box.add(self.icon)

        self.connect("enter-notify-event", self._on_enter_tooltip)
        self.connect("leave-notify-event", self._on_leave_tooltip)
        self.add(box)

    def _on_enter_tooltip(
        self, eventbox: Gtk.EventBox, eventcrossing: Gdk.EventCrossing
    ) -> None:
        self.icon.set_opacity(1)
        self.parent.controller.set_statusbar(self.text)

    def _on_leave_tooltip(
        self, eventbox: Gtk.EventBox, eventcrossing: Gdk.EventCrossing
    ) -> None:
        self.icon.set_opacity(0.8)
        self.parent.controller.set_statusbar("")

    def set_text(self, text: str) -> None:
        self.text = text
