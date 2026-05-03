from typing import Any, TYPE_CHECKING

from dzgui.api import pefile as PeFile
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP,
)
from dayzquery import DayzMod
from dzgui.views.components.frame import HeadingFrame
from dzgui.views.trees.tree_server_mods import ServerModTreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # type: ignore # noqa E402


if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


# TODO: pack entire box in scrolled window
class PreConnectionAssistant(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.controller = controller

        self.button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.END,
            valign=Gtk.Align.END,
            hexpand=True,
            vexpand=True,
            spacing=10,
        )

        self.rules: dict[Any]
        self.mods: list["DayzMod"]

        self.controller.register_widget("preconnect", self)

        # TODO: strings
        self.back = Gtk.Button(label="Back")
        # TODO: dynamic button text if no mods needed
        self.ok = Gtk.Button(label="Download mods and connect")
        self.button_box.add(self.back)
        self.button_box.add(self.ok)

        self.back.connect("clicked", self._on_back_clicked)
        self.ok.connect("clicked", self._on_ok_clicked)

        self.warnings = []
        # TODO: populate with strings and icons
        # set visibility if warnings > 1
        frame = HeadingFrame(Gtk.Label(label="ITEM ONE"), "Warnings")

        self.tree = ServerModTreeView(self.controller)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.add(self.tree)
        self.scrolled.set_size_request(600, 400)

        self.tree_frame = HeadingFrame(self.scrolled, "Mods")

        # TODO: should form a part of tree_frame above
        self.mod_count = Gtk.Label(label="")

        self.title = Gtk.Label(label="")

        self.add(self.title)
        self.add(self.tree_frame)
        self.add(self.mod_count)
        self.add(frame)
        self.add(self.button_box)

    def _on_ok_clicked(self, button: Gtk.Button) -> None:
        # TODO: update mod store in place with spinner/toast
        # TODO: cancel mod downloads
        pass

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        page = self.controller.get_prior_page()
        self.controller.open_page(page)

    def populate(self, res: dict[Any], mods: list["DayzMod"]) -> None:
        self.tree.populate(mods)
        total = len(mods)
        self.title.set_text(f"Connecting to {res["name"]}")
        if total < 1:
            self.tree.set_visible(False)
            self.mod_count.set_visible(False)
            return
        else:
            self.tree.set_visible(True)
            self.mod_count.set_visible(True)
            self.mod_count.set_text(f"Total mods: {str(total)}")
        # steam_path = self.controller.get_config_man().lookup(Preferences.DEFAULT)
        # dayz_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ)
        # dayz_exp_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ_EXP)
        pass

    def download_mods(self) -> None:
        pass

    def connect(self) -> None:
        # TODO: add to history file and list store
        pass

    # TODO: icon for mod signature issue
    # or "Update mods and connect"
    # also handle servers with no mods; do not show tree
