from typing import TYPE_CHECKING

from dzgui.const.enum import RowType, Preferences
from dzgui.util import strings

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

class Statusbar(Gtk.Statusbar):
    def __init__(self, controller: "Controller") -> None:
        super().__init__()

        self.controller = controller
        self.controller.register_widget("statusbar", self)

        help_text = strings.statusbar_helptext
        self.set_text(help_text)

        version = self.controller.get_prefs().version
        self.status_right_label = Gtk.Label(label=version)
        self.add(self.status_right_label)

        self.players = ""

    def get_text(self) -> str:
        area = self.get_message_area()
        label = area.get_children()[0]
        return label.get_text()

    def set_text(self, string: str) -> None:
        if string is None:
            return
        meta = self.get_context_id("Statusbar")
        self.push(meta, string)

    def refresh(self, row: "RowType") -> None:
        if row is None:
            formatted = ""
        else:
            formatted = self.format_metadata(row)
        self.set_text(formatted)

    def append_distance(self, dist: str) -> None:
        # TODO: process strings in controller
        if dist == strings.unknown:
            dist = f"| Distance: {dist}"
        else:
            dist = f"| Distance: {dist}"
        self.set_text(self.players + dist)

    def format_metadata(self, row: "RowType") -> str:
        prefix = row.dict["tooltip"]

        if row == RowType.QUICK_CONNECT or row == RowType.CHNG_FAV:
            label = self.controller.query_config(Preferences.FAV_LBL)
            if len(label) < 1:
                label = "unset"
            return f"{prefix} ({label})"
        else:
            return prefix
