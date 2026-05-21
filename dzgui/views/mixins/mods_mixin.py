from dzgui.views.trees.tree_base import TreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402


class ModsMixin:
    def _on_mod_row_activated(
        self, tree: TreeView, path: Gtk.TreePath, column: Gtk.TreeViewColumn
    ) -> None:

        mod = self.get_value_at_index(2)  # type: ignore
        self.controller.open_workshop_page(mod)  # type: ignore
