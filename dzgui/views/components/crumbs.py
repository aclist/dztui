from typing import TYPE_CHECKING

from dzgui.const.enum import NotebookPage
from dzgui.util.strings import label_main_menu, crumbs
from dzgui.util.format import embolden

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.views.base import Notebook


class Breadcrumbs(Gtk.Label):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(halign=Gtk.Align.START)

        crumbs = embolden(label_main_menu)
        self.set_markup(crumbs)

        notebook = controller.get_notebook()
        servers = controller.get_server_notebook()
        notebook.connect_after("switch-page", self._on_notebook_page_changed)
        servers.connect_after("switch-page", self._on_server_tab_changed)

    def _on_server_tab_changed(
        self, notebook: "Notebook", page: Gtk.Widget, index: int
    ) -> None:
        label = notebook.get_tab_label_text(page)
        self.set_server_crumbs(label)

    def _on_notebook_page_changed(
        self, notebook: "Notebook", page: Gtk.Widget, index: int
    ) -> None:
        enum = notebook.get_page_by_enum()
        if enum == NotebookPage.SERVERS:
            label = page.get_current_tab_text()
            self.set_server_crumbs(label)
        else:
            crumbs = enum.dict["crumbs"]
            self.set_crumbs(crumbs)

    def set_server_crumbs(self, suffix: str) -> None:
        self.set_crumbs(crumbs.default + suffix)

    def set_crumbs(self, crumbs: str) -> None:
        text = embolden(crumbs)
        self.set_markup(text)
