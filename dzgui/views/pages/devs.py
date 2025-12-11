import typing

import gi  # noqa E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from dataclasses import fields
from typing import Union, TYPE_CHECKING

from dzgui.const.enum import NotebookPage
from dzgui.util.strings import developers
from dzgui.util.css import add_class

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.config.userprefs import UserPrefs
    from dzgui.config.xdg import Xdg

class Developers(Gtk.Box):
    """
    Shows TreeViews displaying contents of parsed XDG paths
    and user preferences
    """
    def __init__(self, controller: "Controller") -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=10,
            margin_end=10,
        )

        self.controller = controller

        heading = Gtk.Label(label=developers.header)
        heading.set_halign(Gtk.Align.CENTER)
        add_class(heading, "page-heading")

        back_button = Gtk.Button(label="Back", halign=Gtk.Align.START)
        back_button.connect("clicked", self._on_back_clicked)
        paths_label = Gtk.Label()
        paths_label.set_markup(f"<b>{developers.paths_label}</b>")

        prefs_label = Gtk.Label()
        prefs_label.set_markup(f"<b>{developers.prefs_label}</b>")

        paths_tree = self._make_tree(self.controller.prefs.paths)
        prefs_tree = self._make_tree(self.controller.prefs)
        trees_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        path = Gtk.TreePath.new_from_indices([0])
        paths_tree.set_cursor(path)
        prefs_tree.set_cursor(path)

        for el in [
            paths_label,
            paths_tree,
            prefs_label,
            prefs_tree
        ]:
            trees_box.add(el)

        self.add(heading)
        self.add(back_button)
        self.add(trees_box)

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        self.controller.open_page(NotebookPage.OPTIONS)

    def _make_tree(self, prefs: Union["Xdg", "UserPrefs"]) -> Gtk.TreeView:
        view = Gtk.TreeView()
        renderer = Gtk.CellRendererText()
        for i, col in enumerate(developers.columns):
            column = Gtk.TreeViewColumn(col, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            view.append_column(column)

        store = Gtk.ListStore(str, str)
        for field in fields(prefs):
            if field.name == "paths":
                break
            k, v = field.name, getattr(prefs, field.name)
            store.append((k, str(v)))

        view.set_model(store)
        return view
