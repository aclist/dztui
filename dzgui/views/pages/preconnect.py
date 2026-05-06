from dataclasses import dataclass
from typing import Self, TYPE_CHECKING

from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP,
    ERROR,
    WARNING,
)
from dayzquery import DayzMod
from dzgui.util.css import add_class
from dzgui.strings import preconnect
from dzgui.views.components.frame import HeadingFrame
from dzgui.views.trees.tree_server_mods import ServerModTreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # type: ignore # noqa E402


if TYPE_CHECKING:
    from dzgui.api.servers import A2SInfo
    from dzgui.controllers.mc import Controller


@dataclass
class Warnings:
    passworded: bool
    dayz_running: bool
    no_steam: bool
    wrong_version: bool


@dataclass
class Errors:
    no_space: bool
    no_dayz_exp: bool
    no_dayz: bool


class MaskedTree(Gtk.TreeView):
    def __init__(self, icon: str) -> None:
        super().__init__(headers_visible=False, can_focus=False)

        self.icon = icon
        self.store = Gtk.ListStore(str, str)
        self.set_model(self.store)
        self.get_selection().set_mode(Gtk.SelectionMode.NONE)

        icon_renderer = Gtk.CellRendererPixbuf()
        # NOTE: adjust vertical offset between columns
        icon_renderer.set_property("yalign", 0.6)
        icon_column = Gtk.TreeViewColumn("", icon_renderer)
        icon_column.add_attribute(icon_renderer, "icon-name", 0)
        icon_column.set_fixed_width(50)

        text_renderer = Gtk.CellRendererText()
        text_column = Gtk.TreeViewColumn("", text_renderer, text=1)

        self.append_column(icon_column)
        self.append_column(text_column)
        add_class(self, "masked-tree")

    def append(self, items: list[str]) -> None:
        self.store.clear()
        for item in items:
            self.store.append([self.icon, item])


class PreConnectionAssistant(Gtk.ScrolledWindow):
    def __init__(self, controller: "Controller") -> None:
        super().__init__()

        self.controller = controller

        self.button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.END,
            valign=Gtk.Align.END,
            hexpand=True,
            vexpand=True,
            spacing=10,
        )

        self.controller.register_widget("preconnect", self)

        # TODO: dynamic button text if no mods needed
        self.back = Gtk.Button(label=preconnect.back, halign=Gtk.Align.START)
        self.cancel = Gtk.Button(
            label=preconnect.cancel, halign=Gtk.Align.END, sensitive=False, hexpand=True
        )
        self.ok = Gtk.Button(label=preconnect.update_mods, halign=Gtk.Align.END)

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
        add_class(self.title, "preconnect-heading")

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

        self.tree_frame = HeadingFrame(self.tree_box, preconnect.mods)

        # TODO: abstract into components
        self.warning_tree = MaskedTree(WARNING)
        self.warning_frame = HeadingFrame(self.warning_tree, preconnect.warnings)

        self.error_tree = MaskedTree(ERROR)
        self.error_frame = HeadingFrame(self.error_tree, preconnect.errors)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.add(self.title)
        self.box.add(self.tree_frame)
        self.box.add(self.warning_frame)
        self.box.add(self.error_frame)
        self.box.add(self.button_box)

        self.add(self.box)

        self.connect("key-press-event", self._on_keypress)
        self.connect("map", self._on_map)

    def _on_map(self, widget: Self) -> None:
        self.tree_frame.set_visible(True)
        self.mod_count.set_visible(True)

    def _on_keypress(self, widget: Self, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            self.back.emit("clicked")

    def _on_ok_clicked(self, button: Gtk.Button) -> None:
        # TODO: update mod store in place with spinner/toast
        # TODO: cancel mod downloads
        pass

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        page = self.controller.get_prior_page()
        self.controller.open_page(page)

    def populate(self, res: "A2SInfo", mods: list["DayzMod"]) -> None:
        self.tree.populate(mods)
        total = len(mods)

        self._set_warnings()

        info = res.get_info()
        name = info.server_name
        self.title.set_text(name)
        if total < 1:
            self.tree_frame.set_visible(False)
            self.mod_count.set_visible(False)
            return
        else:
            self.tree.set_visible(True)
            self.mod_count.set_visible(True)
            # TODO: print no. of mods that need updating
            prefix = preconnect.total_mods
            self.mod_count.set_text(f"{prefix}{str(total)}")

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
        # TODO: if errors > 1, disable buttons

    def _set_warnings(self) -> None:
        self.warning_tree.append(["Password protected", "Some other error", "Error 3"])
        self.error_tree.append(["Password protected", "Some other error", "Error 3"])
        pass

    def download_mods(self) -> None:
        pass

    def connect_server(self) -> None:
        # TODO: add to history file and list store
        # TODO: concat mods
        """
        spawn dialog in thread
        watch for subprocess
        return to prior page when finished
        """
        pass
