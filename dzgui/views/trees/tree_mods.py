import logging
from typing import Any, TYPE_CHECKING

from dzgui.const.constants import APP_NAME, HEX_RED
from dzgui.const.enum import ContextMenuGroup
from dzgui.util import strings, localize
from dzgui.views.mixins.context_mixin import ContextMixin
from dzgui.views.mixins.mods_mixin import ModsMixin
from dzgui.views.trees.tree_base import TreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa


if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter

logger = logging.getLogger(APP_NAME)


class ModTreeView(ModsMixin, ContextMixin, TreeView):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(controller, menu=ContextMenuGroup.MOD)
        self.controller = controller
        emitter = self.controller.get_emitter()
        emitter.connect("mod_page_loaded", self._on_mod_page_loaded)
        emitter.connect("mods_highlighted", self._on_mods_highlighted)

        self.set_fixed_height_mode(True)
        self.set_headers_visible(True)

        self.set_model(None)

        for i, column_title in enumerate(strings.mod_cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_cell_data_func(renderer, self._format_color, func_data=None)
            if i == 4:
                column.set_cell_data_func(renderer, self._format_float, func_data=None)

            if column_title == "Mod":
                column.set_fixed_width(500)
            else:
                column.set_fixed_width(150)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_sort_column_id(i)
            if i != 4:
                self.append_column(column)

        self.selected_row = self.get_selection()
        self.selected_row.set_mode(Gtk.SelectionMode.MULTIPLE)

        self.connect("generic_row_activated", self._on_mod_row_activated)
        self.connect("generic_treesel_changed", self._parent_selection_changed)
        self.connect("button-press-event", self.present_menu)
        self.connect("key-press-event", self.present_menu)

    def _on_mods_highlighted(self, emitter: "Emitter") -> None:
        self.get_selection().unselect_all()

    # TODO: test loading with no mods
    def _on_mod_page_loaded(self, emitter: "Emitter") -> None:
        self.set_cursor(0)

    def get_selected_mod(self) -> str:
        path = self.get_focused_row_path()
        model = self.get_model()
        tree_iter = model.get_iter(path)
        mod = model.get(tree_iter, 2)[0]
        return mod
        # return mod, tree_iter

    # def _on_mods_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
    #     # TODO: multiselect
    #     # if event.keyval is Gdk.KEY_space:
    #     #    it = self.get_focused_row_iter()
    #     #    self.get_selection().select_iter(it)
    #     #    path = self.get_focused_row_path()
    #     #    self.set_cursor(path)
    #     #    return False
    #     self.present_menu(widget, event)

    # def _on_mods_button_press(self, widget: Gtk.Widget, event: Gdk.EventButton) -> None:
    #     if event.button == 3:
    #         self.present_menu(widget, event)

    def _parent_selection_changed(self, base_class: TreeView, sel: Gtk.TreeSelection):
        pass

    def _format_color(
        self,
        column: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererText,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        data: Any,
    ) -> Any:
        state = model[it][4]
        if state is True:
            cell.set_property("foreground", HEX_RED)
        else:
            cell.set_property("foreground", None)
        return

    def _format_float(
        self,
        column: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererText,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        data: Any,
    ) -> Any:
        val = model[it][3]
        formatted = localize.number(val)
        cell.set_property("text", formatted)
        return
