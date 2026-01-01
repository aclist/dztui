import logging

from typing import TYPE_CHECKING

from dzgui.const.enum import ContextMenuGroup
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

        # TODO: maybe put this in init
        self.set_fixed_height_mode(True)
        self.set_headers_visible(True)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        model = self.controller.get_log_store()
        self.set_model(model)

        for i, column_title in enumerate(strings.log_cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(
                column_title, renderer, text=i
            )
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_resizable(True)
            column.set_sort_column_id(i)
            self.append_column(column)

        self.connect("button-press-event", self._on_log_button_press)
        self.connect("button-release-event", self._on_log_button_release)
        self.connect("key-press-event", self._on_log_keypress)

        self.s = self.get_selection().get_selected_rows()

    def _on_log_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        self.present_menu(widget, event)

    def _on_log_button_press(self,
        widget: Gtk.Widget,
        event: Gdk.EventButton
    ) -> bool:

        """
        Prevents context menu from deselecting rows
        """
        if event.button == 3:
            self.s = self.get_selection().get_selected_rows()
            return True
        return False

    def _on_log_button_release(self,
        widget: Gtk.Widget,
        event: Gdk.EventButton
    ) -> None:
        if event.button == 3:
            self.present_menu(widget, event)
            self.get_selection().unselect_all()
            for row in self.s[1]:
                self.get_selection().select_path(row)
