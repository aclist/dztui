from dzgui.const.enum import ContextMenuGroup
from dzgui.model.model_factory import ModelFactory
from dzgui.strings import server_mods
from dzgui.views.mixins.context_mixin import ContextMixin
from dzgui.views.trees.tree_base import TreeView

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


class ServerModTreeView(ContextMixin, TreeView):  # type: ignore
    def __init__(self, controller: "Controller") -> None:
        super().__init__(controller, menu=ContextMenuGroup.SERVER_MOD)

        self.mod_store = ModelFactory().make_server_mod_store()

        self.set_fixed_height_mode(True)
        self.set_headers_visible(True)
        self.set_model(self.mod_store)

        self.connect("button-press-event", self.present_menu)
        self.connect("key-press-event", self.present_menu)
        self.connect("row-activated", self._on_row_activated)

        columns = [
            server_mods.mod,
            server_mods.mod_id,
            server_mods.up_to_date,
        ]
        for i, column_title in enumerate(columns):
            renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            self.append_column(column)
            column.set_sort_column_id(i)
            match column_title:
                case server_mods.mod:
                    column.set_fixed_width(350)
                case server_mods.mod_id:
                    column.set_fixed_width(200)
                case _:
                    pass

    def mark_mods_synched(self) -> None:
        for row in self.mod_store:
            row[2] = server_mods.checkmark

    # TODO: could be problematic if user downloads mods out of band
    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        path: Gtk.TreePath,
        col: Gtk.TreeViewColumn,
    ) -> None:
        mod = self.get_value_at_index(1)
        self.controller.open_workshop_page(mod)

    def get_selected_mod(self) -> str:
        path = self.get_focused_row_path()
        model = self.get_model()
        if model is None:
            raise AttributeError("Trying to call a method on a non-existent model")
        tree_iter = model.get_iter(path)
        mod = model.get_value(tree_iter, 1)
        return str(mod)

    def populate(self, mods: list[list[str]]) -> None:
        self.mod_store.clear()
        for mod in mods:
            self.mod_store.append(mod)
        path = Gtk.TreePath.new_from_indices([0])
        self.set_cursor(path)
