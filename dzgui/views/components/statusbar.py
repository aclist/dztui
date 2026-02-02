from typing import Self, Union, TYPE_CHECKING

from dzgui.const.enum import NotebookPage, ServerTab

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject  # noqa E402

if TYPE_CHECKING:
    from dzgui.const.enum import ServerTab
    from dzgui.controllers.mc import Controller
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

        version = self.controller.get_prefs().version
        self.status_right_label = Gtk.Label(
            label=version, hexpand=True, halign=Gtk.Align.END
        )

        self.attach(self.statusbar, 0, 0, 3, 1)
        self.attach_next_to(self.spinner, self.statusbar, Gtk.PositionType.RIGHT, 3, 1)
        self.attach_next_to(
            self.status_right_label, self.spinner, Gtk.PositionType.RIGHT, 3, 1
        )

        self.players = ""

        controller.mediator.menu.connect(
            "generic_treesel_changed", self._help_row_changed
        )
        controller.mediator.notebook.connect_after(
            "switch-page", self._on_notebook_page_changed
        )
        self.emitter.connect("distcalc_started", self._on_distcalc_started)
        # TODO:
        self.connect("distcalc_ended", self._on_distcalc_ended)

        self.connect("server_page_changed", self._on_server_page_changed)

    # TODO: move to emitter
    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object,))
    def server_page_changed(self, tab: ServerTab) -> None:
        pass

    @GObject.Signal(
        flags=GObject.SignalFlags.RUN_LAST,
        arg_types=(
            object,
            object,
        ),
    )
    def distcalc_ended(
        self, dist: Union[str, None], context: Union["ServerTab", NotebookPage]
    ) -> None:
        pass

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

        match enum:
            case NotebookPage.MODS:
                bar = self.controller.format_mod_statusbar()
            case NotebookPage.HELP:
                bar = self.controller.get_help_row()
            case NotebookPage.SERVERS:
                self.emit("server_page_changed", ServerTab.BROWSER)
                return

        self.set_by_context(enum, bar)

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
            pretty = self.append_distance(dist)
            self.set_by_context(context, pretty)

    def append_distance(self, dist: str) -> str:
        return f"{self.playercount} | Distance: {dist}"

    def _on_server_page_changed(self, statusbar: Self, context: "ServerTab") -> None:
        count = self.controller.get_player_count()
        self.playercount = count

        self.set_by_context(context, count)
        tree = self.controller.get_active_treeview()
        # TODO: emit page change signal on emitter, treeview catches signal and calls distcalc
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

    def _help_row_changed(self, tree: "TreeView", sel: Gtk.TreeSelection) -> None:
        row = tree.get_value_at_index(1)
        if self.controller.loaded is False:
            return
        tooltip = row.dict["tooltip"]
        self.set_by_context(NotebookPage.HELP, tooltip)
