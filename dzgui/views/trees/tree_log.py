import logging

from typing import Any, TYPE_CHECKING

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
        self.set_vexpand(True)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        self.set_model(None)
        # self.filter: Gtk.TreeModelFilter

        # TODO: strings
        # NOTE: default filters that should be shown on startup
        self.filters = ["CRITICAL", "WARNING"]
        for i, column_title in enumerate(strings.log_cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_resizable(True)
            column.set_sort_column_id(i)
            if i == 1:
                column.set_fixed_width(100)
            self.append_column(column)

        self.connect("button-press-event", self._on_log_buttonpress)
        self.connect("key-press-event", self._on_log_keypress)

    def populate_log(self, filepath: str) -> None:
        model = ModelFactory().new_model_from_logfile(filepath)
        _filter = model.filter_new()
        _filter.set_visible_func(self._filter_rows)
        sortable = Gtk.TreeModelSort(_filter)
        self.set_model(sortable)
        _filter.refilter()
        self.set_cursor(0)

    def toggle_filter(self, _filter: str) -> None:
        if _filter in self.filters:
            self.filters.remove(_filter)
        else:
            self.filters.append(_filter)
        # NOTE: unwrap TreeModelSort and TreeModelFilter
        self.get_model().get_model().refilter()

    def _filter_rows(
        self, model: Gtk.ListStore, _iter: Gtk.TreeIter, data: Any
    ) -> None:
        if len(self.filters) < 1:
            return False
        return model[_iter][1] in self.filters

    def _on_log_buttonpress(self, widget: Gtk.Widget, event: Gdk.EventButton) -> None:
        if event.button == Gdk.BUTTON_SECONDARY:
            self.present_menu(widget, event)
            return True

    def _on_log_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        self.present_menu(widget, event)
