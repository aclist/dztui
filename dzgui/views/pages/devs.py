from dataclasses import fields
from typing import Self, Union, TYPE_CHECKING

from dzgui.const.enum import NotebookPage
from dzgui.util.css import add_class
from dzgui.util.strings import developers
from dzgui.views.components.labels import BoldLabel
from dzgui.views.trees.tree_base import TreeView

import gi  # noqa E402

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.config.userprefs import UserPrefs
    from dzgui.config.xdg import Xdg


class Developers(Gtk.ScrolledWindow):
    """
    Shows TreeViews displaying contents of parsed XDG paths
    and user preferences
    """

    def __init__(self, controller: "Controller") -> None:
        super().__init__()

        self.controller = controller
        self.box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, margin_start=10, margin_end=10
        )

        heading = Gtk.Label(label=developers.header)
        heading.set_halign(Gtk.Align.CENTER)
        add_class(heading, "page-heading")

        back_button = Gtk.Button(label="Back", halign=Gtk.Align.START)
        back_button.connect("clicked", self._on_back_clicked)

        paths_label = BoldLabel(developers.paths_label)
        prefs_label = BoldLabel(developers.prefs_label)

        prefs = self.controller.get_prefs()
        paths_tree = self._make_tree(prefs.paths)
        self.prefs_tree = self._make_tree(prefs)
        trees_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        path = Gtk.TreePath.new_from_indices([0])
        paths_tree.set_cursor(path)
        self.prefs_tree.set_cursor(path)

        for el in [paths_label, paths_tree, prefs_label, self.prefs_tree]:
            trees_box.add(el)

        for el in [heading, back_button, trees_box]:
            self.box.add(el)

        self.add(self.box)
        self.connect("map", self._on_map)

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        self.controller.open_page(NotebookPage.OPTIONS)

    def _make_tree(self, prefs: Union["Xdg", "UserPrefs"]) -> Gtk.TreeView:
        tree = TreeView(self.controller)
        renderer = Gtk.CellRendererText()
        for i, col in enumerate(developers.columns):
            column = Gtk.TreeViewColumn(col, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            tree.append_column(column)

        store = self._make_store(prefs)
        tree.set_model(store)
        # store = Gtk.ListStore(str, str)
        # for field in fields(prefs):
        #    if field.name == "paths":
        #        continue
        #    k, v = field.name, getattr(prefs, field.name)
        #    store.append((k, str(v)))

        return tree

    def _make_store(self, prefs: Union["Xdg", "UserPrefs"]) -> Gtk.ListStore:
        store = Gtk.ListStore(str, str)
        for field in fields(prefs):
            if field.name == "paths":
                continue
            k, v = field.name, getattr(prefs, field.name)
            store.append((k, str(v)))
        return store

    def _on_map(self, widget: Self) -> None:
        prefs = self.controller.get_prefs()
        store = self._make_store(prefs)
        self.prefs_tree.set_model(store)

    def grab_content_area(self) -> None:
        return
