from typing import Self, Union, TYPE_CHECKING
from warnings import deprecated

from dzgui.const.enum import NotebookPage, ServerTab
from dzgui.util.strings import esc_to_return, question_to_return
from dzgui.views.components.buttons import LoggerAlertsButton

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject  # noqa E402

if TYPE_CHECKING:
    from dzgui.const.enum import ServerTab
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter
    from dzgui.views.trees.tree_base import TreeView
    from dzgui.views.base import Notebook


class Statusbar(Gtk.Grid):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self.controller = controller
        self.controller.register_widget("statusbar", self)
        self.emitter = controller.get_emitter()

        self.playercount = ""
        self.statusbar = Gtk.Statusbar()

        self.spinner = Gtk.Spinner()

        self.attach(self.statusbar, 0, 0, 3, 1)
        self.attach_next_to(self.spinner, self.statusbar, Gtk.PositionType.RIGHT, 3, 1)

        # TODO: pack version event box in right panel into hbox with update button
        # TODO: spawns a modal or just jumps right to install page
        # from dzgui.views.components.buttons import IconTextButton
        # b = IconTextButton("dialog-information-symbolic", label="Updates available")
        # b.set_halign(Gtk.Align.END)
        # b.set_hexpand(True)
        # self.attach_next_to(b, self.spinner, Gtk.PositionType.RIGHT, 3, 1)

        self.players = ""

        controller.get_menu().connect("generic_treesel_changed", self._help_row_changed)
        controller.get_notebook().connect_after(
            "switch-page", self._on_notebook_page_changed
        )

        self.emitter.connect("distcalc_started", self._on_distcalc_started)
        self.emitter.connect("distcalc_ended", self._on_distcalc_ended)
        self.emitter.connect("servers_loaded", self._on_servers_loaded)
        self.emitter.connect("mods_updated", self._on_mods_updated)

    def _on_alerts_clicked(self, button: LoggerAlertsButton) -> None:
        self.controller.populate_log()

    def _on_mods_updated(self, emitter: "Emitter", msg: str, mods: int) -> None:
        self.set_by_context(NotebookPage.MODS, msg)

    def _on_notebook_page_changed(
        self, notebook: "Notebook", child: Gtk.Widget, index: int
    ) -> None:
        if self.controller.loaded is False:
            return

        enum = notebook.get_page_by_enum()
        show_statusbar = enum.dict["statusbar"]

        if show_statusbar is False:
            self.set_by_context(enum, "")
            return

        if enum in (
            NotebookPage.THANKS,
            NotebookPage.CHANGELOG,
            NotebookPage.LOG,
            NotebookPage.CONNECTION,
        ):
            self.set_by_context(enum, esc_to_return)
            return

        match enum:
            case NotebookPage.HELP:
                bar = self.controller.get_help_row()
            case NotebookPage.KEYS:
                bar = question_to_return
            case _:
                return

        self.set_by_context(enum, bar)

    # TODO: unused
    def _on_notebook_page_returned(
        self, statusbar: Self, prior_context: NotebookPage
    ) -> None:
        self.pop(prior_context)

    def _on_server_row_changed(self, statusbar: Self) -> None:
        self.spinner.start()

    def _on_distcalc_started(self, emitter: "Emitter") -> None:
        self.spinner.start()

    def _on_distcalc_ended(
        self,
        statusbar: Self,
        dist: Union[str, None],
        context: Union["ServerTab", NotebookPage],
    ) -> None:
        self.spinner.stop()
        # TODO: CalcDist is being called when table is not loaded
        if dist is None:
            self.set_by_context(context, "")
        else:
            pretty = self.append_distance(dist)
            self.set_by_context(context, pretty)

    def append_distance(self, dist: str) -> str:
        return f"{self.playercount} Distance: {dist}"

    def _on_servers_loaded(self, statusbar: Self, context: "ServerTab") -> None:
        count = self.controller.get_player_count()
        self.playercount = count

        self.set_by_context(context, count)
        self.emitter.emit("statusbar_loaded")

    def pop(self, context: Union["ServerTab", "NotebookPage"]) -> None:
        cid = self.statusbar.get_context_id(str(context))
        self.statusbar.pop(cid)

    @deprecated("currently unused")
    # def get_text(self) -> str:
    #    area = self.statusbar.get_message_area()
    #    label = area.get_children()[0]
    #    return str(label.get_text())

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

    def set_text(self, string: str, context: str) -> int:
        meta = self.statusbar.get_context_id(context)
        self.statusbar.push(meta, string)
        self.set_cache(string)
        return meta

    def _help_row_changed(self, tree: "TreeView", sel: Gtk.TreeSelection) -> None:
        row = tree.get_value_at_index(1)
        if self.controller.loaded is False:
            return
        tooltip = row.dict["tooltip"]
        self.set_by_context(NotebookPage.HELP, tooltip)
