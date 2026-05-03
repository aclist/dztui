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

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # type: ignore # noqa E402


if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class PreConnectionAssistant(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__()

        self.controller = controller

        self.button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.END,
            valign=Gtk.Align.END,
            hexpand=True,
            spacing=10,
        )

        self.rules: dict[Any]
        self.mods: list["DayzMod"]

        # TODO: pack in scrolled window

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
        # steam_path = self.controller.get_config_man().lookup(Preferences.DEFAULT)
        # dayz_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ)
        # dayz_exp_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ_EXP)
        pass

    def download_mods(self) -> None:
        pass

    def connect(self) -> None:
        # TODO: add to history file and list store
        pass
