import logging
from typing import TYPE_CHECKING

from dzgui.const.constants import APP_NAME
from dzgui.const.enum import RowType, NotebookPage
from dzgui.model.model_factory import ModelFactory
from dzgui.util.open_links import open_link_by_rowtype
from dzgui.views.trees.tree_base import TreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

logger = logging.getLogger(APP_NAME)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class MenuTreeView(TreeView):
    """
    Simple Gtk.ListStore representation of main
    menu options
    """

    def __init__(self, controller: "Controller") -> None:
        super().__init__(controller)

        self.controller = controller

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Main menu", renderer, text=0)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.append_column(column)

        help_store = ModelFactory().make_help_store()
        self.set_model(help_store)

        self.selected_row = self.get_selection()

        self.controller.register_widget("menu", self)

        self.set_row_separator_func(self._separate)
        self.connect("generic_row_activated", self._parent_row_activated)

    def _parent_row_activated(
        self, tree: TreeView, path: Gtk.TreePath, column: Gtk.TreeViewColumn
    ) -> None:
        row_type = self.get_value_at_index(1)

        match row_type:
            case RowType.THANKS:
                self.controller.open_page(NotebookPage.THANKS)
            case RowType.SHOW_LOG:
                self.controller.populate_log()
            case RowType.CHANGELOG:
                self.controller.open_page(NotebookPage.CHANGELOG)
            case RowType.DUMP_LOG:
                self.controller.dump_diagnostics()
                pass

        docs = [
            RowType.DOCS,
            RowType.DOCS_FALLBACK,
            RowType.BUGS,
            RowType.FORUM,
            RowType.SPONSOR,
        ]
        if row_type in docs:
            open_link_by_rowtype(row_type)

    def get_row_enum(self) -> str:
        # NOTE: col 1 contains a RowType enum
        model = self.get_model()
        _iter = self.get_focused_row_iter()
        rowtype = model.get_value(_iter, 1)
        return str(rowtype.dict["tooltip"])
