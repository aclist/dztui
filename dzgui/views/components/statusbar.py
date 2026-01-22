from warnings import deprecated
from typing import Self, Union, TYPE_CHECKING

from dzgui.const.enum import NotebookPage, RowType
from dzgui.util import strings

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject  # noqa E402

if TYPE_CHECKING:
    from dzgui.const.enum import ServerTab
    from dzgui.controllers.mc import Controller


class Statusbar(Gtk.Grid):
    __gsignals__ = {
        "server_page_changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "notebook_page_changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "notebook_page_returned": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

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
        self.status_right_label = Gtk.Label(
            label=version, hexpand=True, halign=Gtk.Align.END
        )

        self.attach(self.statusbar, 0, 0, 3, 1)
        self.attach_next_to(self.spinner, self.statusbar, Gtk.PositionType.RIGHT, 3, 1)
        self.attach_next_to(
            self.status_right_label, self.spinner, Gtk.PositionType.RIGHT, 3, 1
        )

        self.set_text(help_text, "Help")
        self.players = ""

        self.connect("server_page_changed", self._on_server_page_changed)
        self.connect("notebook_page_changed", self._on_notebook_page_changed)
        self.connect("notebook_page_returned", self._on_notebook_page_returned)

    def _on_notebook_page_changed(
        self, statusbar: Self, context: "NotebookPage"
    ) -> None:
        status = context.dict["statusbar"]
        bar = ""
        if status is False:
            self.set_by_context(context, "")
            return

        match context:
            case NotebookPage.MODS:
                bar = self.controller.format_mod_statusbar()
            case NotebookPage.HELP:
                bar = self.controller.get_help_text()
        self.set_by_context(context, bar)

    def _on_notebook_page_returned(
        self, statusbar: Self, prior_context: "NotebookPage"
    ) -> None:
        self.pop(prior_context)

    def _on_server_page_changed(self, statusbar: Self, context: "ServerTab") -> None:
        self.pop(context)

    def start_spinner(self) -> None:
        self.spinner.start()

    def stop_spinner(self) -> None:
        self.spinner.stop()

    def pop(self, context: Union["ServerTab", "NotebookPage"]) -> None:
        cid = self.statusbar.get_context_id(str(context))
        self.statusbar.pop(cid)

    def get_text(self) -> str:
        area = self.statusbar.get_message_area()
        label = area.get_children()[0]
        return label.get_text()

    def set_by_context(
        self, context: Union[NotebookPage, "ServerTab"], string: str
    ) -> None:
        meta = self.statusbar.get_context_id(str(context))
        self.statusbar.push(meta, string)
        self.set_cache(string)

    def get_cache(self) -> str:
        return self.cache

    def set_cache(self, string: str) -> None:
        self.cache = string

    def set_text(self, string: str, context: str) -> None:
        meta = self.statusbar.get_context_id(context)
        self.statusbar.push(meta, string)
        self.set_cache(string)

    def refresh(self, row: "RowType") -> None:
        if row is None:
            formatted = ""
        else:
            formatted = self.format_metadata(row)
        self.set_text(formatted, "Help")

    @deprecated("use controller")
    def format_metadata(self, row: "RowType") -> str:
        prefix = row.dict["tooltip"]

        if row == RowType.QUICK_CONNECT or row == RowType.CHNG_FAV:
            label = self.controller.query_config(Preferences.FAV_LBL)
            if len(label) < 1:
                label = "unset"
            return f"{prefix} ({label})"
        else:
            return prefix
