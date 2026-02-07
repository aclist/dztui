from typing import TYPE_CHECKING
from dzgui.views.trees.tree_menu import MenuTreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class Help(Gtk.ScrolledWindow):
    def __init__(self, controller: "Controller") -> None:
        super().__init__()
        self.treeview = MenuTreeView(controller)
        self.add(self.treeview)

        self.controller = controller

        # FIXME: remember focused row
        #self.treeview.focus_first_row()

    def get_treeview(self) -> MenuTreeView:
        return self.treeview

    def grab_content_area(self) -> None:
        self.treeview.grab_focus()
