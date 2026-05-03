from dzgui.model.model_factory import ModelFactory
from dzgui.views.mixins.cursor_mixin import CursorMixin
from dzgui.views.trees.tree_base import TreeView
from dzgui.util import strings

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class ServerModTree(TreeView):  # type: ignore
    def __init__(self, controller: "Controller") -> None:
        super().__init__(controller)

        # self.view = TreeView(controller)
        self.mod_store = ModelFactory().make_server_mod_store()

        self.set_fixed_height_mode(True)
        self.set_headers_visible(True)
        self.set_model(self.mod_store)

        # self.scrollable_tree = Gtk.ScrolledWindow()
        # self.scrollable_tree.add(self.view)
        # self.scrollable_tree.set_size_request(700, 400)

        # self.view.connect("row-activated", self._on_row_activated)

        for i, column_title in enumerate(strings.server_mod_cols):
            renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            self.append_column(column)
            column.set_sort_column_id(i)
            # FIXME: do not recycle generic string vars
            match column_title:
                case strings.mod:
                    column.set_fixed_width(350)
                case strings._id:
                    column.set_fixed_width(200)
                case _:
                    pass

        # mod_count = len(mods)
        # self._set_footer(mod_count)

    def populate(self, mods: list[list[str]]) -> None:
        for mod in mods:
            self.mod_store.append(mod)
