from typing import Self, TYPE_CHECKING
from dzgui.views.components.scrollable import NoOverlayScrolledWindow
from dzgui.views.trees.tree_mods import ModTreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class Mods(NoOverlayScrolledWindow):
    def __init__(self, controller: "Controller") -> None:
        super().__init__()

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.controller = controller
        self.emitter = controller.get_emitter()
        self.tree = ModTreeView(controller)
        self.tree.set_vexpand(True)

        self.offline_button = Gtk.Button(
            label="Play offline",
            halign=Gtk.Align.START,
            margin_top=10,
            margin_bottom=10,
        )
        self.offline_button.connect("clicked", self._on_offline_clicked)

        self.box.add(self.offline_button)
        self.box.add(self.tree)

        self.add(self.box)
        self.controller.register_widget("modtreeview", self.tree)

        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

    def _on_offline_clicked(self, button: Gtk.Button) -> None:
        self.controller.open_offline(self.tree.get_model())
        # TODO: add offline page

    def _on_unmap(self, widget: Self) -> None:
        self.emitter.emit("mod_page_toggled", False)

    def _on_map(self, widget: Self) -> None:
        self.emitter.emit("mod_page_toggled", True)

    def grab_content_area(self) -> None:
        self.tree.grab_focus()
