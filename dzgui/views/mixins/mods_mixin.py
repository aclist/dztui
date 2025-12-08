from dzgui.views.trees.tree_base import TreeView

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402


class ModsMixin:
    def _on_mod_row_activated(self,
            tree: TreeView,
            path: Gtk.TreePath,
            column: Gtk.TreeViewColumn
        ) -> None:

        path = self.get_focused_row_path()
        self.controller.open_mod_page(path)
