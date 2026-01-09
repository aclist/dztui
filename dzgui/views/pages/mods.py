from typing import TYPE_CHECKING
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
        self.tree = ModTreeView(controller)

        self.add(self.tree)
        self.controller.register_widget("modtreeview", self.tree)
