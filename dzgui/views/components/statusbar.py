from typing import TYPE_CHECKING

from dzgui.const.enum import RowType, Preferences
from dzgui.util import strings

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

class Statusbar(Gtk.Grid):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self.controller = controller
        self.controller.register_widget("statusbar", self)

        help_text = strings.statusbar_helptext

        self.context: int
        self.statusbar = Gtk.Statusbar()

        self.spinner = Gtk.Spinner()
        self.spinner.start()

        version = self.controller.get_prefs().version
        self.status_right_label = Gtk.Label(label=version, hexpand=True, halign=Gtk.Align.END)

        self.attach(self.statusbar, 0, 0, 3, 1)
        self.attach_next_to(self.spinner, self.statusbar, Gtk.PositionType.RIGHT, 3, 1)
        self.attach_next_to(self.status_right_label, self.spinner, Gtk.PositionType.RIGHT, 3, 1)

        self.set_text(help_text, "Help")
        self.players = ""

    def get_text(self) -> str:
        area = self.statusbar.get_message_area()
        label = area.get_children()[0]
        return label.get_text()

    def set_text(self, string: str, context: str) -> None:
        # if string is None:
        #     return
        meta = self.statusbar.get_context_id(context)
        #tv = self.controller.get_active_treeview()
        #cur_context = tv.get_enum()
        #cid = self.get_context_by_enum(cur_context)
        #if cid != meta:
        #    print("requested: ", meta)
        #    print("current: ", cid)
        #    return
        # TODO: substacks
        # get_context_id(ServerTab)
        self.statusbar.push(meta, string)
        #self.set_context(meta)


    # TODO: type checking
    # def get_context_by_enum(self, context: "ServerTab") -> int:
    #     cid = self.statusbar.get_context_id(str(context))
    #     # TODO: substacks
    #     return cid
    #
    # def get_context(self) -> int:
    #     return self.context
    #
    # def set_context(self, context: int) -> None:
    #     self.context = context

    def refresh(self, row: "RowType") -> None:
        if row is None:
            formatted = ""
        else:
            formatted = self.format_metadata(row)
        self.set_text(formatted, "Help")

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
