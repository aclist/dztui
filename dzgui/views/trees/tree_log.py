import logging

from typing import TYPE_CHECKING

from dzgui.const.enum import ContextMenuGroup
from dzgui.model.model_factory import ModelFactory
from dzgui.util import strings
from dzgui.views.trees.tree_base import TreeView
from dzgui.views.mixins.context_mixin import ContextMixin

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

logger = logging.getLogger(__name__)


class LogTreeView(ContextMixin, TreeView):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(controller, menu=ContextMenuGroup.LOG)

        self.controller = controller
        self.controller.register_widget("logtreeview", self)

        self.set_headers_visible(True)
        self.set_fixed_height_mode(True)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        self.set_model(None)

        for i, column_title in enumerate(strings.log_cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_resizable(True)
            column.set_sort_column_id(i)
            self.append_column(column)

        self.connect("button-press-event", self._on_log_buttonpress)
        self.connect("key-press-event", self._on_log_keypress)

    def populate_log(self, filepath: str) -> None:
        model = ModelFactory().new_model_from_logfile(filepath)
        self.set_model(model)
        self.set_cursor(0)

    def _on_log_buttonpress(self, widget: Gtk.Widget, event: Gdk.EventButton) -> None:
        if event.button == Gdk.BUTTON_SECONDARY:
            self.present_menu(widget, event)
            return True

    def _on_log_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        self.present_menu(widget, event)
