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
        "distcalc_ended": (GObject.SignalFlags.RUN_FIRST, None, (object, str)),
        "server_row_changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self.controller = controller
        self.controller.register_widget("statusbar", self)

        help_text = strings.statusbar_helptext

        self.playercount = ""
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

        self.connect("server_row_changed", self._on_server_row_changed)
        self.connect("server_page_changed", self._on_server_page_changed)
        self.connect("notebook_page_changed", self._on_notebook_page_changed)
        self.connect("notebook_page_returned", self._on_notebook_page_returned)
        self.connect("distcalc_ended", self._on_distcalc_ended)

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
            case NotebookPage.SERVERS:
                pass

        self.set_by_context(context, bar)

    def _on_notebook_page_returned(
        self, statusbar: Self, prior_context: NotebookPage
    ) -> None:
        self.pop(prior_context)

    def _on_server_row_changed(self, statusbar: Self) -> None:
        self.spinner.start()

    def _on_distcalc_ended(
        self,
        statusbar: Self,
        dist: Union[str, None],
        context: Union["ServerTab", NotebookPage],
    ) -> None:
        self.spinner.stop()
        if dist is None:
            self.set_by_context(context, self.playercount)
        else:
            pretty = f"{self.playercount} | Distance: {dist}"
            self.set_by_context(context, pretty)

    def _on_server_page_changed(self, statusbar: Self, context: "ServerTab") -> None:
        c = self.controller.get_player_count()
        self.playercount = c

        self.set_by_context(context, c)
        tree = self.controller.get_active_treeview()
        tree.emit("distcalc_started")

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
