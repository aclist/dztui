from typing import Self, TYPE_CHECKING
from dzgui.views.trees.tree_mods import ModTreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class Mods(Gtk.ScrolledWindow):
    def __init__(self, controller: "Controller") -> None:
        super().__init__()

        self.controller = controller
        self.emitter = controller.get_emitter()
        self.tree = ModTreeView(controller)

        self.add(self.tree)
        self.controller.register_widget("modtreeview", self.tree)

        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

    def _on_unmap(self, widget: Self) -> None:
        self.emitter.emit("mod_page_toggled", False)

    def _on_map(self, widget: Self) -> None:
        self.emitter.emit("mod_page_toggled", True)

    def grab_content_area(self) -> None:
        self.tree.grab_focus()
