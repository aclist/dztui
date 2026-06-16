from pathlib import Path

from typing import Self, TYPE_CHECKING
from dzgui.api.steam import find_user_id
from dzgui.const.enum import NotebookPage, Preferences
from dzgui.views.components.buttons import SteamWorkshopButton
from dzgui.views.components.scrollable import NoOverlayScrolledWindow
from dzgui.views.trees.tree_mods import ModTreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class Mods(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.box = NoOverlayScrolledWindow()
        self.tree = ModTreeView(controller)
        self.tree.set_vexpand(True)
        self.box.add(self.tree)

        self.statusbar_cache = ""
        self.controller = controller
        self.controller.register_widget("modtreeview", self.tree)
        self.emitter = controller.get_emitter()

        # TODO: move
        default_steam_path = self.controller.query_config(Preferences.DEFAULT)
        steam_path = Path(default_steam_path)
        uid = find_user_id(steam_path)

        pretty_uid = "" if uid is None else uid
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        workshop_button = SteamWorkshopButton()
        workshop_button.set_margin_top(10)
        workshop_button.set_margin_bottom(10)
        workshop_button.connect(
            "clicked", lambda _: self.controller.open_user_workshop(pretty_uid)
        )
        self.offline_button = Gtk.Button(
            label="Play offline",
            halign=Gtk.Align.START,
            margin_top=10,
            margin_bottom=10,
        )
        self.offline_button.connect("clicked", self._on_offline_clicked)

        hbox.add(workshop_button)
        hbox.add(self.offline_button)

        self.add(hbox)
        self.add(self.box)

        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

    def _on_offline_clicked(self, button: Gtk.Button) -> None:
        self.statusbar_cache = self.controller.get_statusbar().get_cache()
        self.controller.open_offline()

    def _on_unmap(self, widget: Self) -> None:
        self.emitter.emit("mod_page_toggled", False)

    def _on_map(self, widget: Self) -> None:
        self.emitter.emit("mod_page_toggled", True)
        # TODO: delegation
        # NOTE: handles going back from offline mods page
        # more generic cache restoration method
        if len(self.statusbar_cache) > 0:
            self.controller.get_statusbar().set_by_context(
                NotebookPage.MODS, self.statusbar_cache
            )

    def grab_content_area(self) -> None:
        self.tree.grab_focus()
