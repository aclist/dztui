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
        # TODO: dynamic button text if no mods needed
        self.back = Gtk.Button(label="Back", halign=Gtk.Align.START)
        self.cancel = Gtk.Button(
            label="Cancel", halign=Gtk.Align.END, sensitive=False, hexpand=True
        )
        self.ok = Gtk.Button(label="Update mods and connect", halign=Gtk.Align.END)

        self.button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            valign=Gtk.Align.END,
            vexpand=True,
            spacing=5,
        )
        for button in self.back, self.cancel, self.ok:
            self.button_box.add(button)

        self.back.connect("clicked", self._on_back_clicked)
        self.ok.connect("clicked", self._on_ok_clicked)

        self.title = Gtk.Label(label="")

        self.tree = ServerModTreeView(self.controller)
        self.mod_count = Gtk.Label(label="", halign=Gtk.Align.START, margin_start=5)
        # TODO: live count of remaining downloads
        # "Steam is downloading: {mod_name}"
        # mention whether manual or auto mod is active

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.add(self.tree)
        self.scrolled.set_size_request(600, 400)

        self.tree_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.tree_box.add(self.scrolled)
        self.tree_box.add(self.mod_count)

        self.tree_frame = HeadingFrame(self.tree_box, "Mods")

        self.warnings = []
        # TODO: populate with strings and icons
        # set visibility if warnings > 1
        # warning category enums with matching strings
        """
        blocking warning types:
        - build mismatch
        - version mismatch
        - not enough drive space
        passing warning types:
        - dayz is running
        - steam is not running
        - server has password
        """
        frame = HeadingFrame(Gtk.Label(label="ITEM ONE"), "Warnings")

        self.add(self.title)
        self.add(self.tree_frame)
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
            self.tree_frame.set_visible(False)
            self.mod_count.set_visible(False)
            return
        else:
            self.tree.set_visible(True)
            self.mod_count.set_visible(True)
            self.mod_count.set_text(f"Total mods: {str(total)}")

        # TODO: check which mods need updating
        # TODO: fourth column: needs update
        # steam_path = self.controller.get_config_man().lookup(Preferences.DEFAULT)
        # dayz_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ)
        # dayz_exp_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ_EXP)
        pass

    def download_mods(self) -> None:
        pass

    def connect(self) -> None:
        # TODO: add to history file and list store
        """
        spawn dialog in thread
        watch for subprocess
        return to prior page when finished
        """
        self.back.emit("clicked")
        pass

    # TODO: icon for mod signature issue
    # or "Update mods and connect"
    # also handle servers with no mods; do not show tree
