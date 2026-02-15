from typing import TYPE_CHECKING
from dzgui.views.mixins.cursor_mixin import CursorMixin
from dzgui.views.mixins.help_menu_mixin import HelpMenuMixin
from dzgui.views.trees.tree_log import LogTreeView


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class Log(CursorMixin, HelpMenuMixin, Gtk.ScrolledWindow):  # type: ignore
    def __init__(self, controller: "Controller") -> None:
        super().__init__()
        self.treeview = LogTreeView(controller)
        self.add(self.treeview)

        self.controller = controller
        self.controller.register_widget("logtreeview", self.treeview)

        self.connect("key-press-event", self._on_esc_keypress)

    def get_treeview(self) -> LogTreeView:
        return self.treeview

    def grab_content_area(self) -> None:
        self.treeview.grab_focus()
